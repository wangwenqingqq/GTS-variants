# Large L2 result-fusion campaign

This directory contains the registered contract, fixture generator, CUDA
driver generator, runner, validation suite and audit script for the GIST,
Deep and Tloc `N=65536`/`N=1000000` comparison. `RESULTS.md` is generated
from `EVIDENCE.json` after all 192 runs pass. The clean campaign uses GPU 1 of
`pro6000-8` and the pinned source hashes in `local/raw/source_pins.json`.
An initial GPU 5 batch stopped when another process entered that card; its
failed receipt is preserved in the remote scratch root and excluded from the
clean campaign.

The immutable registration is `PREREGISTRATION.json`. The runner copies the
generated driver and scripts to a remote scratch root, compiles
`graph_bench.cu`, verifies the preflight hashes, then runs `suite.py` under
the `/tmp/gtspp_gpu1.lock` advisory lock. The stages are full output,
sanitizer gates, stress, paired timing, sustained timing and NSYS traces.
The runner records a receipt, hashes, monitored GPU snapshots and per-query
results for every run. `verify.py` checks complete GPU output against a CPU
float64 oracle and against the native A path before any timing stage.

The local `local/raw/` tree is copied from the remote run root; the audit
recomputes the deterministic CPU validation summaries there. It is excluded
from Git because it includes the binary fixtures, full output and raw traces.
After copying it, the offline derivation is:

```bash
python3 analyze.py local/raw EVIDENCE.json
python3 report.py
```

`analyze.py` fails if registration, binaries, inputs, output hashes, stage
order, GPU admission or sanitizer/profiler checks differ from the contract.
The pairwise interval is the exact six-round paired log-ratio bootstrap.
