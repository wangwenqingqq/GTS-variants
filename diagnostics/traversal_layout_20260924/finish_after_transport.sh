#!/usr/bin/env bash
# Continue only after the old orchestrator exits at a completed stage boundary.
set -euo pipefail
root=$1
prior_pid=$2
gpu_index=$3
gpu_uuid=$4
if kill -0 "$prior_pid" 2>/dev/null; then
    echo 'Prior orchestrator still alive; refusing duplicate execution' >&2
    exit 1
fi
export PATH=/usr/local/cuda-13.1/bin:$PATH
python3 - "$root" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from suite import require,plan
expected=[]
for ds in ['GIST','Deep','Tloc']:
    d=root/'data'/ds;require(d,root,'screen')
    radii=json.loads((d/'fixtures/oracle.json').read_text())['radii']
    for row in plan('stress',radii):
        expected.append(json.loads((d/'runs'/row[0]/'receipt.json').read_text()))
observed=[json.loads(line) for line in (root/'logs/stress.txt').read_text().splitlines() if line.startswith('{')]
assert observed==expected and len(expected)==36
for stage in ['screen','sustained','trace']:
    assert not (root/'logs'/f'{stage}.txt').exists(),stage
print('PASS complete stress boundary; no duplicate or partial stage resumed',flush=True)
PY
for stage in screen sustained trace; do
    echo "START $stage $(date -u +%FT%TZ)"
    python3 "$root/suite.py" "$root" "$stage" --gpu "$gpu_uuid" --gpu-index "$gpu_index" >"$root/logs/$stage.txt" 2>&1
    echo "DONE $stage $(date -u +%FT%TZ)"
done
