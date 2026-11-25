import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
r=d['rows']
assert len(r)==70 and len({(v['repo_id'],v['number']) for v in r})==70
assert d['summary']['any_D6']==sum(v.get('current_D6',False) for v in r)
assert d['summary']['all_channels_clean']==sum(v.get('all_channels_clean',False) for v in r)
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
print('R01B1_VERIFIED 70 row identities and aggregates',flush=True)
