"""Independent count-space sensitivity calculations using fixed outcome labels."""
import csv, io, zipfile, json, math, itertools, tempfile, subprocess, sys, hashlib, collections, functools
from fractions import Fraction as F
from pathlib import Path
R=Path(__file__).resolve().parent
class Inputs:
 def read(self,name):return (R/name).read_bytes()
z=c=Inputs()
read=lambda b:list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')))); rows=read(z.read('audited_prs.csv')); key=lambda r:(r['repo_id'],r['number'])
A,H='agentic','human_candidate';N={A:858,H:841}; base=F(100*115,858)-F(100*38,841)
# Re-run original freeze using original source code/seed and check all five outputs.
with tempfile.TemporaryDirectory() as t:
 p=Path(t)
 for f in ['freeze.py','rq3_labels.csv','structured_ci_witnesses.csv','seed.txt']:(p/f).write_bytes(c.read(f))
 subprocess.run([sys.executable,'freeze.py'],cwd=p,check=True,stdout=subprocess.DEVNULL)
 verified=['negative_frame.csv','frozen_sample.csv','stratum_design.csv','design_summary.json','repository_inventory.csv']
 assert all((p/f).read_bytes()==c.read(f) for f in verified)
# Independent recurrence for tail decision; original single-definition code's floating point is checked at primary alpha.
@functools.lru_cache(None)
def tail_num(N,K,n,x,upper):
 lo=max(0,n+K-N);hi=min(n,K)
 w=math.comb(K,lo)*math.comb(N-K,n-lo);total=0
 for j in range(lo,hi+1):
  if (j>=x if upper else j<=x):total+=w
  if j<hi:
   q=w*(K-j)*(n-j);d=(j+1)*(N-K-n+j+1);assert q%d==0;w=q//d
 return total
@functools.lru_cache(None)
def iv(N,n,k,u,den):
 if n==N:return (k,k+u)
 norm=math.comb(N,n);lo=0;hi=N
 while lo<hi:
  mid=(lo+hi)//2
  if den*tail_num(N,mid,n,k,True)>=norm:hi=mid
  else:lo=mid+1
 L=lo;lo=0;hi=N
 while lo<hi:
  mid=(lo+hi+1)//2
  if den*tail_num(N,mid,n,k+u,False)>=norm:lo=mid
  else:hi=mid-1
 return L,lo
# Combine 167 certainty observations and 6 original C1 strata.
by=collections.defaultdict(list)
for r in rows:by[r['arm'],r['stratum']].append(r)
def status(r,e):
 if e!='broad_only':return r[e]
 if r['broad']=='unknown':return 'unknown'
 return 'positive' if r['broad']=='positive' and r['whole_artifact']=='no_observed_report' else 'no_observed_report'
def cells(e):
 out=[]
 for (a,s),v in sorted(by.items()):
  n=len(v);NN=n if v[0]['design']=='census' else int(v[0]['inclusion_denominator']);k=sum(status(r,e)=='positive' for r in v);u=sum(status(r,e)=='unknown' for r in v);out.append((a,s,NN,n,k,u))
 return out
def calc(e,den):
 lower=upper=htl=hth=F(0);arms={}
 for a in [A,H]:
  countL=countU=0;hL=hU=F(0)
  for aa,s,NN,n,k,u in cells(e):
   if aa!=a:continue
   L,U=iv(NN,n,k,u,den);countL+=L;countU+=U;hL+=F(NN*k,n);hU+=F(NN*(k+u),n)
  arms[a]=dict(N=N[a],L=countL,U=countU,HTL=float(hL),HTU=float(hU))
  q=F(100,N[a]);lower+=q*(countL if a==A else -countU);upper+=q*(countU if a==A else -countL);htl+=q*(hL if a==A else -hU);hth+=q*(hU if a==A else -hL)
 return dict(endpoint=e,tail_denominator=den,HT_low=float(htl),HT_high=float(hth),CI_low=float(lower),CI_high=float(upper),arms=arms)
independent=[calc(e,d) for e in ['broad','whole_artifact'] for d in [160,320,480]]+[calc('broad_only',480)]
orig=list(csv.DictReader(open(R/'domain_contrasts.csv')))
for r in independent:
 if r['tail_denominator'] not in (160,320):continue
 x=next(x for x in orig if x['domain']=='all' and x['endpoint']==r['endpoint']);f='endpoint95' if r['tail_denominator']==160 else 'joint95';assert abs(r['CI_low']-float(x[f+'_low']))<1e-10 and abs(r['CI_high']-float(x[f+'_high']))<1e-10
# Worst adverse per-row relabeling, with fixed design and unknown counts allowed to resolve adversarially.
# For upper bound: increase A possible positives (observed no -> positive), decrease H certain positives.
# For lower bound: decrease A certain positives, increase H possible positives. Each change edits one observed PR.
# Dynamic programming over cells; within cell, extreme effect at a given edit count is monotone.
def stress(e,side,target,max_edits=40):
 den=320; dp={0:(F(0),[])}
 for a,s,NN,n,k,u in cells(e):
  increase=(side=='upper' and a==A) or (side=='lower' and a==H)
  cap=n-k-u if increase else k
  options=[]
  for m in range(min(cap,max_edits)+1):
   kk=k+m if increase else k-m; L,U=iv(NN,n,kk,u,den);v=F(100,N[a])*(U if a==A and side=='upper' else L if a==A else -L if side=='upper' else -U)
   options.append((m,v))
  nxt={}
  for i,(v,path) in dp.items():
   for m,w in options:
    if i+m>max_edits:continue
    q=v+w;j=i+m
    if j not in nxt or (q>nxt[j][0] if side=='upper' else q<nxt[j][0]):nxt[j]=(q,path+([(a,s,m)] if m else []))
  dp=nxt
 cross=next((i for i,(v,p) in sorted(dp.items()) if (v>=target if side=='upper' else v<=target)),None)
 assert cross is not None
 return dict(endpoint=e,side=side,target=float(target),minimum_adverse_relabels=cross,initial_bound=float(dp[0][0]),last_surviving_bound=float(dp[cross-1][0]) if cross else None,first_failing_bound=float(dp[cross][0]),witness_cells=dp[cross][1],one_edit_bound=float(dp[1][0]),definition='Hypothetical endpoint-label changes, one edited observed PR per change; no empirical error-rate inference. Opposing endpoint can be adjusted consistently with nesting.')
stresses=[stress('broad','upper',base,8),stress('whole_artifact','lower',F(0),30)]
# A more stringent third endpoint family: directly measure broad-only contrast with 24-tail Bonferroni.
# broad_only gap = broad gap minus whole gap; same PR nesting enforced for known observed labels.
# Its unknown count is deliberately pessimistic, so no claim of equal outcome when both unknown.
result=dict(freeze_outputs_verified=verified,independent_count_calculations=independent,adverse_relabeling=stresses,observed_broad_only_by_arm=dict(collections.Counter(r['arm'] for r in rows if status(r,'broad_only')=='positive')))
(R/'stress_summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
