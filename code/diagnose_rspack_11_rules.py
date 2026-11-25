import json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
r=d['rows'];assert len(r)==16 and len({(x['repo_id'],x['number']) for x in r})==16
assert all(x['expected_comments']==len(x['comments']) and x['same_issue_hash'] for x in r)
assert all(hashlib.sha256(c['body'].encode()).hexdigest()==c['sha256'] for x in r for c in x['comments'])
assert all(not x['published_D6'] for x in r)
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':len(r),'comments':sum(len(x['comments']) for x in r),'verified':True},indent=2)+'\n')
print('R02B1_VERIFIED 16 identities and raw comment hashes',flush=True)
