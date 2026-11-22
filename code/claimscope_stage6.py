#!/usr/bin/env python3
"""ClaimScope Stage 6: claim-specific repository influence certificates.

Inputs: publicly released compact RQ3 labels, never performance ground truth.
No causal claims or author-identity validation. Standard library only.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, random
from dataclasses import dataclass
from pathlib import Path

GIT_BLOB_ID = '136a2cf5bf1a9a71f06f2a7c6c9932194865c854'
REPO_SOURCE = 'PurdueDualityLab/EMSE-perf-pr-study'
AGENT, HUMAN = 'agentic', 'human_candidate'

@dataclass(frozen=True)
class Observation:
    repo: str
    pr: str
    arm: str
    pattern: str
    M6: int
    M6_no_diff: int
    url: str


def git_blob_sha1(raw:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()


def parse_rows(source):
    parsed, seen = [], set()
    for row in source:
        if row.get('sample_arm') not in (AGENT, HUMAN):
            raise ValueError('unknown arm')
        if row.get('in_metric_layer') not in ('True', 'False') or row.get('validation_present') not in ('True', 'False'):
            raise ValueError('invalid gate')
        if row['in_metric_layer'] == 'False':
            # Still reject duplicate identities among the full export.
            key=(row['repo_id'],row['number'])
            if not all(key): raise ValueError('empty PR identity')
            if key in seen: raise ValueError('duplicate PR across dataset or cohort')
            seen.add(key)
            continue
        if row['validation_present']!='True':
            raise ValueError('metric inclusion without validation gate')
        # A PR identity must be unique independently of its cohort; otherwise
        # the same underlying observation can appear on both sides of a comparison.
        key=(row['repo_id'],row['number'])
        if not all(key): raise ValueError('empty PR identity')
        if key in seen: raise ValueError('duplicate PR across dataset or cohort')
        seen.add(key)
        if row['D6'] not in ('True','False') or row['D6_nodiff'] not in ('True','False'):
            raise ValueError('nonboolean metric')
        m6=int(row['D6']=='True'); nd=int(row['D6_nodiff']=='True')
        if nd>m6:raise ValueError('no-diff must be nested within full evidence')
        parsed.append(Observation(row['repo_id'], row['number'], row['sample_arm'],row['pattern'],m6,nd,row['html_url']))
    if not parsed or set(r.arm for r in parsed)!={AGENT,HUMAN}:raise ValueError('nonempty groups required')
    return parsed


def load_csv(path, validate_blob=True):
    raw=Path(path).read_bytes()
    sha=git_blob_sha1(raw)
    if validate_blob and sha!=GIT_BLOB_ID:
        raise ValueError('source blob mismatch. Expected '+GIT_BLOB_ID+'; received '+sha)
    rows=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    must={'repo_id','number','sample_arm','pattern','validation_present','in_metric_layer','D6','D6_nodiff','html_url'}
    if rows and not must.issubset(rows[0]):raise ValueError('missing source fields')
    return parse_rows(rows)


def group_stats(records,field='M6'):
    out={}
    for arm in (AGENT,HUMAN):
        z=[x for x in records if x.arm==arm]
        if not z:raise ValueError('missing arm')
        count=sum(getattr(x,field) for x in z)
        out[arm]={'n':len(z),'positive':count,'rate':count/len(z)}
    a,h=(out[g] for g in (AGENT,HUMAN))
    return {'groups':out, 'contrast_pp':100*(a['rate']-h['rate']),
            'ratio':a['rate']/h['rate'] if h['rate'] else None}


def repo_index(records):
    repo=collections.defaultdict(list)
    for x in records:repo[x.repo].append(x)
    return dict(repo)


def pattern_standardized(records,field='M6'):
    patterns=collections.defaultdict(list)
    for x in records:patterns[x.pattern].append(x)
    total=len(records);std=0; rows=[]
    for pat,v in patterns.items():
        s=group_stats(v,field)
        w=len(v)/total
        std+=w*s['contrast_pp']
        rows.append({'pattern':pat,'n':len(v),'weight':w,'contrast_pp':s['contrast_pp'],
                     'groups':s['groups']})
    return {'standardized_contrast_pp':std,'patterns':sorted(rows,key=lambda x:-x['n'])}


def influence(records,field='M6',top=10):
    baseline=group_stats(records,field)['contrast_pp']
    mapping=repo_index(records)
    oneouts=[]
    for rid,bucket in mapping.items():
        rest=[x for x in records if x.repo!=rid]
        if set(x.arm for x in rest)!={AGENT,HUMAN}:continue
        r=group_stats(rest,field)
        byarm={g:sum(getattr(x,field) for x in bucket if x.arm==g) for g in (AGENT,HUMAN)}
        sizes={g:sum(x.arm==g for x in bucket) for g in (AGENT,HUMAN)}
        oneouts.append({'repo_id':rid,'representative_url':bucket[0].url,'positives':byarm,
                       'n':sizes,'contrast_after_pp':r['contrast_pp'],
                       'shift_pp':r['contrast_pp']-baseline})
    oneouts.sort(key=lambda x:(-abs(x['shift_pp']),x['repo_id']))
    return oneouts[:top]


def within_shared(records,field='M6'):
    mapping=repo_index(records);v=[]
    for rid,b in mapping.items():
        if set(x.arm for x in b)=={AGENT,HUMAN}:
            a=[getattr(x,field) for x in b if x.arm==AGENT]
            h=[getattr(x,field) for x in b if x.arm==HUMAN]
            v.append(sum(a)/len(a)-sum(h)/len(h))
    if not v:raise ValueError('no overlapping repositories')
    return {'shared_repos':len(v),'equal_repo_contrast_pp':100*sum(v)/len(v),
            'positive':sum(x>0 for x in v),'negative':sum(x<0 for x in v),'ties':sum(x==0 for x in v)}


def cluster_bootstrap(records,field='M6',B=2500,seed=361827):
    if B<100:raise ValueError('B too small')
    byrepo=repo_index(records);buckets=[byrepo[k] for k in sorted(byrepo)];rnd=random.Random(seed);res=[]
    for _ in range(B):
        data=[y for _ in buckets for y in buckets[rnd.randrange(len(buckets))]]
        if set(x.arm for x in data)!={AGENT,HUMAN}:continue
        res.append(group_stats(data,field)['contrast_pp'])
    res.sort()
    if not res:raise ValueError('invalid bootstrap draws')
    return {'B':len(res),'seed':seed,'percentile95_pp':[
        res[math.floor(.025*(len(res)-1))],res[math.floor(.975*(len(res)-1))]],
        'note':'observed-repository sensitivity only, not population confidence interval'}


def certificate(records):
    r=group_stats(records)
    byrepo=repo_index(records)
    leading=max(byrepo, key=lambda id:sum(x.M6 for x in byrepo[id] if x.arm==AGENT))
    leading_positives=sum(x.M6 for x in byrepo[leading] if x.arm==AGENT)
    agents=r['groups'][AGENT]['positive']
    without=[x for x in records if x.repo!=leading]
    std=pattern_standardized(records)
    shared=within_shared(records)
    result={'schema':'claimscope/metric-influence-certificate/v1',
            'source_repo':REPO_SOURCE,'source_git_blob_sha1':GIT_BLOB_ID,
            'outcome':'at-least-one reported quantitative artifact-size metric (D6)',
            'population':'validation-positive PRs with resolved optimization pattern',
            'comparison':'agentic minus human_candidate',
            'observed':r,
            'source_without_code_diff':group_stats(records,'M6_no_diff'),
            'pooled_pattern_standardized':std,
            'shared_repositories_equal_weight':shared,
            'most_concentrated_repository':{'repo_id':leading,'agent_positive_count':leading_positives,
                'agent_positive_share':leading_positives/agents,
                'repository_rows':{'agentic':sum(x.arm==AGENT for x in byrepo[leading]),
                                   'human_candidate':sum(x.arm==HUMAN for x in byrepo[leading])},
                'without':group_stats(without)},
            'influential_repositories':influence(records),
            'provenance_limit':'Compact labels do not disclose the original matching text spans or evidence authorship.',
            'interpretation':{'repository_selection':'SCOPE_SENSITIVE',
                'metric_provenance':'EXTRACTED_PR_ARTIFACT_FLAG; SOURCE_SPAN_NOT_RELEASED',
                'quality_of_improvements':'OUTSIDE_MEASUREMENT',
                'causation_or_model_superiority':'OUTSIDE_MEASUREMENT'}}
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--rq3',required=True,help='original public rq3_labels.csv')
    ap.add_argument('--output',default='claimscope_stage6_replay.json')
    ap.add_argument('--skip-sha-check',action='store_true',help='only for exploratory runs')
    args=ap.parse_args()
    records=load_csv(args.rq3,not args.skip_sha_check)
    cert=certificate(records)
    Path(args.output).write_text(json.dumps(cert,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(records),'gated PRs','D6 gap',cert['observed']['contrast_pp'], 'witness:',cert['most_concentrated_repository']['repo_id'])

if __name__=='__main__':main()
