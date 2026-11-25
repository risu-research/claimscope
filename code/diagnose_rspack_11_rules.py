import json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
r=d['rows'];assert len(r)==40 and len({(x['repo_id'],x['number']) for x in r})==40
assert all(hashlib.sha256(c['body'].encode()).hexdigest()==c['sha256'] for x in r for c in x.get('comments',[]) if c['body'] is not None)
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':len(r),'comments':sum(len(x.get('comments',[])) for x in r),'verified':True},indent=2)+'\n')
print('R02B2I_VERIFIED collection identities and hashes',flush=True)
