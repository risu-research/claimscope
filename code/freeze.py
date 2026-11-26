#!/usr/bin/env python3
"""Recreate the fixed finite-population sampling design, with no network or outcome inputs."""
import csv, hashlib, json, math, collections
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
LABEL='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
WITNESS='9db6c426638e5f071f02b0ba28011b2f8bd398527c24f5c7ec496a01bc500be9'
ARMS=('agentic','human_candidate')
STRATA=('known_report_repo','other_positive_repo','no_published_positive_repo')
SIZES={'known_report_repo':None,'other_positive_repo':120,'no_published_positive_repo':200}
def sha(b):return hashlib.sha256(b).hexdigest()
def key(r):return (int(r['repo_id']),int(r['number']))
def repo(r):return '/'.join(urlsplit(r['html_url']).path.strip('/').split('/')[:2])
def read(n):return list(csv.DictReader((ROOT/n).open(encoding='utf-8-sig',newline='')))
def write(n,rows):
    with (ROOT/n).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def zero_upper(N,n,alpha):
    # One-sided exact upper endpoint for K, conditional on zero observed hits.
    den=math.comb(N,n)
    return max(K for K in range(N+1) if (math.comb(N-K,n)/den if N-K>=n else 0)>=alpha)
def tail_zero(N,n,K):
    return math.comb(N-K,n)/math.comb(N,n) if N-K>=n else 0
assert sha((ROOT/'rq3_labels.csv').read_bytes())==LABEL
assert sha((ROOT/'structured_ci_witnesses.csv').read_bytes())==WITNESS
seed=(ROOT/'seed.txt').read_text().strip();assert len(bytes.fromhex(seed))==32
allrows=read('rq3_labels.csv'); assert len(allrows)==2081 and len(set(map(key,allrows)))==2081
m=[r for r in allrows if r['in_metric_layer']=='True'];assert len(m)==1699
rsp=[r for r in m if repo(r).lower()=='web-infra-dev/rspack']; assert len(rsp)==97
ext=[r for r in m if r not in rsp]; pos=[r for r in ext if r['D6']=='True']; neg=[r for r in ext if r['D6']=='False'];assert len(pos)==70 and len(neg)==1532
assert collections.Counter(r['sample_arm'] for r in neg)=={'agentic':731,'human_candidate':801}
assert len({r['repo_id'] for r in m})==440
names={r['repo_id']:repo(r) for r in m}; assert all(names[r['repo_id']]==repo(r) for r in m)
posrepos={r['repo_id'] for r in pos};assert len(posrepos)==42
w=read('structured_ci_witnesses.csv'); assert len(w)==31 and all(r['before_cutoff']=='True' for r in w)
pmap={(repo(r),int(r['number'])):r for r in pos}
known={pmap[(r['repo'],int(r['number']))]['repo_id'] for r in w};assert len(known)==8 and known<=posrepos
cells=collections.defaultdict(list)
for r in neg:
    rid=r['repo_id']; st=STRATA[0] if rid in known else STRATA[1] if rid in posrepos else STRATA[2]
    cells[(r['sample_arm'],st)].append(r)
assert sum(len(v) for v in cells.values())==1532
frame=[]; design=[]
for arm in ARMS:
    for st in STRATA:
        rs=cells[arm,st];N=len(rs);n=SIZES[st] or N
        assert 0<n<=N
        # Independent 256-bit seed, fixed before new negative evidence retrieval.
        def rank(r):return sha(bytes.fromhex(seed)+f'|ClaimScope-R02A-v1|{arm}|{st}|{key(r)[0]}|{key(r)[1]}'.encode())
        ordered=sorted(rs,key=lambda r:(rank(r),key(r)))
        for i,r in enumerate(ordered,1):
            frame.append({'repo_id':r['repo_id'],'number':r['number'],'repo':repo(r),'html_url':r['html_url'],'arm':arm,'stratum':st,'published_D6':r['D6'],'validation_type':r['validation_type'],'pattern':r['pattern'],'rank_sha256':rank(r),'rank':i,'selected':int(i<=n),'inclusion_numerator':n,'inclusion_denominator':N})
        z=zero_upper(N,n,.05); zb=zero_upper(N,n,.05/4)
        design.append({'arm':arm,'stratum':st,'N':N,'n':n,'repositories':len({r['repo_id'] for r in rs}),'sample_repositories':len({r['repo_id'] for r in ordered[:n]}),'inclusion_probability':n/N,'weight':N/n,'zero_upper_K_95_one_sided':z,'zero_upper_rate_95_one_sided':z/N,'zero_upper_K_simultaneous_95':zb,'zero_upper_rate_simultaneous_95':zb/N,'prob_detect_at_least_one_if_1pct':1-tail_zero(N,n,math.ceil(.01*N)),'prob_detect_at_least_one_if_3pct':1-tail_zero(N,n,math.ceil(.03*N))})
