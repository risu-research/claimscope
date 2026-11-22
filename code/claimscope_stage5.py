#!/usr/bin/env python3
"""ClaimScope Stage 5: reproducible measurement-contract, repository-unit and
identification-bound audits of agentic software engineering PR records.

Consumes public source CSV files; never infers semantic correctness, author
identity, causal effects, or performance improvements from metric extraction.
Python 3.10+ stdlib only. See README.md for pinned source version.
"""
from __future__ import annotations
import argparse, collections, csv, json, math, random
from dataclasses import dataclass
from pathlib import Path

ARMS = ('agentic', 'human_candidate')
SURFACES = ('full', 'no_diff', 'description')
LABELS = {'full':'n_dims', 'no_diff':'n_dims_nodiff', 'description':'n_dims_description_only'}
GROUP = {'agentic': 'agentic', 'human_candidate':'human_candidate'}

@dataclass(frozen=True)
class PR:
    repo: str
    number: str
    arm: str
    pattern: str
    full: bool
    no_diff: bool
    description: bool
    url: str


def parse_csv(path: str | Path) -> list[PR]:
    with open(path, encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        required={'repo_id','number','sample_arm','pattern','html_url','validation_present','in_metric_layer'}|set(LABELS.values())
        if not rd.fieldnames or not required.issubset(set(rd.fieldnames)):
            raise ValueError('missing source fields '+str(required-set(rd.fieldnames or [])))
        rows=list(rd)
    return parse_records(rows)


def parse_records(rows: list[dict]) -> list[PR]:
    seen=set();out=[]
    for r in rows:
        arm=r['sample_arm'];v=r['validation_present'];gate=r['in_metric_layer']
        if arm not in ARMS or v not in ('True','False') or gate not in ('True','False'):
            raise ValueError('unknown author group or gate')
        if gate=='True' and v!='True':raise ValueError('metric gate without validated-positive condition')
        key=(r['repo_id'],r['number'])
        if not all(key):raise ValueError('missing PR identity')
        if key in seen:raise ValueError('duplicate PR identity across cohorts')
        seen.add(key)
        if gate!='True':continue
        nums=[]
        for f in LABELS.values():
            try: n=int(r[f])
            except (ValueError,TypeError):raise ValueError(f'invalid metric dimension count {f}')
            if n<0:raise ValueError('negative metric dimension')
            nums.append(n)
        if not (nums[0]>=nums[1]>=nums[2]):
            raise ValueError('expected evidence-surface nesting full >= no_diff >= description')
        out.append(PR(repo=r['repo_id'],number=r['number'],arm=arm,pattern=r['pattern'],
                      full=nums[0]>0,no_diff=nums[1]>0,description=nums[2]>0,url=r['html_url']))
    if not out:raise ValueError('no gated positive rows')
    return out


def mean(xs):
    if not xs:raise ValueError('empty denominator')
    return sum(xs)/len(xs)


def positive_rate(rows, surface):
    return mean([getattr(x,surface) for x in rows])


def repo_stats(rows:list[PR], surface='full'):
    groups={a:collections.defaultdict(list) for a in ARMS}
    for x in rows:groups[x.arm][x.repo].append(x)
    if not all(groups[a] for a in ARMS):raise ValueError('both groups required')
    byarm={}
    for arm in ARMS:
        repos=groups[arm];ns=sorted((len(rs) for rs in repos.values()),reverse=True)
        n=sum(ns)
        byarm[arm]={'n':n,'n_repos':len(repos),'pooled_rate':positive_rate([x for rr in repos.values() for x in rr],surface),
                    'repo_equal_rate':mean([positive_rate(rr,surface) for rr in repos.values()]),
                    'top1_share':ns[0]/n,'top5_share':sum(ns[:5])/n,'top10_share':sum(ns[:10])/n,
                    'concentration_equivalent_repos':1/sum((x/n)**2 for x in ns)}
    a,h=(groups[x] for x in ARMS)
    shared=set(a)&set(h)
    paired=[positive_rate(a[r],surface)-positive_rate(h[r],surface) for r in sorted(shared)]
    pooled=byarm['agentic']['pooled_rate']-byarm['human_candidate']['pooled_rate']
    equal=byarm['agentic']['repo_equal_rate']-byarm['human_candidate']['repo_equal_rate']
    loo=[]
    for repo in sorted(set(a)|set(h)):
        aa=[x for k,rr in a.items() if k!=repo for x in rr]
        hh=[x for k,rr in h.items() if k!=repo for x in rr]
        if not aa or not hh:continue
        d=positive_rate(aa,surface)-positive_rate(hh,surface)
        loo.append({'repo_id':repo,'excluded_n':len(a.get(repo,[]))+len(h.get(repo,[])),
                    'contrast':d,'shift':d-pooled,'representative_PR':(a.get(repo) or h.get(repo))[0].url})
    loo.sort(key=lambda x:(-abs(x['shift']),x['repo_id']))
    return {'by_arm':byarm,'repo_total':len(set(a)|set(h)),'shared_repo_count':len(shared),
            'pooled_contrast':pooled,'repo_equal_contrast':equal,
            'shared_repo_equal_contrast':mean(paired) if paired else None,
            'shared_positive_repo':sum(x>0 for x in paired),'shared_negative_repo':sum(x<0 for x in paired),
            'shared_tied_repo':sum(x==0 for x in paired),
            'top_leave_one_repo_out':loo[:10], 'extreme_loo':{'min':min(x['contrast'] for x in loo),
                 'max':max(x['contrast'] for x in loo)}}


def bootstrap_repo(rows:list[PR],surface='full',seed=20261010,B=3000):
    """Resample UNION of repositories jointly, preserving same-repository A/H dependence.
    A descriptive cluster-sensitivity interval, not population-design coverage.
    """
    if B<100:raise ValueError('need at least 100 bootstrap draws')
    buckets=collections.defaultdict(lambda:[[0,0],[0,0]])
    for p in rows:
        t=buckets[p.repo][0 if p.arm=='agentic' else 1]
        t[0]+=int(getattr(p,surface));t[1]+=1
    keys=sorted(buckets)
    data=[buckets[k] for k in keys]
    rng=random.Random(seed);samples=[]
    for _ in range(B):
        sums=[[0,0],[0,0]]
        for _ in range(len(data)):
            v=data[rng.randrange(len(data))]
            for j in (0,1):
                sums[j][0]+=v[j][0];sums[j][1]+=v[j][1]
        if all(d for _,d in sums):samples.append(sums[0][0]/sums[0][1]-sums[1][0]/sums[1][1])
    samples.sort()
    if not samples:raise ValueError('bootstrap never sampled both groups')
    return {'method':'joint_repository_cluster_resampling','B':len(samples),'seed':seed,
            'percentile_95':[samples[int(.025*(len(samples)-1))],samples[int(.975*(len(samples)-1))]],
            'median':samples[len(samples)//2],
            'warning':'Sensitivity interval conditional on observed convenience sample; not a design-based population CI.'}


def pattern_standardized(rows:list[PR],surface='full'):
    pats=sorted({p.pattern for p in rows});a=[x for x in rows if x.arm=='agentic'];h=[x for x in rows if x.arm=='human_candidate']
    pooled=positive_rate(a,surface)-positive_rate(h,surface);detail=[];adjusted=0
    for pat in pats:
        ar=[x for x in a if x.pattern==pat];hr=[x for x in h if x.pattern==pat]
        if not ar or not hr:
            raise ValueError('pattern positivity violated; cannot standardize without assumptions: '+pat)
        w=(len(ar)+len(hr))/len(rows)
        da=positive_rate(ar,surface);dh=positive_rate(hr,surface)
        adjusted+=w*(da-dh)
        detail.append({'pattern':pat,'agentic_n':len(ar),'human_candidate_n':len(hr),
                       'agentic_rate':da,'human_candidate_rate':dh,'difference':da-dh,'pooled_weight':w,
                       'small_stratum_warning':min(len(ar),len(hr))<10})
    detail.sort(key=lambda x:x['agentic_n']+x['human_candidate_n'],reverse=True)
    return {'pooled':pooled,'standardized_common_pattern_mix':adjusted,
            'composition_remainder':pooled-adjusted,'categories':detail,
            'warning':'Descriptive pattern standardization; observational cohorts and pattern labels can be confounded.'}


def surface_metrics(rows:list[PR]):
    z={}
    for arm in ARMS:
        arr=[x for x in rows if x.arm==arm]
        z[arm]={'n':len(arr),**{k:sum(getattr(x,k) for x in arr) for k in SURFACES},
                'diff_only_positive':sum(x.full and not x.no_diff for x in arr),
                'not_in_description':sum(x.full and not x.description for x in arr)}
    return z


def nested_bound(total,validated,gated,positive):
    if not 0<=positive<=gated<=validated<=total or total==0:raise ValueError('invalid target population or gate counts')
    return {'target_n':total,'validated':validated,'observed_gated':gated,'positive':positive,
            'unknown_validated':validated-gated,
            'all_pr_bounds':[positive/total,(positive+validated-gated)/total],
            'validation_positive_bounds':[positive/validated,(positive+validated-gated)/validated]}


def sign_verdict(bounds_a,bounds_h):
    lo=bounds_a[0]-bounds_h[1];hi=bounds_a[1]-bounds_h[0]
    return {'contrast_bounds':[lo,hi], 'direction': 'AGENTIC_HIGHER' if lo>0 else ('HUMAN_CANDIDATE_HIGHER' if hi<0 else ('EQUAL' if lo==hi==0 else 'NOT_IDENTIFIED'))}


def identification(rows:list[PR],published=None):
    # These totals come from study manuscript, not full rq2 PR labels.
    if published is None:published={'agentic':{'total':1129,'validation':929},'human_candidate':{'total':1129,'validation':910}}
    z={}
    for arm in ARMS:
        selected=[r for r in rows if r.arm==arm]
        p=published[arm]
        z[arm]=nested_bound(p['total'],p['validation'],len(selected),sum(x.full for x in selected))
    # Equal-denominator population tipping-point with unknown outcomes: how many
    # agentic-only newly positive unknown PRs reverse the all-zero starting assignment?
    a,h=z['agentic'],z['human_candidate'];need=None
    for k in range(a['unknown_validated']+1):
        if (a['positive']+k)/a['target_n']>h['positive']/h['target_n']:
            need=k;break
    return {'group_bounds':z,'all_pr_contrast':sign_verdict(a['all_pr_bounds'],h['all_pr_bounds']),
            'validation_positive_contrast':sign_verdict(a['validation_positive_bounds'],h['validation_positive_bounds']),
            'one_sided_min_additional_agentic_positive_for_positive_all_pr_contrast':need,
            'assumptions':['Counts from paper, nested positive-validation and resolved optimization gates',
                           'Outcomes in excluded validated PRs unconstrained',
                           'Validation-negative PRs are structural zeros ONLY for the defined metric-with-validation outcome',
                           'Observed extracted labels treated as accurate measurements of reported text, not execution truth']}


def audit(rows:list[PR], bootstrap_B=3000,seed=20261010,published=None):
    by_unit=repo_stats(rows,'full')
    sources=surface_metrics(rows)
    strata=pattern_standardized(rows,'full')
    ident=identification(rows,published)
    return {'source':'https://github.com/PurdueDualityLab/EMSE-perf-pr-study/tree/64432e0b6ed7791bbfa929c6c183fc76c75b5d58/analysis/classification_labels',
            'study':'Peng et al. arXiv 2610.03969 (Oct 2026)',
            'unit_and_repository':by_unit,'evidence_surfaces':sources,'patterns':strata,
            'identification':ident,'cluster_resampling':bootstrap_repo(rows,'full',seed,B=bootstrap_B),
            'certificates':{
                'observed_joint_eligibility':'IDENTIFIED_AS_RECORDED',
                'target_generalization':'NOT_IDENTIFIED_DIRECTION',
                'repository_weighting':'SCOPE_SENSITIVE',
                'paired_common_repositories':'DIFFERENT_TARGET_POPULATION',
                'performance_improvement':'OUTSIDE_MEASUREMENT',
                'agent_human_causal_effect':'OUTSIDE_MEASUREMENT'},
            'caveats':['human_candidate does not prove human authorship',
                       'metric signals are not measurements of achieved performance',
                       'claim of repository sensitivity differs from causal or general population inference',
                       'not an automated semantic paper reader','not a discovery of author error']}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--rq3',required=True)
    ap.add_argument('--out',default='stage5_results.json')
    ap.add_argument('--bootstrap',type=int,default=3000)
    ap.add_argument('--seed',type=int,default=20261010)
    args=ap.parse_args()
    result=audit(parse_csv(args.rq3),bootstrap_B=args.bootstrap,seed=args.seed)
    Path(args.out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    r=result['unit_and_repository'];print('PR pooled contrast',r['pooled_contrast'], 'repo equal',r['repo_equal_contrast'],'shared repo',r['shared_repo_equal_contrast']);print('Wrote',args.out)

if __name__=='__main__':main()
