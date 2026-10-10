#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
base="$here/../native_knn_faiss_ivf_20261003"
source=${1:?usage: build.sh PINNED_GTS_SOURCE NEW_SCRATCH}
out=${2:?usage: build.sh PINNED_GTS_SOURCE NEW_SCRATCH}
test ! -e "$out" || { echo 'Scratch already exists; refusing overwrite' >&2; exit 1; }
python3 "$here/prepare.py" "$source" "$out/v2"
mkdir "$out/helpers"
cp "$base"/{run_locked.py,native_ivf.py,verify_outputs.py} "$out/helpers/"
cp "$here"/{run.py,locked.py,analyze.py,CONTRACT.json} "$out/"
cp "$here/test_cache.cu" "$out/v2/"
nvcc="${CUDA_HOME:-/usr/local/cuda}/bin/nvcc"
for mode in G0 G1 G0_count G1_count; do
    enabled=0; counts=0
    [[ $mode == G1* ]] && enabled=1
    [[ $mode == *_count ]] && counts=1
    "$nvcc" -O3 -lineinfo -std=c++17 -arch=sm_120 --extended-lambda \
        -DPR_ENABLED="$enabled" -DPR_COUNTS="$counts" -I"$out/v2/$mode/include" \
        "$out/v2/bench.cu" -o "$out/v2/$mode.bench" >"$out/v2/$mode.build.log" 2>&1
done
"$nvcc" -O3 -lineinfo -std=c++17 -arch=sm_120 --extended-lambda \
    -I"$out/v2/G1/include" "$out/v2/test_cache.cu" -o "$out/v2/test_cache" >"$out/v2/test_cache.build.log" 2>&1
echo 'Compiled only. No GPU correctness or performance run implied.'
