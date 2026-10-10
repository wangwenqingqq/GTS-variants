#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${2:?usage: build.sh PINNED_SOURCE NEW_SCRATCH}
test ! -e "$out" || { echo "Scratch exists; refusing overwrite" >&2; exit 1; }
python3 "$here/prepare.py" "$1" "$out/code"
mkdir "$out/helpers"
cp "$here/../native_knn_faiss_ivf_20261003/"{run_locked.py,native_ivf.py,verify_outputs.py} "$out/helpers/"
cp "$here/../pivot_reuse_original_gts_20261010/"{locked.py,BOUNDARY_CONTRACT.json} "$out/"
cp "$here/"{run.py,analyze.py,CONTRACT.json,diag32.qid} "$out/"
for mode in G0 Gcount; do
    flag=0; [[ $mode == Gcount ]] && flag=1
    "${CUDA_HOME:-/usr/local/cuda}/bin/nvcc" -O3 -lineinfo -std=c++17 -arch=sm_120 --extended-lambda \
       -DLG_COUNTS="$flag" -I"$out/code/count/include" "$out/code/bench.cu" -o "$out/$mode.bench" >"$out/$mode.build.log" 2>&1
done
