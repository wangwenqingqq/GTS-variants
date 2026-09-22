# Validation receipt, 2026-09-22

## Completed

- Live archive identity: main and all 14 include-header SHA-256 values matched
  the pinned source. Original `src/` and `include/` files are unchanged.
- `test_prepare.py`: PASS for source pinning, unused tuner arguments, float
  alias, exact instrumentation anchors, all four kNN overloads, output hashes,
  and refusal to replace existing output.
- Fresh uninstrumented and instrumented builds: PASS with CUDA 13.1.115,
  GCC 13.3.0, C++17, O2, sm_120, RDC, line information, frame pointers and
  nvlink `--ignore-host-info`. Both use the same code-generation contract.
- Instrumented build includes installed NVTX headers and `-ldl`.
- Host-only timer test: PASS for nested call counts and CPU/wall accounting.
  Its executable does not link libcudart; no GPU context/workload was created.

| Binary | SHA-256 |
|---|---|
| Fresh baseline | `302e1210b5f4bef43d515805f4eac7aa28bf3e64e6cfcdf7a1fbc2eadc19ffff` |
| Diagnostic + NVTX | `91e905914bc9c45f9f46bd1f52c573ac4245bfcc5c4948953e05ec4571f13e4e` |

The first compile invoked nvcc via a relocated executable path and failed to
locate `cuda_runtime.h`. Reinvoking the toolkit's actual `bin/nvcc` path resolved
the include discovery issue. The failed build log is retained, not counted as a
pass. Existing format/type warnings remain in both successful archive builds;
no claim of a warning-free source is made.

## Not completed / not claimed

- No workload-specific CPU utilization profile, dynamic transfer census, UVM
  trace, GPU correctness run, sanitizer run, stress run, runtime parity check,
  or end-to-end performance comparison.
- All eight devices had foreign compute workloads at admission checks; GPU 0
  remained occupied. No other device was substituted and no process signaled.
- Nsight Systems 2025.5.2 reports CPU sampling unavailable for the current
  account (`perf_event_open` fails; paranoid level 4). No host permissions or
  GPU settings were changed.
- Instrumentation and optional wait-policy control have compile-only GPU
  validation. Their timing is diagnostic, not a promoted optimization result.
- No manuscript edit, submission, repository visibility change or upload.

The inspected machine has RTX PRO 6000 Blackwell Server Edition GPUs, driver
590.48.01, and two Xeon Gold 6530 sockets / 128 logical CPUs. Exact machine,
process, path and device-UUID records are retained in ignored local evidence,
not in portable/public documentation.

## Evidence files retained locally

Under `diagnostics/cpu_io/local/` (intentionally ignored by Git):

- `preflight_and_identity.log`: timestamped GPU occupancy, installed tools,
  profiler capability and remote source/binary hashes;
- `build_baseline_path_failure.log`, `build_baseline.log`,
  `build_profiled.log`: complete build results;
- `test_prepare.log`, `test_profile.log`: CPU-only checks;
- `EXECUTION_CARD.md`: exact local/remote scratch paths and pending run boundary.

The generated source and its `INSTRUMENTED_SHA256.json` are retained under
`diagnostics/cpu_io/work/profiled/`. Large/raw machine artifacts are not part of
the prospective publish set. The publish gate remains unresolved because live
repository visibility differs from its inherited private-archive policy.
