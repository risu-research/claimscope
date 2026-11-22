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
(cd "$ROOT/code" && "$PYTHON" -m unittest -v test_stage5 test_stage6 test_stage8 test_rspack_source_inventory test_rspack_65_comment_pairs test_sensitivity_rspack65)
"$PYTHON" "$ROOT/code/claimscope_stage5.py" --rq3 "$INPUT" --out "$OUT/stage5.json" --bootstrap 3000 --seed 20261010
"$PYTHON" "$ROOT/code/claimscope_stage6.py" --rq3 "$INPUT" --output "$OUT/stage6.json"
"$PYTHON" "$ROOT/code/inclusion_sensitivity.py" "$INPUT" > "$OUT/inclusion_sensitivity.txt"
"$PYTHON" "$ROOT/code/sensitivity_rspack65.py" --labels "$INPUT" --output "$OUT/rspack65_sensitivity.json" --table "$OUT/rspack65_scenario_table.csv" --bootstrap 12000 --seed 20261122
if [[ "${DEEP:-0}" == "1" ]]; then
  "$PYTHON" "$ROOT/code/stage8_audit.py" --csv "$INPUT" --output "$OUT/stage8_audit.json" > "$OUT/stage8_stdout.json"
  "$PYTHON" "$ROOT/code/all_metric_repo_influence.py" --csv "$INPUT" --output "$OUT/all_metric_repo_influence.csv"
fi
"$PYTHON" - "$OUT/observed_replay.json" "$ROOT/results/observed_replay.json" "$ROOT/data/rq3_labels.csv" <<'PY'
import json,sys,hashlib
from pathlib import Path
new,ref,original=(Path(v) for v in sys.argv[1:])
a,b=(json.loads(p.read_text()) for p in (new,ref))
# Path-dependent replay_source.file differs across installations.
for d in (a,b): d['replay_source'].pop('file',None)
assert a==b, 'Core replay differs from the frozen baseline'
raw=original.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
print('PASS: frozen D6 certificate and source SHA-256')
PY
printf 'PASS: ClaimScope public-label replication. DEEP=%s\n' "${DEEP:-0}"
