#!/usr/bin/env python3
"""R01-B1: current public six-channel replay of fixed non-Rspack D6 positives.
No source text is published: retain per-record hashes, identifiers, match counts,
and compact cue/quant witnesses. Historical snapshot remains unavailable.
"""
import collections, concurrent.futures, csv, datetime, hashlib, json, os, re, time
from pathlib import Path
from urllib.parse import urlsplit, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from audit_rspack_11_exact import load_original_extractor, BLOB_SHAS, PIN

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
HASH='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
CUT='2026-08-27T22:00:14Z'
CHANNELS=('description','issue_comments','review_comments','commit_messages','ci_metadata','code_diff')
TOKEN=os.environ.get('GITHUB_TOKEN','')
extract=load_original_extractor()

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z','+00:00')) if s else None
def late(s):
    return bool(s and dt(s)>dt(CUT))
def get(path,params=None):
    url='https://api.github.com'+path+('?' + urlencode(params) if params else '')
    h={'Accept':'application/vnd.github+json','User-Agent':'claimscope-r01b1','X-GitHub-Api-Version':'2022-11-28'}
    if TOKEN: h['Authorization']='Bearer '+TOKEN
    for k in range(3):
        try:
            with urlopen(Request(url,headers=h),timeout=30) as r:
                return json.load(r),r.headers.get('Link','')
        except HTTPError as e:
            if e.code in (429,500,502,503,504) and k<2:
                time.sleep(min(12,2**k));continue
            raise RuntimeError('HTTP '+str(e.code)+' '+path) from None
    raise RuntimeError('request failed')
def pages(path,params=None,key=None):
    allrows=[]
    for page in range(1,41):
        obj,link=get(path,{**(params or {}),'per_page':100,'page':page})
        batch=obj[key] if key else obj
        if not isinstance(batch,list): raise ValueError('invalid list')
        allrows.extend(batch)
        if 'rel="next"' not in link:
            if len(batch)==100: # do not assume a full page is final
                continue
            return allrows
    raise RuntimeError('pagination cap')
def rec(t,identity,url,actor=None,typ=None,created=None,updated=None):
    return {'text':t,'id':identity,'url':url,'actor':actor,'type':typ,'created':created,'updated':updated}
def inspect(items):
    available=[x for x in items if x['text'] is not None]
    joined='\n'.join(str(x['text']) for x in available)
    def hits(t): return extract(t,include_positions=True).get('D6',[])
    def short(h): return {k:h.get(k) for k in ('rule_id','cue','quant','quant_kind')}
    j=hits(joined)
    separate=[]
    for x in items:
        t=x['text']; a=hits(str(t)) if t is not None else []
        separate.append({**{k:v for k,v in x.items() if k!='text'},'sha256':sha(str(t)) if t is not None else None,
                         'length':len(str(t)) if t is not None else None,'n_hits':len(a),
                         'witnesses':[short(h) for h in a[:2]],'late':late(x['created']) or late(x['updated'])})
    padded=hits(('\n'+' '.join(['zzcommentboundary']*32)+'\n').join(str(x['text']) for x in available))
    return {'records':len(items),'null_records':len(items)-len(available),'joined_sha256':sha(joined),
            'joined_D6':bool(j),'joined_hits':len(j),'joined_witnesses':[short(h) for h in j[:4]],
            'atomic_D6':any(x['n_hits'] for x in separate),'padded_D6':bool(padded),
            'record_manifest':separate}
