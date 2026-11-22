#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INPUT="${INPUT:-$ROOT/data/rq3_labels.csv}"
OUT="${OUT:-$ROOT/build}"
mkdir -p "$OUT"
PYTHON="${PYTHON:-python3}"
if [[ ! -f "$INPUT" ]]; then
  "$PYTHON" "$ROOT/code/replay_public.py" --download --cache "$INPUT" --output "$OUT/observed_replay.json"
fi
"$PYTHON" "$ROOT/code/replay_public.py" --csv "$INPUT" --output "$OUT/observed_replay.json"
(cd "$ROOT/code" && "$PYTHON" -m unittest -v test_stage5 test_stage6 test_stage8 test_rspack_source_inventory test_rspack_65_comment_pairs test_sensitivity_rspack65 test_rspack65_other_sources test_sensitivity_rspack65_observed_channels test_semantic_rspack65_size test_rspack97_semantic)
"$PYTHON" "$ROOT/code/claimscope_stage5.py" --rq3 "$INPUT" --out "$OUT/stage5.json" --bootstrap 3000 --seed 20261010
"$PYTHON" "$ROOT/code/claimscope_stage6.py" --rq3 "$INPUT" --output "$OUT/stage6.json"
"$PYTHON" "$ROOT/code/inclusion_sensitivity.py" "$INPUT" > "$OUT/inclusion_sensitivity.txt"
"$PYTHON" "$ROOT/code/sensitivity_rspack65_observed_channels.py" --source-audit "$ROOT/results/rspack65_other_source_replay.json" --output "$OUT/rspack65_observed_sensitivity.json"
"$PYTHON" "$ROOT/code/sensitivity_rspack65.py" --labels "$INPUT" --output "$OUT/rspack65_sensitivity.json" --table "$OUT/rspack65_scenario_table.csv" --bootstrap 12000 --seed 20261122
"$PYTHON" "$ROOT/code/rspack97_semantic_audit.py" --offline
if [[ "${DEEP:-0}" == "1" ]]; then
  "$PYTHON" "$ROOT/code/stage8_audit.py" --csv "$INPUT" --output "$OUT/stage8_audit.json" > "$OUT/stage8_stdout.json"
  "$PYTHON" "$ROOT/code/all_metric_repo_influence.py" --csv "$INPUT" --output "$OUT/all_metric_repo_influence.csv"
fi
"$PYTHON" - "$OUT/observed_replay.json" "$ROOT/results/observed_replay.json" "$ROOT/data/rq3_labels.csv" <<'PY'
import json,sys,hashlib,math
from pathlib import Path
new,ref,original=(Path(v) for v in sys.argv[1:])
a,b=(json.loads(p.read_text()) for p in (new,ref))
# Path-dependent replay_source.file differs across installations.
for d in (a,b): d['replay_source'].pop('file',None)
if a != b:
    differences=[]
    def compare(x,y,p="root"):
        if type(x)!=type(y):
            differences.append((p,"type",type(x).__name__,type(y).__name__))
        elif isinstance(x,dict):
            for k in sorted(set(x)|set(y)):
                if k not in x or k not in y: differences.append((f"{p}.{k}","missing",str(k in x),str(k in y)))
                else: compare(x[k],y[k],f"{p}.{k}")
        elif isinstance(x,list):
            if len(x)!=len(y): differences.append((p,"length",len(x),len(y)))
            for i,(u,v) in enumerate(zip(x,y)): compare(u,v,f"{p}[{i}]")
        elif x!=y and not (isinstance(x,float) and isinstance(y,float) and math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12)):
            differences.append((p,"value",x,y))
    compare(a,b)
    if differences:
        print("FROZEN_CERTIFICATE_DIFF",json.dumps(differences[:30],ensure_ascii=False,default=str))
        raise AssertionError(f"Core replay differs from frozen baseline in {len(differences)} fields")
    print("PASS: frozen certificate matches at 1e-12 floating-point precision")
raw=original.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
print('PASS: frozen D6 certificate and source SHA-256')
PY
printf 'PASS: ClaimScope public-label replication. DEEP=%s\n' "${DEEP:-0}"
