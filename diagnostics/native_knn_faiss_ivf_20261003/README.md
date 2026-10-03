# Original GTS versus native GPU Faiss-IVF kNN

This diagnostic closes the kNN gap in the preceding range-oriented P6 evidence.
Use [RESULTS.md](RESULTS.md) for conclusions and [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md)
for admissible wording. It does not change the historical incremental tree or
claim an improvement to the current GTS++ production implementation.

## Contract and important exceptions

- RTX PRO 6000 Blackwell Server Edition, one idle device on an eight-GPU host.
  The measured device was index7/NUMA3. Clocks and power settings were not changed.
  Another idle device is allowed, but recheck topology, active processes and locks.
- GIST 1M×960D and Deep 1M×96D, FP32 resident tables; K8/32, B1/32.
- Static **self-inclusive in-dataset** queries. Deliver K original IDs and FP32
  Euclidean distance fields to Host. This is not an out-of-dataset workload.
- GTS receives query IDs and accesses its resident vectors; IVF gathers Host
  vectors and passes them to its native API. Their native input interfaces and
  C++ versus Python callers differ. Both paths charge their actual preparation,
  transfers, allocation/free, search/sort, result delivery and synchronization.
- Independent full-table explicit-RN FP64 oracle, CPU bitwise spot checks and
  boundary ties; actual returned-ID distance fields are checked independently.
  Original GTS arithmetic and native FP32 IVF arithmetic are **not identical**.
  Matching means satisfying the same empirical quality gate, not matching math modes.
- Development128 selects the fastest two-pass mean for each registered quality
  anchor. Final256 is generated only after the configuration freeze; prior query
  IDs and development IDs are excluded. No tuning on final queries.
- Six fresh-process rounds alternate GTS/IVF order. The primary denominator is
  total Host-ready time per **256-query pass**, not a single-query response time.
  File reading, index construction/cache loading, oracle and checks are excluded
  and recorded separately. B32 is the sustained full-pass scope.
- A fixed all-list1024/1024 IVF control was declared **after** observing the
  first-round final quality miss. It is a later six-process **non-paired supplement**,
  not a rescue of the frozen anchors or a direction-balanced production promotion.

`CONTRACT.json` retains the registered semantics. Public hardware/path fields
are redacted; exact collection-to-delivery hashes are in the evidence manifest.
`EXHAUSTIVE_CONTROL.json` is a separate declaration, not a rewritten contract.

## Reproduce from a clean scratch directory

Requirements: Linux, CUDA13.1, a legal idle SM120 GPU, `numactl`, NumPy/CuPy14.1,
and a source-built Faiss1.15.1 native GPU module (`FAISS_ENABLE_GPU=ON`,
`FAISS_ENABLE_CUVS=OFF`, `CMAKE_CUDA_ARCHITECTURES=120`, Release).
See the software/hash manifest in `evidence/` for the collected versions.
No CPU fallback is permitted. Set portable paths explicitly:

```sh
export DATA_ROOT=/path/to/data            # dataset/1000000/fixtures/data.f32bin
export FAISS_PYTHON=/path/to/venv/bin/python
export GPU_UUID='<verified-idle-device-uuid>'
export CUDA_HOME=/usr/local/cuda
```

Real input is not redistributed. The binary format is little-endian int32
`(D,N,2)` followed by row-major FP32 coordinates. Exact converted-data sizes,
SHA256 and finite-value checks are in `evidence/PREFLIGHT.json`. Do not silently
replace them with another similarly named dataset. Index caches and result
binaries remain outside Git with hashes; rebuild caches in scratch when absent.

Copy this directory's scripts/contracts/query fixtures to fresh scratch and run:

```sh
git clone https://github.com/ZJU-DAILY/GTS original-gts
git -C original-gts checkout 3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639
python3 prepare_gts.py original-gts/SourceCode/GTS gts
$CUDA_HOME/bin/nvcc -O3 -std=c++17 -arch=sm_120 --extended-lambda \
  -Igts/adapted/include gts_bench.cu -o gts_bench
$FAISS_PYTHON make_synthetic.py
python3 campaign.py qualify --python "$FAISS_PYTHON" \
  --data-root "$DATA_ROOT" --gpu "$GPU_UUID" >qualify_console.log 2>&1
```

