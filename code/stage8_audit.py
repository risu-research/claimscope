#!/usr/bin/env python3
"""Independent, fixed public-label reanalysis. Descriptive, not causal."""
import csv, collections, math, json, statistics, random, hashlib, argparse
from pathlib import Path

def load(path):
 raw=Path(path).read_bytes()
 rows=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
 actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 if actual!='136a2cf5bf1a9a71f06f2a7c6c9932194865c854':
  raise ValueError(f'Public CSV blob checksum mismatch: {actual}')
 eligible=[r for r in rows if r['in_metric_layer']=='True']
 if len(rows)!=2081 or len(eligible)!=1699: raise ValueError('Population mismatch')
 if len({(r['repo_id'],r['number']) for r in rows})!=len(rows): raise ValueError('Duplicate PR identity')
 return eligible

def run(rows, csv_path):
 A='agentic'; H='human_candidate'; R='476642602'
 def nrate(v,arm,d='D6'):
  a=[z for z in v if z['sample_arm']==arm]; return {'yes':sum(z[d]=='True' for z in a), 'n':len(a),'rate':sum(z[d]=='True' for z in a)/len(a) if a else None}
 def gap(v,d='D6'):return nrate(v,A,d)['rate']-nrate(v,H,d)['rate']
 rd=[]
 for dim in [f'D{i}' for i in range(10)]:
  g0=gap(rows,dim); without=[z for z in rows if z['repo_id']!=R]; g1=gap(without,dim)
  byrepo=collections.defaultdict(list)
  for z in rows:byrepo[z['repo_id']].append(z)
  shifts=[]
  for repo,subset in byrepo.items():
   rem=[z for z in rows if z['repo_id']!=repo]
   sh=g0-gap(rem,dim)
   shifts.append((repo,sh))
  shifts.sort(key=lambda x:(-abs(x[1]),x[0]))
  rank=1+sum(abs(v)>abs(g0-g1)+1e-12 for _,v in shifts)
  rd.append({'dimension':dim,'overall_pp':100*g0,'without_rspack_pp':100*g1,'rspack_influence_pp':100*(g0-g1), 'rspack_rank_by_abs_influence':rank, 'top_repository':shifts[0][0],'max_abs_influence_pp':100*abs(shifts[0][1])})
 def at(v, arm):return nrate([z for z in rows if (z['repo_id']==R)==v],arm)['rate']
 wa=nrate(rows,A)['n']; wh=nrate(rows,H)['n']
 pA=nrate([z for z in rows if z['repo_id']==R],A)['n']/wa
 pH=nrate([z for z in rows if z['repo_id']==R],H)['n']/wh
 rAR,rHR,rAO,rHO=at(True,A),at(True,H),at(False,A),at(False,H)
 comp=(pA-pH)*((rAR+rHR)/2-(rAO+rHO)/2)
 within=(pA+pH)/2*(rAR-rHR)+(1-(pA+pH)/2)*(rAO-rHO)
 assert abs(comp+within-gap(rows))<1e-12
 # Descriptive odds ratio stratified by Rspack; not causal
 cmh_num=cmh_den=0
 for v in (True,False):
  sub=[z for z in rows if (z['repo_id']==R)==v]
  a=nrate(sub,A);h=nrate(sub,H); n=a['n']+h['n']
  cmh_num+=a['yes']*(h['n']-h['yes'])/n
  cmh_den+=(a['n']-a['yes'])*h['yes']/n
 # Randomization sensitivity: shuffle agents at repo level? not valid. Bootstrap repos stratified: full vs non, two-stage.
 byrepo=collections.defaultdict(list)
 for z in rows:byrepo[z['repo_id']].append(z)
 keys=sorted(byrepo)
 rnd=random.Random(702027)
 samples=[]
 # 4000 draws clusters, then remove rspack if present.
 for _ in range(4000):
  keysdraw=[keys[rnd.randrange(len(keys))] for j in keys]
  v=[z for k in keysdraw for z in byrepo[k]]
  if all(any(z['sample_arm']==arm for z in v) for arm in (A,H)):
   samples.append(100*gap(v))
 samples.sort()
 def perc(v,p):return v[math.floor((len(v)-1)*p)]
 # bootstrap restricted without rspack
 nkeys=[k for k in keys if k!=R];nboot=[]
 for _ in range(4000):
  kdraw=[nkeys[rnd.randrange(len(nkeys))] for j in nkeys]
  v=[z for k in kdraw for z in byrepo[k]]
  if all(any(z['sample_arm']==arm for z in v) for arm in (A,H)):
   nboot.append(100*gap(v))
 nboot.sort()
 # Rspack and other arm split by unit source
 counts={'rspack':{arm:nrate([z for z in rows if z['repo_id']==R],arm) for arm in (A,H)},'other':{arm:nrate([z for z in rows if z['repo_id']!=R],arm) for arm in (A,H)}}
 return {'counts':counts,'decomposition':{'overall_pp':100*gap(rows),'composition_pp':100*comp,'within_stratum_pp':100*within,'composition_share_of_observed_gap_pct':100*comp/gap(rows),'p_rspack':{A:pA,H:pH},'difference_identity_residual':comp+within-gap(rows),'MH_common_odds_ratio':cmh_num/cmh_den},'dimensions':rd, 'repo_bootstrap_descriptive':{'seed':702027,'B':4000,'all_95pp':[perc(samples,.025),perc(samples,.975)],'outside_rspack_95pp':[perc(nboot,.025),perc(nboot,.975)],'note':'cluster-resampling stability conditional on observed repos; no population-level CI'},'source_git_blob_sha1':hashlib.sha1(b'blob '+str(Path(csv_path).stat().st_size).encode()+b'\0'+Path(csv_path).read_bytes()).hexdigest()}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--csv',default='rq3_labels.csv');p.add_argument('--output',default='stage8_audit.json');args=p.parse_args();out=run(load(args.csv),args.csv);Path(args.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
