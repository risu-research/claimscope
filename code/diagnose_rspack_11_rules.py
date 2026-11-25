import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
r=d['rows']
assert len(r)==167 and len({(x['repo_id'],x['number']) for x in r})==167
assert sum(x['published_D6'] for x in r)==153
assert all(x['conditions']['full']['compact']['positive']==x['conditions']['full']['gap']['positive'] for x in r if 'conditions'in x)
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
print('B3_VERIFIED 167 identities and baseline parity',flush=True)
