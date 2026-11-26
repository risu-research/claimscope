import csv, hashlib, io, json, zipfile, math, collections, itertools, functools, random
from fractions import Fraction as F
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda b:list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
key=lambda r:(r['repo_id'],r['number'])
A,H='agentic','human_candidate'; arms=(A,H); endpoints=('broad','whole_artifact'); RSP='476642602'; ESP='128479644'; EMB={ESP,'15337142','6860771'}
def write(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r));
    with (R/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def js(name,data): (R/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def zread(z,n):return read(z.read(n))
class Inputs:
    def read(self,name): return (R/name).read_bytes()
z=c1=c3=Inputs()
assert sha(z.read('rq3_labels.csv'))=='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
assert sha(c1.read('frozen_sample.csv'))=='530fb02b8eca1a8ca5c2152080eb7e8b0b823d60d59cdbd1b4bcc34304c7abe6'
assert sha(c1.read('negative_frame.csv'))=='92a40c4d90ed6c8faf187c90c43261ee9c01a602c5ef860e05e9709a8df49a30'
labels=zread(z,'rq3_labels.csv');assert len(labels)==len(set(map(key,labels)))==2081
P={key(r):r for r in labels if r['in_metric_layer']=='True'};assert len(P)==1699
I={key(r):r for r in zread(z,'audited_prs.csv')}; assert len(I)==823
C={key(r):r for r in zread(z,'census_outcomes.csv')};S={key(r):r for r in zread(c1,'sample_outcomes.csv')};D={key(r):r for r in zread(c1,'frozen_sample.csv')};Frame={key(r):r for r in zread(c1,'negative_frame.csv')}
assert len(C)==167 and len(S)==656 and S.keys()==D.keys() and not C.keys()&S.keys() and C.keys()|S.keys()==I.keys()
assert C.keys()=={k for k,r in P.items() if r['D6']=='True' or k[0]==RSP}
assert Frame.keys()==P.keys()-C.keys();assert len(Frame)==1532
assert all(r['selected']=='1' for r in D.values()) and set(D)=={k for k,r in Frame.items() if r['selected']=='1'}
for k,r in I.items():
    source=(C if k in C else S)[k]
    assert all(r[f]==source[f] for f in ('arm','published_D6',*endpoints))
    assert r['arm']==P[k]['sample_arm'] and r['published_D6']==P[k]['D6']
    assert (r['broad'],r['whole_artifact']) in {('positive','positive'),('positive','no_observed_report'),('no_observed_report','no_observed_report'),('unknown','unknown')}
    if k in S:assert all(r[f]==D[k][f]==Frame[k][f] for f in ('stratum','inclusion_numerator','inclusion_denominator'))
    else:assert r['inclusion_numerator']==r['inclusion_denominator']=='1'
strata=collections.defaultdict(list)
for k,r in Frame.items():strata[r['arm'],r['stratum']].append(k)
for (a,s),ks in strata.items():
    n=sum(k in S for k in ks);N=len(ks);assert all(int(I[k]['inclusion_numerator'])==n and int(I[k]['inclusion_denominator'])==N for k in ks if k in S)
assert len(strata)==6
# Exact tails by integers (no floating point tail decision).
@functools.lru_cache(None)
def tail(N,K,n,x,upper):
    lo=max(0,n-(N-K));hi=min(n,K)
    if upper:lo=max(lo,x)
    else:hi=min(hi,x)
    return F(sum(math.comb(K,i)*math.comb(N-K,n-i) for i in range(lo,hi+1)),math.comb(N,n))
@functools.lru_cache(None)
def interval(N,n,k,u,alpha):
    assert 0<=k<=k+u<=n<=N
    if n==N:return k,k+u
    if n==0:return 0,N
    lo,hi=0,N
    while lo<hi:
        m=(lo+hi)//2
        if tail(N,m,n,k,True)>=alpha:hi=m
        else:lo=m+1
    L=lo;lo,hi=0,N
    while lo<hi:
        m=(lo+hi+1)//2
        if tail(N,m,n,k+u,False)>=alpha:lo=m
        else:hi=m-1
    return L,lo
# Independent original code comparison (original single-definition calculation).
namespace={'__file__':str(R/'estimate.py'),'__name__':'single_definition_import'};exec(compile(c1.read('estimate.py'),'estimate.py','exec'),namespace)
alpha={'endpoint95':F(1,160),'joint95':F(1,320)}
cellrows=[]; limits={}; old={e:json.loads(c1.read('single_definition_broad.json' if e=='broad' else 'single_definition_whole.json')) for e in endpoints}
for e in endpoints:
 for st,ks in sorted(strata.items()):
    N=len(ks);obs=[I[k][e] for k in ks if k in I];n=len(obs);k=obs.count('positive');u=obs.count('unknown');r=dict(endpoint=e,arm=st[0],stratum=st[1],N=N,n=n,positive=k,unknown=u,no_observed=n-k-u,HT_low=float(F(N*k,n)),HT_high=float(F(N*(k+u),n)))
    for mode,a in alpha.items():
        L,U=interval(N,n,k,u,a);limits[e,mode,st]=(L,U);r[mode+'_low']=L;r[mode+'_high']=U
        if mode=='endpoint95':
            assert (L,U)==namespace['interval'](N,n,k,u)
            x=next(x for x in old[e]['cells'] if (x['arm'],x['stratum'])==st);assert (L,U)==(x['simultaneous_lower_K'],x['simultaneous_upper_K'])
    cellrows.append(r)
write('stratum_inference.csv',cellrows)
# Optimize a linear contrast over the known positive counts and possible unresolved/unsampled cases.
# Each cell fixes all observed non-unknown labels, and allows total K within its interval.
# Sorted allocation is exact for a linear objective with unit binary outcomes and one cardinality interval.
def choose(cs,l,u,maximum):
    assert 0<=l<=u<=len(cs)
    v=sorted(cs,reverse=maximum);n_good=sum(x>0 if maximum else x<0 for x in v)
    return sum(v[:max(l,min(u,n_good))],F(0))
def bounds(e,coef,mode):
    lo=hi=F(0)
    for k in C:
        v=coef.get(k,F(0));x=I[k][e]
        if x=='positive':lo+=v;hi+=v
        elif x=='unknown':lo+=min(v,0);hi+=max(v,0)
    for st,ks in strata.items():
        p=[k for k in ks if k in I and I[k][e]=='positive'];f=[coef.get(k,F(0)) for k in ks if k not in I or I[k][e]=='unknown'];b=sum((coef.get(k,F(0)) for k in p),F(0));lo+=b;hi+=b
        L,U=(len(p),len(p)+len(f)) if mode=='logical' else limits[e,mode,st]
        l=max(0,L-len(p));u=min(len(f),U-len(p));assert l<=u
        lo+=choose(f,l,u,False);hi+=choose(f,l,u,True)
    return lo,hi
def ht(e,coef):
    lo=hi=F(0)
    for k,r in I.items():
        v=coef.get(k,F(0))*F(int(r['inclusion_denominator']),int(r['inclusion_numerator']))
        if r[e]=='positive':lo+=v;hi+=v
        elif r[e]=='unknown':lo+=min(v,0);hi+=max(v,0)
    return lo,hi
# Exhaustive small optimization tests and exact-tail inversion checks.
count=0
rng=random.Random(1729)
for n in range(0,8):
 for _ in range(12):
    v=[F(rng.randrange(-5,6),rng.randrange(1,6)) for j in range(n)]
    for l in range(n+1):
     for u in range(l,n+1):
        vals=[sum((v[j] for j in subset),F(0)) for i in range(l,u+1) for subset in itertools.combinations(range(n),i)]
        assert choose(v,l,u,False)==min(vals) and choose(v,l,u,True)==max(vals);count+=1
for N in range(1,15):
 for n in range(N+1):
  for k in range(n+1):
   for u in range(n-k+1):
    for a in alpha.values():
        L,U=interval(N,n,k,u,a)
        assert L==min(K for K in range(N+1) if tail(N,K,n,k,True)>=a) and U==max(K for K in range(N+1) if tail(N,K,n,k+u,False)>=a)
        count+=1
# Generic derived contrast results; confidence event shared across all derived contrasts.
def result(e,coef):
    out={}
    for name,b in [('HT',ht(e,coef))]+[(m,bounds(e,coef,m)) for m in (*alpha,'logical')]:
        out.update({name+'_low':float(b[0]),name+'_high':float(b[1])})
    return out
N=collections.Counter(r['sample_arm'] for r in P.values()); assert N=={A:858,H:841}
repoarms=collections.defaultdict(collections.Counter)
for k,r in P.items():repoarms[k[0]][r['sample_arm']]+=1
shared={k for k,v in repoarms.items() if len(v)==2};assert len(repoarms)==440 and len(shared)==84
allkeys=set(P)
def domain_coeff(ks,den=None):
    counts=collections.Counter(P[k]['sample_arm'] for k in ks);den=counts if den is None else den
    return {k:F(100 if P[k]['sample_arm']==A else -100,den[P[k]['sample_arm']]) for k in ks},counts
def original(coef):return float(sum((v for k,v in coef.items() if P[k]['D6']=='True'),F(0)))
def domainrow(name,ks,e):
    co,ns=domain_coeff(ks);r=dict(domain=name,endpoint=e,N_A=ns[A],N_H=ns[H],original_gap_pp=original(co),**result(e,co))
    # Conditional domain-specific exact intervals, separately (not jointly valid across chosen domains).
    low=high=F(0);condlo=condhi=F(0);sample_zero=0
    for a in arms:
        sgn=F(100 if a==A else -100,ns[a]);c=[k for k in ks if k in C and P[k]['sample_arm']==a];p=sum(I[k][e]=='positive' for k in c);u=sum(I[k][e]=='unknown' for k in c);L=p;U=p+u;hl=F(p);hu=F(p+u)
        for (aa,st),full in strata.items():
            if aa!=a:continue
            dom=[k for k in full if k in ks];obs=[I[k][e] for k in dom if k in I];nn=len(obs);NN=len(dom);kk=obs.count('positive');uu=obs.count('unknown');l,h=interval(NN,nn,kk,uu,alpha['endpoint95']);L+=l;U+=h
            if nn:hl+=F(NN*kk,nn);hu+=F(NN*(kk+uu),nn)
            elif NN:sample_zero+=NN;hu+=NN
        low+=min(sgn*L,sgn*U);high+=max(sgn*L,sgn*U);condlo+=min(sgn*hl,sgn*hu);condhi+=max(sgn*hl,sgn*hu)
    r.update(conditional95_low=float(low),conditional95_high=float(high),conditional_est_low=float(condlo),conditional_est_high=float(condhi),conditional_unsampled_cell_population=sample_zero)
    return r
domains={'all':allkeys,'without_rspack':{k for k in P if k[0]!=RSP},'without_esphome':{k for k in P if k[0]!=ESP},'without_embedded_trio':{k for k in P if k[0] not in EMB},'without_rspack_esphome':{k for k in P if k[0] not in {RSP,ESP}},'without_rspack_embedded_trio':{k for k in P if k[0] not in EMB|{RSP}},'shared_repos':{k for k in P if k[0] in shared},'shared_without_rspack':{k for k in P if k[0] in shared-{RSP}}}
domainrows=[domainrow(name,ks,e) for name,ks in domains.items() for e in endpoints];write('domain_contrasts.csv',domainrows)
armrows=[]
for e in endpoints:
 for a in arms:
    ks={k for k in P if P[k]['sample_arm']==a};co={k:F(1) for k in ks};r=result(e,co);armrows.append(dict(endpoint=e,arm=a,N=N[a],original_positive=sum(P[k]['D6']=='True' for k in ks),**r,**{f'{k}_pct':v*100/N[a] for k,v in r.items()}))
write('arm_estimates.csv',armrows)
# Additive decomposition in fixed original denominator. D6 published positives form baseline.
fullco,_=domain_coeff(allkeys);decomp=[]
for e in endpoints:
 for name,ks in [('original_positive_reclassification',{k for k in P if P[k]['D6']=='True'}),('rspack_negative_addition',{k for k in P if k[0]==RSP and P[k]['D6']=='False'}),('non_rspack_negative_expansion',set(Frame)),('total',allkeys),('rspack_contribution',{k for k in P if k[0]==RSP}),('non_rspack_contribution',{k for k in P if k[0]!=RSP})]:
    co={k:fullco[k] for k in ks};orig=original(co);out=result(e,co);decomp.append(dict(endpoint=e,component=name,original_gap_contribution=orig,**out,**{'change_'+k:v-orig for k,v in out.items()}))
write('gap_decomposition.csv',decomp)
# Pooled/equal shared-repository weights: finite common-support descriptive contrasts, not causal.
std=[]
for ex in [False,True]:
    ids=shared-{RSP} if ex else shared;total=sum(sum(repoarms[r].values()) for r in ids)
    for kind in ['pooled_PR','equal_repository']:
        co={k:F(100 if P[k]['sample_arm']==A else -100,repoarms[k[0]][P[k]['sample_arm']])*(F(sum(repoarms[k[0]].values()),total) if kind=='pooled_PR' else F(1,len(ids))) for k in P if k[0] in ids}
        for e in endpoints:std.append(dict(scope='shared_without_rspack' if ex else 'shared',weighting=kind,repositories=len(ids),endpoint=e,original_gap_pp=original(co),**result(e,co)))
write('repository_standardization.csv',std)
# Exact population-weighted two-domain decomposition: symmetric Kitagawa decomposition.
kit=[]
wa=F(repoarms[RSP][A],N[A]);wh=F(repoarms[RSP][H],N[H]);w=(wa+wh)/2
for e in endpoints:
    within={};comp={}
    for k in P:
        a=P[k]['sample_arm'];rsp=k[0]==RSP;den=repoarms[RSP][a] if rsp else N[a]-repoarms[RSP][a]
        within[k]=F(100 if a==A else -100,den)*(w if rsp else 1-w)
        comp[k]=F(100,den)*(wa-wh)/2*(1 if rsp else -1)
        assert within[k]+comp[k]==fullco[k]
    for name,co in [('within_two_domains',within),('composition_two_domains',comp)]:kit.append(dict(endpoint=e,component=name,original_gap_pp=original(co),**result(e,co)))
write('two_domain_decomposition.csv',kit)
# All leave-one-repository-out, inherited simultaneous event (no post-selection testing).
loo=[]
for rid in sorted(repoarms,key=int):
    ks={k for k in P if k[0]!=rid};co,ns=domain_coeff(ks)
    for e in endpoints:loo.append(dict(repo_id=rid,repo=next(r['html_url'].split('/pull/')[0].split('github.com/')[1] for k,r in P.items() if k[0]==rid),endpoint=e,N_A=ns[A],N_H=ns[H],original_gap_pp=original(co),**result(e,co)))
write('leave_one_repository_out.csv',loo)
# Deterministic Rspack census checks, independent of probability-sample inference.
rs=[r for k,r in I.items() if k[0]==RSP];order=zread(z,'rspack_report_order.csv');replay=zread(z,'census_replay.csv');rp={key(r):r for r in replay};assert len(rs)==len(order)==97
assert all(r['current_D6']==I[key(r)]['published_D6'] for r in replay if r['current_D6'] in ('True','False'))
prov=zread(c3,'rspack_match_labels.csv');assert len(prov)==133
ordcounts=collections.Counter((r['both_reports'],r['intervening_count'],r['published_D6']) for r in order)
rsrows=[]
for a in arms:
    v=[r for r in rs if r['arm']==a];rsrows.append(dict(arm=a,N=len(v),published_positive=sum(r['published_D6']=='True' for r in v),semantic_positive=sum(r['broad']=='positive' for r in v),atomic_positive=sum(int(rp[key(r)]['atomic_D6'])>0 for r in v),joined_positive=sum(int(rp[key(r)]['joined_D6'])>0 for r in v)))
write('rspack_arm_census.csv',rsrows)
write('report_order_counts.csv',[dict(both_reports=k[0],intervening_count=k[1],published_D6=k[2],n=v) for k,v in sorted(ordcounts.items())])
# Endpoint contrast: broad-only (known nested outcomes); both unknown imply broad-only unknown.
# Re-use conservative joint marginal gaps for the difference, plus direct HT on nested pairs.
# This is not an additional independently protected endpoint.
# Report logical bounds and contrast of estimates separately, not mistaken for CI.
summary=dict(metric_N=len(P),audited_N=len(I),population_repositories=len(repoarms),shared_repositories=len(shared),optimization_and_inversion_tests=count,original_gap_pp=original(fullco),primary=domainrows[:2],rspack=rsrows,observed_endpoint_pairs={str(k):v for k,v in collections.Counter((r['broad'],r['whole_artifact']) for r in I.values()).items()},loo={e:{'HT_low_min':min(r['HT_low'] for r in loo if r['endpoint']==e),'HT_high_max':max(r['HT_high'] for r in loo if r['endpoint']==e),'joint95_excludes_zero_positive':sum(r['joint95_low']>0 for r in loo if r['endpoint']==e),'joint95_excludes_zero_negative':sum(r['joint95_high']<0 for r in loo if r['endpoint']==e)} for e in endpoints})
js('summary.json',summary);print(json.dumps(summary,indent=2))
