import json,hashlib,base64
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
assert len(d['rows'])==40 and len({(x['repo_id'],x['number']) for x in d['rows']})==40
assert all(not x['published_D6'] for x in d['rows'])
for n,s in d['source_b64'].items():
    b=base64.b64decode(s);assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==d['source_blob_sha1'][n]
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':40,'source_blobs_verified':True},indent=2)+'\n')
print('R02B2E_REPLAY_VERIFIED identities and pinned extractor source blobs',flush=True)
