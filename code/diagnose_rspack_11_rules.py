import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
assert len(d['rows'])==4
assert all(r['conditions']['original']['D6']==0 and r['conditions']['report_alone']['D6']>0 and r['conditions']['repair_only']['D6']>0 for r in d['rows'])
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':4,'verified':True},indent=2)+'\n')
print('NORMALIZER_VERIFIED four controlled recoveries',flush=True)
