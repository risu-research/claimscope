#!/usr/bin/env python3
"""R02-B2c collection only: frozen ranks 21–30 in each random stratum.
Keep all comments, no keyword filtering, no semantic/extractor decisions here.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,get,pages,repo_of,positive,sha
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
CUT='2026-08-27T22:00:00Z'
IDS=[(32944298,7863),(32944298,9194),(197336679,634),(6860771,3542),(172404626,47),(7243421,1977),(121814210,7374),(237392204,9655),(136202695,22668),(116150224,1069),(101194285,9208),(305438235,199),(139199684,20972),(101194285,10232),(210716005,127779),(305438235,537),(210716005,122389),(101194285,9943),(305438235,286),(210716005,120633),(4127088,46572),(238797860,16276),(708452754,919),(650377372,6883),(537233603,21408),(575321313,2013),(100061716,33753),(701547123,21019),(10458362,6886),(238797860,16420),(599431918,13419),(128479644,13902),(599431918,16835),(599431918,20249),(23496542,6892),(101194285,8661),(23496542,8444),(599431918,21811),(599431918,11698),(599431918,22610)]
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
    print('R02B2C_COLLECTION '+json.dumps([{'repo':z['repo'],'number':z['number'],'n':len(z.get('comments',[])),'errors':z['errors']} for z in out]),flush=True)
if __name__=='__main__':main()
