#!/usr/bin/env python3
"""R02-B2i secondary exact replay, after semantic ledger was fixed.
Issue comment comparison must be checked against first retrieval.
No expanded semantic endpoint is inferred from these six-channel flags.
"""
import csv,hashlib,json,datetime,concurrent.futures
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,positive,one,extract
from r02b2i_collect import IDS
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
LEDGER_SHA='6d64c4c780fc35c4f5286f5849d3d00b1ddd30f334b6e103b3b78054cd7de8c4'
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    lookup={(int(r['repo_id']),int(r['number'])):r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines())}
    rows=[lookup[k] for k in IDS]
    assert len(rows)==40 and all(not positive(r['D6']) and positive(r['in_metric_layer']) for r in rows)
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
    data={'pin':PIN,'source_blob_sha1':BLOB_SHAS,'source_b64':blobs,'label_sha256':HASH,'semantic_ledger_sha256':LEDGER_SHA,'pr_ledger_sha256':'12c3d7dc133f108ce2470d2908eb0f2e2b1768cddab590165d4320b02fd05e00','collection_zip_sha256':'f2bd6e8b2295dc12bb08d0877aebc3b2908d84727495399489e9c262eaad9336','retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':out}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('R02B2I_REPLAY '+json.dumps([{'repo':r['repo'],'number':r['number'],'D6':r.get('current_D6'),'clean':r.get('all_channels_clean'),'errors':r.get('errors')} for r in out]),flush=True)
if __name__=='__main__':main()
