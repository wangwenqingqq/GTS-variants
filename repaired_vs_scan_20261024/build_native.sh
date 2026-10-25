#!/usr/bin/env bash
# User-local build only. Run in a fresh task scratch; never install system-wide.
set -euo pipefail
ROOT=$(cd "${1:?usage: build_native.sh TASK_SCRATCH}" && pwd)
CODE=$(cd "$(dirname "$0")" && pwd)
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.1}
export PATH="$CUDA_HOME/bin:$PATH"
PREFIX="$ROOT/deps"
test ! -e "$PREFIX"
mkdir -p "$PREFIX" "$ROOT/logs" "$ROOT/bin"
git clone https://github.com/kokkos/kokkos.git "$PREFIX/kokkos"
git -C "$PREFIX/kokkos" checkout --detach 82799e4577568f9666bde36265ac15d78da3e6c8
git clone https://github.com/arborx/ArborX.git "$PREFIX/ArborX"
git -C "$PREFIX/ArborX" checkout --detach 3a20eaba22bd8b6c13d6b32064a2086a3ce1c993
cmake -S "$PREFIX/kokkos" -B "$PREFIX/kokkos-build" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX/install" \
  -DCMAKE_CXX_COMPILER="$PREFIX/kokkos/bin/nvcc_wrapper" \
  -DCMAKE_CXX_STANDARD=20 -DCMAKE_BUILD_TYPE=Release \
  -DKokkos_ENABLE_CUDA=ON -DKokkos_ENABLE_SERIAL=ON \
  -DKokkos_ENABLE_CUDA_LAMBDA=ON -DKokkos_ARCH_BLACKWELL120=ON \
  > "$ROOT/logs/kokkos.configure.log" 2>&1
cmake --build "$PREFIX/kokkos-build" -j4 > "$ROOT/logs/kokkos.build.log" 2>&1
cmake --install "$PREFIX/kokkos-build" > "$ROOT/logs/kokkos.install.log" 2>&1
mkdir "$PREFIX/benchmark"
cp "$CODE/ArborX_CMakeLists.txt" "$PREFIX/benchmark/CMakeLists.txt"
cp "$CODE/arborx_bench.cpp" "$CODE/bench_io.hpp" "$PREFIX/benchmark/"
python3 "$CODE/prepare_arborx_counter.py" "$PREFIX/benchmark/arborx_bench.cpp" "$PREFIX/benchmark/arborx_count_fast.cpp"
cmake -S "$PREFIX/benchmark" -B "$PREFIX/benchmark-build" \
  -DARBORX_SOURCE="$PREFIX/ArborX" -DCOUNTER_SOURCE="$PREFIX/benchmark/arborx_count_fast.cpp" -DCMAKE_PREFIX_PATH="$PREFIX/install" \
  -DCMAKE_CXX_COMPILER="$PREFIX/kokkos/bin/nvcc_wrapper" \
  -DCMAKE_CXX_STANDARD=20 -DCMAKE_BUILD_TYPE=Release \
  > "$ROOT/logs/arborx.configure.log" 2>&1
cmake --build "$PREFIX/benchmark-build" -j2 > "$ROOT/logs/arborx.build.log" 2>&1
cp "$PREFIX/benchmark-build/arborx_bench" "$ROOT/bin/arborx_bench"
cp "$PREFIX/benchmark-build/arborx_count" "$ROOT/bin/arborx_count_fast"
printf '%s\n' 'Native Kokkos CUDA sm_120 + ArborX built; GPU correctness/timing still required.'
