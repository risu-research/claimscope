#!/usr/bin/env python3
"""R02-C3a2 secondary exact replay, after semantic ledger was fixed.
Issue comment comparison must be checked against first retrieval.
No expanded semantic endpoint is inferred from these six-channel flags.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,positive,one,extract
from r02c3a2_collect import IDS
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
LEDGER_SHA='ac61d3bd2e71f4f94f5090b58a6b8797d852f1e5c48947aae6837e514897613c'
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
    data={'pin':PIN,'source_blob_sha1':BLOB_SHAS,'source_b64':blobs,'label_sha256':HASH,'semantic_ledger_sha256':LEDGER_SHA,'pr_ledger_sha256':'134172c60f724a5ed73b6ee081b224302a534f380905d187f5ea9a3c5eb2ce24','collection_zip_sha256':'539e49177be14d5e3615ac57d7e67da3ef52b34a6c255c98a6deb156ae81e5c5','retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':out}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('R02C3A2_REPLAY '+json.dumps([{'repo':r['repo'],'number':r['number'],'D6':r.get('current_D6'),'clean':r.get('all_channels_clean'),'errors':r.get('errors')} for r in out]),flush=True)
if __name__=='__main__':main()
