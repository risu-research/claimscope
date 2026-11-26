import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
assert len(d['rows'])==14 and len({(x['repo_id'],x['number']) for x in d['rows']})==14
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':14,'collection_only':True,'protocol_sha256':'923523e534b484b877da578c9759682da603e49ddddf9dd085ec22fd7be3ac96'},indent=2)+'\n')
