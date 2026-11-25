#!/usr/bin/env python3
"""R02-B2k collection only: frozen ranks 101–110 in each random stratum.
Keep all comments, no keyword filtering, no semantic/extractor decisions here.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,get,pages,repo_of,positive,sha
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
CUT='2026-08-27T22:00:00Z'
IDS=[(29078997,80734),(29078997,82948),(622646426,686),(237392204,9384),(645180041,974),(136202695,22670),(213728552,522),(164374484,800),(581186630,89),(3292397,671),(210716005,124172),(305438235,346),(599431918,12694),(305438235,460),(139199684,20454),(210716005,128505),(210716005,124450),(210716005,122947),(923332984,1092),(599431918,14802),(537233603,21645),(808266543,6245),(23247808,2634),(537233603,23181),(537233603,22724),(65711522,73054),(151331938,13982),(413918947,11915),(32051890,12065),(166515022,26168),(599431918,20509),(599431918,22438),(599431918,20318),(128479644,10977),(101194285,11673),(210716005,121223),(128479644,15512),(101194285,9627),(128479644,11445),(128479644,13794)]
def eligible(c):
    if not c.get('created_at') or not c.get('updated_at'):return 'undated'
    if c['created_at']>CUT:return 'late_created'
    if c['updated_at']>CUT:return 'late_edited'
    return 'eligible'
def work(r):
    rid,n=int(r['repo_id']),int(r['number']);repo=repo_of(r)
    z={'repo_id':rid,'number':n,'repo':repo,'errors':[]}
    try:
        try:p,_=get('/repos/'+repo+'/pulls/'+str(n))
        except Exception:p,_=get('/repositories/'+str(rid)+'/pulls/'+str(n))
        assert p['number']==n and p['base']['repo']['id']==rid
        canonical=p['base']['repo']['full_name']
        z.update(canonical_repo=canonical,head=p['head']['sha'],base=p['base']['sha'],expected=p['comments'],pr_created=p.get('created_at'),pr_updated=p.get('updated_at'),pr_author=p['user']['login'])
        a=pages('/repos/'+canonical+'/issues/'+str(n)+'/comments')
        z['comments']=[{'id':c['id'],'url':c['html_url'],'actor':(c.get('user') or {}).get('login'),'author_id':(c.get('user') or {}).get('id'),'type':(c.get('user') or {}).get('type'),'created':c.get('created_at'),'updated':c.get('updated_at'),'eligibility':eligible(c),'body':c.get('body'),'sha256':sha(c['body']) if c.get('body') is not None else None} for c in a]
        if len(a)!=p['comments']:z['errors'].append('count mismatch')
        if len({c['id'] for c in a})!=len(a):z['errors'].append('duplicate IDs')
        if any(c['body'] is None for c in z['comments']):z['errors'].append('null body')
    except Exception as e:z['errors'].append(str(e))
    return z
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    lookup={(int(r['repo_id']),int(r['number'])):r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines())}
    rows=[lookup[k] for k in IDS]
    assert len(set(IDS))==40 and all(positive(r['in_metric_layer']) and not positive(r['D6']) for r in rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:out=list(pool.map(work,rows))
    data={'pin':PIN,'label_sha256':HASH,'frozen_sample_sha256':'530fb02b8eca1a8ca5c2152080eb7e8b0b823d60d59cdbd1b4bcc34304c7abe6','cutoff':CUT,'retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':out}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('R02B2K_COLLECTION '+json.dumps([{'repo':z['repo'],'number':z['number'],'n':len(z.get('comments',[])),'errors':z['errors']} for z in out]),flush=True)
if __name__=='__main__':main()
