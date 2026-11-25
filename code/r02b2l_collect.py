#!/usr/bin/env python3
"""R02-B2l collection only: frozen ranks 111–120 in each random stratum.
Keep all comments, no keyword filtering, no semantic/extractor decisions here.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,get,pages,repo_of,positive,sha
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
CUT='2026-08-27T22:00:00Z'
IDS=[(121814210,7372),(263364731,883),(26785339,5636),(722184017,2113),(792160692,82),(381857226,10446),(164374484,798),(19330736,7173),(30932325,7279),(267563398,940),(210716005,128630),(210716005,123041),(210716005,125722),(139199684,20450),(599431918,14397),(305438235,657),(210716005,122956),(210716005,120916),(599431918,22598),(210716005,121851),(413794983,2221),(701547123,22982),(701547123,24956),(274495425,5228),(126897385,3117),(255027515,978),(481206475,1005),(5108051,28374),(166515022,28512),(537233603,23543),(128479644,13700),(210716005,116419),(128479644,14598),(128479644,13401),(23496542,10414),(128479644,13825),(101194285,10520),(128479644,12628),(128479644,15690),(23496542,9021)]
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
    print('R02B2L_COLLECTION '+json.dumps([{'repo':z['repo'],'number':z['number'],'n':len(z.get('comments',[])),'errors':z['errors']} for z in out]),flush=True)
if __name__=='__main__':main()
