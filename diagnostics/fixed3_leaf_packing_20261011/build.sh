#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${2:?usage: build.sh PINNED_SOURCE NEW_SCRATCH}
test ! -e "$out" || { echo 'Scratch exists; refusing overwrite' >&2; exit 1; }
python3 "$here/prepare.py" "$1" "$out/code"
mkdir "$out/helpers"
cp "$here/../native_knn_faiss_ivf_20261003/"{run_locked.py,native_ivf.py,verify_outputs.py} "$out/helpers/"
cp "$here/../pivot_reuse_original_gts_20261010/BOUNDARY_CONTRACT.json" "$out/"
cp "$here/../leaf_execution_geometry_20261011/analyze.py" "$out/helpers/geometry_analyze.py"
cp "$here/"{CONTRACT.json,diag32.qid,confirm256.qid,test_leaf.cu,run.py,analyze.py,locked.py,resources.py} "$out/"
nvcc=${CUDA_HOME:-/usr/local/cuda}/bin/nvcc
flags=(-O3 -lineinfo -std=c++17 -arch=sm_120 --extended-lambda -Xptxas=-v)
for mode in G0 G1 G2; do
    "$nvcc" "${flags[@]}" -I"$out/code/$mode/include" "$out/code/bench.cu" -o "$out/$mode.bench" >"$out/$mode.build.log" 2>&1
    "$nvcc" "${flags[@]}" -DLG_COUNTS=1 -I"$out/code/${mode}_count/include" "$out/code/count_bench.cu" -o "$out/${mode}_count.bench" >"$out/${mode}_count.build.log" 2>&1
    "$nvcc" "${flags[@]}" -DFP_MODE="${mode#G}" -I"$out/code/$mode/include" "$out/test_leaf.cu" -o "$out/$mode.unit" >"$out/$mode.unit.build.log" 2>&1
    "${CUDA_HOME:-/usr/local/cuda}/bin/cuobjdump" --dump-resource-usage "$out/$mode.bench" >"$out/$mode.resources.txt"
    "${CUDA_HOME:-/usr/local/cuda}/bin/cuobjdump" --dump-sass "$out/$mode.bench" >"$out/$mode.sass.txt"
done
sha256sum "$out/"*.bench "$out/"*.unit >"$out/BINARY_SHA256.txt"
python3 "$out/resources.py" "$out"