`make_synthetic.py` creates missing files, reuses exact matching fixtures and
rejects nonmatching existing files without overwriting. Its exact fixture hashes
are recorded in the manifest. The pinned upstream
already uses FP32 (`#define short float`); the adapter adds capacity, a fixed
1GiB workspace and full IDs, not a search/pruning/distance optimization.

To replay the delivered frozen comparison, copy `FROZEN_CONFIG.json`
after successful local qualification, and run the frozen
final queries. Keep the qualification just produced locally, rather than
substituting archived receipts for local checks. Scratch oracle/cache outputs
are regenerated as needed:

```sh
python3 campaign.py formal --python "$FAISS_PYTHON" \
  --data-root "$DATA_ROOT" --gpu "$GPU_UUID" >formal_console.log 2>&1
python3 run_control.py --python "$FAISS_PYTHON" \
  --data-root "$DATA_ROOT" --gpu "$GPU_UUID" >control_console.log 2>&1
$FAISS_PYTHON verify_outputs.py postcheck
python3 analyze.py .
python3 profile_queries.py --python "$FAISS_PYTHON" \
  --data-root "$DATA_ROOT" --gpu "$GPU_UUID" >profile_console.log 2>&1
python3 analyze_profiles.py .
```

For a **new** development campaign, run `campaign.py development`, then create
fresh final queries with `freeze_queries.py` from the repository diagnostic
layout. Do not overwrite this delivery's FROZEN_CONFIG/query metadata. A replay
uses the delivered fixed queries; rerunning development is not needed to replay.
The portable runner defaults to NUMA3; if using another topology, change the
explicit runner NUMA argument before collecting a new campaign and record it.

## Distinct validation/provenance gates

- Qualification covers N4097, D96/960, K8/32, B1/32, ragged33 queries, nine duplicate
  vectors at the boundary, eight GTS passes and two IVF passes.
- Recorded memcheck/synccheck cover **reused-cache GTS queries only**, not initial
  construction, Faiss, oracle or CUDA Graphs. These are not universal safety proofs.
- The original collection quality checker did not explicitly gate negative or
  nondecreasing distance fields and reported scale1-relative, not pure relative,
  errors. `verify_outputs.py` adds those checks separately: all retained GTS
  outputs are checked offline; native outputs use separately labeled validation
  replays/control runs. Never represent these as part of the old timing checker.
- The offline cache audit verifies the complete ID permutation and exact
  contiguous, disjoint leaf intervals. A summed size check alone is insufficient.
- The public runner removes private alias paths, exposes NUMA/legacy lock roots,
  deduplicates newly created locks by descriptor identity and reaps owned process
  groups on exceptions. It differs from the collected runner; both identities
  remain in provenance. No collected timing source or raw receipt is overwritten.
  The separately rebuilt adapter is compiled and smoke-checked on the intended
  GPU; its container hash differs from the measured binary. No smoke timing is
  substituted for the measured six-round binary. Exact flags/hashes are recorded.
- NSYS captures only `formal.query_pass`, first32 final GIST queries, K8/B1 and
  K8/B32. Profiler durations are **diagnostic**, not public timing. Inclusive CUDA
  API durations overlap GPU work and do not measure CPU arithmetic. No NCU
  coalescing counters or causal optimization ablation are supplied here.
  Raw-string NVTX capture explicitly enables `NSYS_NVTX_PROFILER_REGISTER_ONLY=0`,
  as described in the [NVIDIA user guide](https://docs.nvidia.com/nsight-systems/UserGuide/).
  The earlier no-report attempt is preserved, not treated as a successful trace.

Minimal CPU checks:

```sh
python3 test_protocol.py
$FAISS_PYTHON test_quality.py
python3 -m py_compile *.py
```

## Evidence publication

Public evidence is a whitelisted, redacted text copy. `COLLECTION_MANIFEST.json`
maps original and curated SHA256 values. Failed compiler/lock/oracle/padding
attempts remain visible with their failure status. Original data, index caches,
output binaries and NSYS binary traces are not shipped. Their hashes and
structured trace summaries retain provenance without exposing host paths or
unrelated workloads. No credentials, device configuration or raw conversations
are included. Existing upstream/public history is not rewritten by this task.

This delivery is published on a new standalone branch containing only the two
requested experiment deliveries. It does not inherit older trace/history blobs
and does not remediate exposure in existing repository history. See the root
publication provenance for its source checkpoint.
