#!/usr/bin/env bash
# Generate pinned scratch copies; compile only, no GPU query or admission.
set -euo pipefail
ROOT=$(cd "${1:?usage: build_cuda.sh TASK_SCRATCH ORIGINAL_GTS}" && pwd)
ORIGINAL=$(cd "${2:?provide the eight pinned original GTS source files}" && pwd)
CODE=$(cd "$(dirname "$0")" && pwd)
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.1}
export PATH="$CUDA_HOME/bin:$PATH"
test ! -e "$ROOT/build_v3"
mkdir -p "$ROOT/logs" "$ROOT/bin"
python3 "$CODE/prepare_cuda.py" "$ORIGINAL" "$ROOT/build_v3"
FLAGS=(-std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -Xptxas=-v)
nvcc "${FLAGS[@]}" -DINSTRUMENT=0 "$ROOT/build_v3/bench.cu" -o "$ROOT/bin/bench_v3" > "$ROOT/logs/bench_v3.build.log" 2>&1
nvcc "${FLAGS[@]}" -DINSTRUMENT=1 "$ROOT/build_v3/bench_count.cu" -o "$ROOT/bin/bench_count_v4" > "$ROOT/logs/bench_count_v4.build.log" 2>&1
printf '%s\n' 'A/R/native S built; correctness, sanitizers and timing still require locked admission.'
