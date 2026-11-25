import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results'
d=json.loads((p/'rspack_11_exact_extractor.json').read_text())
assert len(d['rows'])==12 and len({(x['repo_id'],x['number']) for x in d['rows']})==12
assert all(len(x['joined']['hits'])>0 for x in d['rows'] if 'joined' in x)
v=d['valkey']['conditions']
assert v['full']['hits'] and v['pair']['hits'] and not v['A']['hits'] and not v['B']['hits'] and not v['padded_pair']['hits']
(p/'rspack_11_rule_diagnostics.json').write_text(json.dumps({'n':len(d['rows']),'valkey':{k:len(x['hits']) for k,x in v.items()}},indent=2)+'\n')
print('B2_VERIFIED identities, exact positive witnesses, pair sufficiency',flush=True)
