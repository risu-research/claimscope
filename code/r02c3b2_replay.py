#!/usr/bin/env python3
"""R02-C3b2 secondary exact replay, after semantic ledger was fixed.
Issue comment comparison must be checked against first retrieval.
No expanded semantic endpoint is inferred from these six-channel flags.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,positive,one,extract
from r02c3b2_collect import IDS
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
LEDGER_SHA='cf31d006d938e6c1eb441cd21450721a102e121e4b26bd14020d2ce95defb141'
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    lookup={(int(r['repo_id']),int(r['number'])):r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines())}
    rows=[lookup[k] for k in IDS]
    assert len(rows)==10 and all(positive(r['D6']) and positive(r['in_metric_layer']) for r in rows)
    def work(r):
        z=one(r)
        z['published_D6']=positive(r['D6'])
        return z
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:out=list(pool.map(work,rows))
    sources={n:(ROOT/'code/upstream_pinned'/n).read_text(encoding='utf8') for n in BLOB_SHAS}
    # Source bytes are exported independently of replay, for offline exact testing.
    # Encode as base64 so original git blob bytes are maintained.
    import base64
    blobs={n:base64.b64encode((ROOT/'code/upstream_pinned'/n).read_bytes()).decode() for n in BLOB_SHAS}
    data={'pin':PIN,'source_blob_sha1':BLOB_SHAS,'source_b64':blobs,'label_sha256':HASH,'semantic_ledger_sha256':LEDGER_SHA,'pr_ledger_sha256':'d29e445f968784e6350d6c81808b2b230069854b9bb9e748f2f45ecc0a642e68','collection_zip_sha256':'6b6290df3df1e97930a19465dba74ec910cfd2aee1eb55850094e5607279e2df','retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':out}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('R02C3B2_REPLAY '+json.dumps([{'repo':r['repo'],'number':r['number'],'D6':r.get('current_D6'),'clean':r.get('all_channels_clean'),'errors':r.get('errors')} for r in out]),flush=True)
if __name__=='__main__':main()
