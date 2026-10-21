# Reproduction and custody

## Data-free check

Use a checkout containing this artifact and the exact parent dependencies named in SOURCE_FREEZE.json. Python3 standard library is sufficient:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/topk_frontier_cpu_gate0_20261021/check.py --test
```

The check verifies publication/source identities,counters,oracle ratios and output-hash custody. Three intentionally altered copies must be rejected. It does not read the private raw vectors or independently rerun full result membership.

## Authorized CPU population replay

Requires Linux,g++17 support,Python3,and the hash-pinned parent Words/DNA trace and selection files. Raw data is not in Git. Obtain it through its original permitted source route;verify identities against the parent artifacts/shared_frontier_cpu_trace_20261021/evidence/INPUTS.json. Do not substitute protein for DNA. The current4096 reference rows are pinned by the preceding certificate artifact;this run adds64 independently sampled external queries.

```sh
export PARENT_INPUTS=/path/to/verified_parent_prepared
export RUN_ROOT=/path/to/a_new_persistent_run
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
nice -n 10 python3 artifacts/topk_frontier_cpu_gate0_20261021/run.py   --parent-inputs "$PARENT_INPUTS" --out "$RUN_ROOT"
python3 artifacts/topk_frontier_cpu_gate0_20261021/analyze.py   --run "$RUN_ROOT" --parent-inputs "$PARENT_INPUTS"   --seal "$RUN_ROOT.SEAL.json" --out /path/to/a_new_summary.json
```

The runner refuses existing output directories,checks dependencies/inputs before every launch,uses one arithmetic thread,times out at900sec/target and stops at first failure. It does not restart failures. Byte-identical counters/input identities are expected under the same compiler/standard-library sampling behavior;timings/binary bytes are environment-specific. C++ std::shuffle reproducibility across different standard libraries is not promised;the actual deletion-ID lists are retained in raw custody. Changed replay deletion IDs require a new contract,not replacement of published evidence.

Only edit(metric),build_gts,quickjoin,readids and write_hits are reached in the parent CPU helper slice. It includes unused old functions,but no query-ball/annulus/shared() execution occurs. No CUDA is built or launched.

## Custody

The131-member raw archive contains execution sources,binary,input/selection snapshots,full method/reference outputs,counter CSVs,start/exit records,stdout/stderr and pre-analysis run seal. Its SHA256 is e35cfdf63c8174033d31b93dae07cafd410cab76d4ed4eb3ad19d96ac7ca8708;compressed size662347 bytes. Every member was independently streamed and hashed before local extraction. evidence/RAW_CUSTODY.json and RAW_MEMBERS.json identify it without publishing device paths or raw strings. Existing data/source directories were not overwritten or cleaned.

Postprocessing source(analyze.py/check.py) was added after sealed population execution and is identity-pinned by MANIFEST.json,not retrospectively labeled prepopulation code. Independent score DP checks and corruption tests do not replace failed samples;there were no population failures or reruns.
