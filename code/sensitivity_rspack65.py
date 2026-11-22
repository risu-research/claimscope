#!/usr/bin/env python3
"""Local D6 evidence-boundary sensitivity for the 1,699 public analytic PRs.

Replays 65 source-linked Rspack positive flags under two explicit interventions:
(a) set their D6 indicators to false, keeping all 1,699 denominators;
(b) omit the same 65 observations, changing both denominators.
All other source labels stay fixed. Python standard library only.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import math
import random
from pathlib import Path

import claimscope_stage6 as core

ROOT=Path(__file__).resolve().parents[1]
RSPACK='476642602'
SOURCE_SHA256='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
PAIR_BLOB_SHA='ddf2cf809ec82e20a83ce034711bc21512d52051'
ARM_NAMES=('agentic','human_candidate')


def load_inputs(source, pairs, boundary):
    raw=Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Original label CSV SHA-256 differs from pinned upstream bytes')
    observations=core.load_csv(source)
    if len(observations)!=1699 or len({(r.repo,r.pr) for r in observations})!=1699:
        raise ValueError('Original analytic cohort must have 1,699 unique PRs')
    if core.git_blob_sha1(Path(pairs).read_bytes())!=PAIR_BLOB_SHA:
        raise ValueError('65-PR source-linked comment pair CSV differs from frozen witness')
    with Path(pairs).open(encoding='utf-8',newline='') as f:
        witnesses=list(csv.DictReader(f))
    with Path(boundary).open(encoding='utf-8',newline='') as f:
        runs=list(csv.DictReader(f))
    if len(witnesses)!=72 or len(runs)!=97:
        raise ValueError('Expected 72 comment pair witnesses and 97 complete Rspack checks')
    selected={}
    for p in witnesses:
        key=(RSPACK,str(int(p['pr_number'])))
        if p['published_D6']!='True' or p['pair_only_D6']!='True' or p['pair_with_separator_D6']!='False' or p['cue_D6_alone']!='False' or p['quant_D6_alone']!='False':
            raise ValueError('Nonconforming witness '+str(key))
        if p['cue_comment_account']!='github-actions[bot]' or p['quant_comment_account']!='github-actions[bot]':
            raise ValueError('Comment author differs from audited automation account')
        if p['source_comment_gap']!='1' or p['cue_comment_id']==p['quant_comment_id']:
            raise ValueError('Comment pairing identity or adjacency mismatch')
        if key in selected and selected[key]!=p['sample_arm']:
            raise ValueError('Conflicting cohorts within same PR')
        selected[key]=p['sample_arm']
    if len(selected)!=65:
        raise ValueError('Expected 65 unique source-linked boundary-only PRs')
    seen=set();independent=set()
    for r in runs:
        key=(RSPACK,str(int(r['pr_number'])))
        if key in seen:raise ValueError('Duplicate boundary audit PR')
        seen.add(key)
        if r['all_concat_D6']!=r['published_D6']:
            raise ValueError('Current comment concat differs from published D6 for '+str(key))
        if (r['all_concat_D6'],r['all_individual_D6'],r['all_padded_D6'])==('True','False','False'):
            independent.add(key)
    if set(selected)!=independent or len(seen)!=97:
        raise ValueError('Comment pair witness set differs from 97-PR boundary sensitivity set')
    index={(x.repo,x.pr):x for x in observations}
    for key,arm in selected.items():
        r=index.get(key)
        if r is None or r.arm!=arm or r.M6!=1 or r.M6_no_diff!=1:
            raise ValueError('Published PR, original D6, or no-diff status failed 1:1 join '+str(key))
    rspack=[x for x in observations if x.repo==RSPACK]
    if len(rspack)!=97 or sum(x.M6 for x in rspack)!=83:
        raise ValueError('Rspack original cohort does not match locked counts')
    if collections.Counter(selected.values())!={'agentic':60,'human_candidate':5}:
        raise ValueError('Unexpected arm composition in 65-PR witness cohort')
    return observations, selected


def by_arm(records,excluded=frozenset()):
    ans={}
    for arm in ARM_NAMES:
        v=[x for x in records if x.arm==arm and (x.repo,x.pr) not in excluded]
        if not v:raise ValueError('Missing arm')
        count=sum(x.M6 for x in v)
        ans[arm]={'n':len(v),'D6_yes':count,'D6_no':len(v)-count,'rate':count/len(v),'rate_percent':100*count/len(v)}
    a,h=[ans[x] for x in ARM_NAMES]
    return {'by_arm':ans,'gap_pp':a['rate_percent']-h['rate_percent'],'rate_ratio':a['rate']/h['rate'] if h['rate'] else None}


def set_selected_off(original,selected):
    # Preserve all other published PRs and denominators; only D6 is varied.
    from dataclasses import replace
    return [replace(x,M6=0,M6_no_diff=0) if (x.repo,x.pr) in selected else x for x in original]


def two_stratum_kitagawa(records):
    rows={}
    for arm in ARM_NAMES:
        allarm=[x for x in records if x.arm==arm]
        rows[arm]={}
        for label,inside in (('rspack',True),('other',False)):
            arr=[x for x in allarm if (x.repo==RSPACK)==inside]
            rows[arm][label]={'n':len(arr),'positives':sum(x.M6 for x in arr), 'weight':len(arr)/len(allarm),'rate':sum(x.M6 for x in arr)/len(arr)}
    within=sum((rows['agentic'][s]['weight']+rows['human_candidate'][s]['weight'])/2 *
        (rows['agentic'][s]['rate']-rows['human_candidate'][s]['rate']) for s in ('rspack','other'))
    composition=sum((rows['agentic'][s]['weight']-rows['human_candidate'][s]['weight'])*
        (rows['agentic'][s]['rate']+rows['human_candidate'][s]['rate'])/2 for s in ('rspack','other'))
    actual=by_arm(records)['gap_pp']/100
    if abs(within+composition-actual)>1e-12:raise ValueError('Kitagawa accounting does not close')
    return {'rates_and_weights':rows,'within_rate_component_pp':within*100,
            'composition_component_pp':composition*100,
            'composition_fraction_of_pooled_gap':composition/actual if actual else None,
            'checksum_gap_pp':100*(within+composition)}


def partial_identification(original,selected):
    # Number of independently supported D6 positives retained among the 65 is unavailable.
    base=by_arm(set_selected_off(original,selected))['by_arm']
    scenarios=[]
    for kept_a in range(61):
        for kept_h in range(6):
            gap=100*((base['agentic']['D6_yes']+kept_a)/base['agentic']['n']-
                (base['human_candidate']['D6_yes']+kept_h)/base['human_candidate']['n'])
            scenarios.append((gap,kept_a,kept_h))
    lo=min(scenarios);hi=max(scenarios)
    return {'unknown_other_source_support':{'agentic_0_to_60':60,'human_candidate_0_to_5':5},
            'conditional_gap_min_pp':lo[0], 'min_retained_agentic':lo[1],'min_retained_human_candidate':lo[2],
            'conditional_gap_max_pp':hi[0], 'max_retained_agentic':hi[1],'max_retained_human_candidate':hi[2],
            'all_count_combinations':len(scenarios),
            'always_positive_under_local_scope':all(v[0]>0 for v in scenarios)}


def paired_cluster_bootstrap(original,scenario,B=12000,seed=20261122):
    if len(original)!=len(scenario):raise ValueError('Paired records differ in length')
    groups=collections.defaultdict(lambda:[[0,0,0],[0,0,0]])
    for a,b in zip(original,scenario):
        if (a.repo,a.pr,a.arm)!=(b.repo,b.pr,b.arm):raise ValueError('Pair alignment failure')
        x=groups[a.repo][0 if a.arm=='agentic' else 1]
        x[0]+=a.M6;x[1]+=b.M6;x[2]+=1
    keys=sorted(groups);table=[groups[k] for k in keys]
    rng=random.Random(seed)
    vec={'published':[],'scenario':[],'scenario_minus_published':[]}
    skipped=0
    for _ in range(B):
        sums=[[0,0,0],[0,0,0]]
        for __ in table:
            v=table[rng.randrange(len(table))]
            for j in (0,1):
                for c in (0,1,2):sums[j][c]+=v[j][c]
        if sums[0][2]==0 or sums[1][2]==0:skipped+=1;continue
        po=100*(sums[0][0]/sums[0][2]-sums[1][0]/sums[1][2])
        sc=100*(sums[0][1]/sums[0][2]-sums[1][1]/sums[1][2])
        vec['published'].append(po);vec['scenario'].append(sc);vec['scenario_minus_published'].append(sc-po)
    def summary(vals):
        vals.sort();n=len(vals)
        return {'median_pp':vals[n//2],'percentile_95_pp':[vals[int(.025*(n-1))],vals[int(.975*(n-1))]],
                'fraction_le_zero':sum(v<=0 for v in vals)/n}
    return {'method':'matched joint-repository cluster resampling','seed':seed,'requested_draws':B,'retained_draws':B-skipped,
            'repository_count':len(keys),'metrics':{name:summary(v) for name,v in vec.items()},
            'interpretation':'Descriptive dependence on observed repository composition; no population-sampling design assumed.'}


def run(source,pairs,boundary,B=12000,seed=20261122):
    original,keys=load_inputs(source,pairs,boundary)
    counter=set_selected_off(original,keys)
    publication=by_arm(original)
    flag_off=by_arm(counter)
    drop65=by_arm(original,keys)
    leave_repo=by_arm([x for x in original if x.repo!=RSPACK])
    original_rspack=by_arm([x for x in original if x.repo==RSPACK])
    changed_rspack=by_arm([x for x in counter if x.repo==RSPACK])
    baseline_d6=sum(x.M6 for x in original)
    touched={key for key in keys}
    for x,y in zip(original,counter):
        if (x.repo,x.pr) not in touched and x!=y:
            raise ValueError('Unexpected change to unrelated PR')
        if (x.repo,x.pr) in touched and (x.M6!=1 or y.M6!=0 or x.M6_no_diff!=1 or y.M6_no_diff!=0):
            raise ValueError('Selected D6 flag change violated frozen source invariants')
    shared_orig=core.within_shared(original)
    shared_scenario=core.within_shared(counter)
    pattern_orig=core.pattern_standardized(original)
    pattern_scenario=core.pattern_standardized(counter)
    shift=flag_off['gap_pp']-publication['gap_pp']
    return {'schema':'claimscope/rspack65-local-D6-sensitivity/v1',
            'input_provenance':{'public_source_csv_sha256':SOURCE_SHA256,'public_source_git_blob_sha1':core.GIT_BLOB_ID,
               'pair_ledger_git_blob_sha1':PAIR_BLOB_SHA,
               'pinned_upstream_extractor_commit':'64432e0b6ed7791bbfa929c6c183fc76c75b5d58',
               'target_repo_id':RSPACK,'all_export_rows':2081,'analytic_rows':len(original),'analytic_repository_count':len(core.repo_index(original)),
               'pair_witnesses':72,'unique_PRs':len(keys),'selected_by_arm':dict(collections.Counter(keys.values()))},
            'scenarios':{'published':publication,'disable_65_D6_flags':flag_off,
                'exclude_65_PR_rows':drop65,'exclude_Rspack_repository':leave_repo,
                'Rspack_published':original_rspack,'Rspack_disable_65':changed_rspack},
            'effects':{'absolute_shift_pp':shift,'gap_attenuation_fraction':-shift/publication['gap_pp'],
                'original_total_D6_yes':baseline_d6,'scenario_total_D6_yes':sum(x.M6 for x in counter),
                'affected_fraction_of_all_1699_PRs':len(keys)/len(original),
                'affected_fraction_of_all_published_D6_yes':len(keys)/baseline_d6,
                'agentic_rate_shift_pp':flag_off['by_arm']['agentic']['rate_percent']-publication['by_arm']['agentic']['rate_percent'],
                'human_rate_shift_pp':flag_off['by_arm']['human_candidate']['rate_percent']-publication['by_arm']['human_candidate']['rate_percent']},
            'within_shared_repository':{'published':shared_orig,'disable_65':shared_scenario},
            'pattern_standardized':{'published_gap_pp':pattern_orig['standardized_contrast_pp'],
                'disable_65_gap_pp':pattern_scenario['standardized_contrast_pp']},
            'two_stratum_kitagawa':{'published':two_stratum_kitagawa(original),'disable_65':two_stratum_kitagawa(counter)},
            'other_evidence_channel_retention':partial_identification(original,keys),
            'joint_repository_bootstrap':paired_cluster_bootstrap(original,counter,B,seed),
            'interpretation':{
                'disable_65_D6_flags':'Controlled local intervention on 65 Rspack D6 flags. Other 1,634 published labels and all original denominators fixed.',
                'exclude_65_PR_rows':'Observed original labels after excluding 65 PRs with cross-comment-only issue-thread matches.',
                'exclude_Rspack_repository':'Observed original labels after excluding all Rspack PRs.',
                'full_extractor_recode_status':'Unknown. Other original evidence channels and the historical 2026-08-27 snapshot remain unavailable.',
                'causal_or_truth_status':'Descriptive measurement-sensitivity calculations under specified operations.'}}


def write_scenario_table(result, path):
    names=('published','disable_65_D6_flags','exclude_65_PR_rows','exclude_Rspack_repository',
           'Rspack_published','Rspack_disable_65')
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf8',newline='') as f:
        w=csv.writer(f)
        w.writerow(('scenario','agentic_n','agentic_D6_yes','agentic_rate_pct',
                    'human_candidate_n','human_candidate_D6_yes','human_candidate_rate_pct','contrast_pp'))
        for name in names:
            a=result['scenarios'][name]['by_arm']['agentic']
            h=result['scenarios'][name]['by_arm']['human_candidate']
            w.writerow((name,a['n'],a['D6_yes'],f"{a['rate_percent']:.9f}",
                h['n'],h['D6_yes'],f"{h['rate_percent']:.9f}",
                f"{result['scenarios'][name]['gap_pp']:.9f}"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels',type=Path,default=ROOT/'data/rq3_labels.csv')
    parser.add_argument('--pairs',type=Path,default=ROOT/'results/rspack_65_comment_pairs.csv')
    parser.add_argument('--boundary',type=Path,default=ROOT/'results/rspack_97_comment_boundary_audit.csv')
    parser.add_argument('--output',type=Path,default=ROOT/'build/rspack65_sensitivity.json')
    parser.add_argument('--bootstrap',type=int,default=12000)
    parser.add_argument('--table',type=Path,default=ROOT/'build/rspack65_scenario_table.csv')
    parser.add_argument('--seed',type=int,default=20261122)
    args=parser.parse_args()
    res=run(args.labels,args.pairs,args.boundary,args.bootstrap,args.seed)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(res,indent=2,sort_keys=True)+'\n',encoding='utf8')
    write_scenario_table(res,args.table)
    print(json.dumps({'n':res['input_provenance']['analytic_rows'],
       'original_gap_pp':res['scenarios']['published']['gap_pp'],
       'disable_gap_pp':res['scenarios']['disable_65_D6_flags']['gap_pp'],
       'drop_gap_pp':res['scenarios']['exclude_65_PR_rows']['gap_pp'],
       'excluding_rspack_gap_pp':res['scenarios']['exclude_Rspack_repository']['gap_pp'],
       'source_linked_PRs':res['input_provenance']['unique_PRs']},indent=2))

if __name__=='__main__':main()
