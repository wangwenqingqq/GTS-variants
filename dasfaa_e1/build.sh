#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p bin evidence/build
python3 prepare_native.py
for pair in 'D 0' 'G 1' 'P 2'; do
  read -r arm backend <<< "$pair"
  "${CUDA_HOME:-/usr/local/cuda}/bin/nvcc" -std=c++17 -O3 -lineinfo -arch=sm_120 -DBACKEND="$backend" dynamic.cu -o "bin/$arm" \
    >"evidence/build/$arm.stdout" 2>"evidence/build/$arm.stderr"
done
sha256sum bin/{D,G,P} > evidence/build/binaries.sha256

python3 - <<'PYHASH'
import hashlib, json
from pathlib import Path
root=Path('.')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'selected_query_api':'searchIndexKnnV2 + tombstone overfetch + exact delta top-k + GPU-distance host merge',
          'native_static_knn_selected':True,
          'runtime_validated':False,
          'timing_eligible':False,
          'binary_sha256':{str(p):sha(p) for p in sorted((root/'bin').iterdir()) if p.is_file()},
          'input_source_sha256':{str(p):sha(p) for arm in ('g','p') for p in sorted((root/f'source_{arm}'/'include').iterdir()) if p.is_file()},
          'derived_source_sha256':{str(p):sha(p) for arm in ('g','p') for p in sorted((root/f'native_{arm}').iterdir()) if p.is_file()},
          'adapter_sha256':{str(root/p):sha(root/p) for p in ('dynamic.cu','case.hpp','prepare_native.py','build.sh')},
          'static_knn_patch_provenance':json.loads((root/'evidence/static_knn_patch_provenance.json').read_text())}
(root/'evidence/build/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PYHASH
