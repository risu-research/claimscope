import csv, json, random, collections, statistics, pathlib, hashlib
p=pathlib.Path(__file__).parent
raw=(p/'rq3_labels.csv').read_bytes(); rows=[r for r in csv.DictReader(raw.decode().splitlines()) if r['in_metric_layer']=='True']; assert len(rows)==1699 and len({(r['repo_id'],r['number']) for r in rows})==1699
repos=collections.defaultdict(list)
for r in rows:repos[r['repo_id']].append(r)
assert len(repos)==440
R=next(k for k,v in repos.items() if '/rspack/pull/' in v[0]['html_url']); A='agentic'; H='human_candidate'
def counts(rs,key='D6'):
 return tuple(sum(r['sample_arm']==g and (r[key]=='True' if positive else True) for r in rs) for g in [A,H] for positive in [True,False])
def gap(c):return 100*(c[0]/c[1]-c[2]/c[3])
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
base=counts(rows); rc=counts(repos[R]); other=sub(base,rc); assert base==(115,858,38,841) and rc==(76,88,7,9)
scan=[]
for i in range(10):
 key='D'+str(i); b=counts(rows,key); shifts=sorted([(abs(gap(b)-gap(sub(b,counts(rs,key)))),k) for k,rs in repos.items()],reverse=True); scan.append({'metric':key,'rspack_shift':gap(b)-gap(sub(b,counts(repos[R],key))),'rspack_rank':next(i+1 for i,(_,k) in enumerate(shifts) if k==R),'max_shift':shifts[0][0],'second_shift':shifts[1][0]})
nd=counts(rows,'D6_nodiff'); ndr=counts(repos[R],'D6_nodiff'); assert nd==(107,858,34,841) and ndr==rc
shared=[counts(rs) for rs in repos.values() if all(counts(rs)[i]>0 for i in (1,3))]
thresholds={str(t):{'repos':len(c:=[v for v in shared if min(v[1],v[3])>=t]),'gap':statistics.mean(map(gap,c))} for t in (1,2,3,5)}
refs=[100*(rc[1]/base[1]-rc[3]/base[3])*(rc[i]/rc[i+1]-other[i]/other[i+1])/gap(base)*100 for i in (0,2)]
# fixed fresh paired repository bootstrap, same draw applied to both arms; percentile endpoints via linear interpolation
rng=random.Random(20261125); cells=[counts(repos[k]) for k in sorted(repos,key=int)]; vals=[]
for _ in range(12000):
 c=[0]*4
 for k in rng.choices(range(440),k=440):
  for j in range(4):c[j]+=cells[k][j]
 if c[1] and c[3]:vals.append(gap(c))
assert len(vals)==12000
vals.sort()
def q(p):
 x=(len(vals)-1)*p;i=int(x);return vals[i]+(x-i)*(vals[i+1]-vals[i])
out={'label_sha256':hashlib.sha256(raw).hexdigest(),'cohort':base,'rspack':rc,'other':other,'scan':scan,'nodiff':nd,'nodiff_rspack':ndr,'nodiff_gap':gap(nd),'nodiff_other_gap':gap(sub(nd,ndr)),'shared_thresholds':thresholds,'reference_composition_shares':refs,'bootstrap':{'seed':20261125,'reps':len(vals),'p025':q(.025),'p975':q(.975)}}
(p/'legacy_audit.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2))
