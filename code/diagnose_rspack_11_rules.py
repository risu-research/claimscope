import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
assert len(d['rows'])==20 and len({(x['repo_id'],x['number']) for x in d['rows']})==20
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':20,'collection_only':True},indent=2)+'\n')