frame.sort(key=lambda r:(r['arm'],r['stratum'],r['rank'])); selected=[r for r in frame if r['selected']];assert len(selected)==656
assert len({(r['repo_id'],r['number']) for r in frame})==1532
assert all(r['published_D6']=='False' for r in frame)
assert not ({(r['repo_id'],r['number']) for r in frame}&{(r['repo_id'],r['number']) for r in pos+rsp})
write('negative_frame.csv',frame);write('frozen_sample.csv',selected);write('stratum_design.csv',design)
repos=[]
for rid in sorted({r['repo_id'] for r in ext},key=int):
    rr=[r for r in ext if r['repo_id']==rid]; nn=[r for r in frame if r['repo_id']==rid]; ss=[r for r in nn if r['selected']]
    repos.append({'repo_id':rid,'repo':names[rid],'known_report_repo':int(rid in known),'published_positive_repo':int(rid in posrepos),'metric_total':len(rr),'positive_agentic':sum(r['D6']=='True' and r['sample_arm']=='agentic' for r in rr),'positive_human_candidate':sum(r['D6']=='True' and r['sample_arm']=='human_candidate' for r in rr),'negative_agentic':sum(r['arm']=='agentic' for r in nn),'negative_human_candidate':sum(r['arm']=='human_candidate' for r in nn),'selected_agentic':sum(r['arm']=='agentic' for r in ss),'selected_human_candidate':sum(r['arm']=='human_candidate' for r in ss)})
write('repository_inventory.csv',repos)
arm_summary={}
for arm in ARMS:
    ds=[d for d in design if d['arm']==arm];N=sum(d['N'] for d in ds);n=sum(d['n'] for d in ds);den=sum(r['sample_arm']==arm for r in m)
    # Bound on design variance of Horvitz-Thompson total for binary outcomes.
    # Finite-population S^2 <= floor(N^2/4)/(N*(N-1)).
    var=sum(d['N']**2*(1-d['n']/d['N'])/d['n']*(math.floor(d['N']**2/4)/(d['N']*(d['N']-1))) for d in ds if d['n']<d['N'])
    K=sum(d['zero_upper_K_simultaneous_95'] for d in ds)
    arm_summary[arm]={'negative_N':N,'sample_n':n,'original_metric_N':den,'sample_repositories':len({r['repo_id'] for r in selected if r['arm']==arm}),'worst_case_design_se_total':math.sqrt(var),'worst_case_design_se_rate':math.sqrt(var)/N,'illustrative_normal_95_halfwidth_pp':1.96*math.sqrt(var)/N*100,'zero_hits_joint_upper_K':K,'zero_hits_joint_upper_negative_rate':K/N,'zero_hits_joint_upper_original_denominator_pp':K/den*100}
summary={'label_sha256':LABEL,'witness_sha256':WITNESS,'seed':seed,'original_rows':len(allrows),'metric_rows':len(m),'excluded_metric_rows':len(allrows)-len(m),'excluded_metric_D6_positive':sum(r['D6']=='True' and r['in_metric_layer']!='True' for r in allrows),'metric_repositories':440,'non_rspack_repositories':len(repos),'negative_repositories':len({r['repo_id'] for r in frame}),'positive_repositories':len(posrepos),'positive_repositories_with_negatives':len({r['repo_id'] for r in frame if r['stratum']!=STRATA[2]}),'selected_repositories':len({r['repo_id'] for r in selected}),'known_report_repositories':len(known),'selected_total':len(selected),'negative_total':len(frame),'strata':design,'arms':arm_summary,'frame_sha256':sha((ROOT/'negative_frame.csv').read_bytes()),'sample_sha256':sha((ROOT/'frozen_sample.csv').read_bytes()),'largest_negative_repos':sorted([{'repo':r['repo'],'negative':r['negative_agentic']+r['negative_human_candidate']} for r in repos],key=lambda r:(-r['negative'],r['repo']))[:20]}
(ROOT/'design_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