def positive(v): return v.lower()=='true'
def repo_of(r): return '/'.join(urlsplit(r['html_url']).path.strip('/').split('/')[:2])
def one(r):
    repo=repo_of(r); n=int(r['number']); rid=int(r['repo_id']); base='/repos/'+repo
    result={'repo':repo,'number':n,'repo_id':rid,'arm':r['sample_arm'],'published_D6':True,
            'published_nodiff':positive(r['D6_nodiff']),'channels':{},'errors':{}}
    try:
        try: p,_=get(base+'/pulls/'+str(n))
        except RuntimeError: p,_=get('/repositories/'+str(rid)+'/pulls/'+str(n))
        if p['number']!=n or p['base']['repo']['id']!=rid: raise ValueError('identity mismatch')
        canonical=p['base']['repo']['full_name'];base='/repos/'+canonical
        result.update(canonical_repo=canonical,head_sha=p['head']['sha'],base_sha=p['base']['sha'],
                      pr_updated=p.get('updated_at'),pr_actor=p['user']['login'])
    except Exception as e:
        result['errors']['PR']=str(e);return result
    u=p['html_url']; q='/pulls/'+str(n)
    description='\n'.join(str(x) for x in (p.get('title'),p.get('body')) if x is not None)
    result['channels']['description']=inspect([rec(description,n,u,p['user']['login'],p['user']['type'],p.get('created_at'),None)])
    result['channels']['description']['pr_update_after_cutoff']=late(p.get('updated_at'))
    jobs=[('issue_comments',base+'/issues/'+str(n)+'/comments',None,None,p.get('comments')),
          ('review_comments',base+q+'/comments',None,None,p.get('review_comments')),
          ('commit_messages',base+q+'/commits',None,None,p.get('commits')),
          ('code_diff',base+q+'/files',None,None,p.get('changed_files')),
          ('ci_metadata',base+'/actions/runs',{'event':'pull_request','head_sha':p['head']['sha']},'workflow_runs',None)]
    for ch,path,params,key,expected in jobs:
        try:
            a=pages(path,params,key)
            if ch=='ci_metadata': a=[x for x in a if x.get('head_sha')==p['head']['sha']]
            items=[]
            for x in a:
                if ch in ('issue_comments','review_comments'):
                    user=x.get('user') or {}
                    items.append(rec(x.get('body'),x['id'],x.get('html_url'),user.get('login'),user.get('type'),x.get('created_at'),x.get('updated_at')))
                elif ch=='commit_messages':
                    c=x['commit'];actor=x.get('author') or {}
                    items.append(rec(c.get('message'),x['sha'],x.get('html_url'),actor.get('login'),actor.get('type'),(c.get('committer') or {}).get('date')))
                elif ch=='code_diff':
                    items.append(rec(x.get('patch'),x['filename'],x.get('blob_url')))
                else:
                    items.append(rec(x.get('name'),x['id'],x.get('html_url'),created=x.get('created_at'),updated=x.get('updated_at')))
            s=inspect(items);s['expected_count']=expected;s['count_matches']=expected is None or expected==len(a)
            result['channels'][ch]=s
            if not s['count_matches']: result['errors'][ch]='metadata count mismatch'
            if s['null_records']: result['errors'][ch]='null source text present'
        except Exception as e: result['errors'][ch]=str(e)
    def anyflag(chs,field='joined_D6'):
        return any(result['channels'].get(ch,{}).get(field,False) for ch in chs)
    result['current_D6']=anyflag(CHANNELS)
    result['current_nodiff']=anyflag(CHANNELS[:-1])
    result['issue_boundary_only']=bool(result['channels'].get('issue_comments',{}).get('joined_D6') and not result['channels']['issue_comments']['atomic_D6'] and not result['channels']['issue_comments']['padded_D6'])
    result['current_boundary_preserved']=anyflag([ch for ch in CHANNELS if ch!='issue_comments']) or anyflag(['issue_comments'],'atomic_D6')
    result['all_channels_retrieved']=len(result['channels'])==6
    result['all_channels_clean']=result['all_channels_retrieved'] and not result['errors']
    return result
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH,'label hash mismatch'
    rows=[r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines()) if positive(r['in_metric_layer']) and positive(r['D6']) and repo_of(r).lower()!='web-infra-dev/rspack']
    assert len(rows)==70 and len({(r['repo_id'],r['number']) for r in rows})==70
    assert collections.Counter(r['sample_arm'] for r in rows)=={'agentic':39,'human_candidate':31}
    assert sum(not positive(r['D6_nodiff']) for r in rows)==12
    assert len({r['repo_id'] for r in rows})==42
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for f in concurrent.futures.as_completed([pool.submit(one,r) for r in rows]):
            v=f.result();results.append(v)
            print('R01B1_ROW '+json.dumps({k:v.get(k) for k in ('repo','number','arm','current_D6','current_nodiff','all_channels_clean','issue_boundary_only','errors')}),flush=True)
    results.sort(key=lambda r:(r['repo_id'],r['number']))
    summary={'n':len(results),'label_sha256':HASH,'pin':PIN,'source_blob_sha1':BLOB_SHAS,'retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'all_channels_retrieved':sum(r.get('all_channels_retrieved',False) for r in results),
             'all_channels_clean':sum(r.get('all_channels_clean',False) for r in results),
             'any_D6':sum(r.get('current_D6',False) for r in results),
             'clean_D6':sum(r.get('current_D6',False) and r.get('all_channels_clean',False) for r in results),
             'issue_boundary_only':sum(r.get('issue_boundary_only',False) for r in results),
             'channels':{ch:{'retrieved':sum(ch in r['channels'] for r in results),
                 'joined_positive':sum(r['channels'].get(ch,{}).get('joined_D6',False) for r in results),
                 'atomic_positive':sum(r['channels'].get(ch,{}).get('atomic_D6',False) for r in results)} for ch in CHANNELS},
             'by_arm':{arm:{'n':sum(r['arm']==arm for r in results),'observed_D6':sum(r['arm']==arm and r.get('current_D6',False) for r in results),'clean':sum(r['arm']==arm and r.get('all_channels_clean',False) for r in results)} for arm in ('agentic','human_candidate')},
             'published_diff_only':[{k:r.get(k) for k in ('repo','number','arm','current_D6','current_nodiff','all_channels_clean','errors')} for r in results if not r['published_nodiff']],
             'limits':['Current API replay, not recovery of original August bytes or ordering.','Null patch and inaccessible sources not treated as negative.','PR updated_at not proof of description modification.','No semantic classification or automation exclusivity inferred.']}
    OUT.write_text(json.dumps({'summary':summary,'rows':results},indent=2,ensure_ascii=False)+'\n')
    print('R01B1_SUMMARY '+json.dumps(summary),flush=True)
if __name__=='__main__':main()
