# Reproduction and evidence boundary

Use a fresh output directory for every command and Python without `-O`.
The public verification path never initializes CUDA, accesses private inputs,
or replays a benchmark sample. An installed Python3.10+/NumPy runtime is enough
for scalar checks; the optional CPU protocol test also needs a C++17 compiler.

## Public checks

```sh
REPO=$(pwd)
BUNDLE="$REPO/artifacts/dynamic_query_aware_exact_gpu_20261015"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/verify.py" \
  --repo "$REPO" --out "$VERIFY_OUT"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/test_protocol.py" \
  --out "$CPU_TEST_OUT"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/test_audit.py" \
  --out "$AUDIT_TEST_OUT"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/summarize.py" \
  --out "$SUMMARY_OUT"
```

The verifier checks the exact publication whitelist, unchanged parent
checkpoints, source/header identities,72 primary process distributions and
bootstrap statistics, every normalized NCU capture,117 guard/quality receipt
bindings, and the final reserved-memory accounting. It recreates temporary
scalar inputs for the **same frozen analyzer**, not a rewritten estimator.
The CPU-only adversarial audit test rejects consistent wrong commands, extra
files/guards and symlinks. The summary exporter reconstructs the descriptive
update, finite-tail, memory and rate inventory.
CSV reconstruction is only a check of published normalized metrics; it is not
a new profiler run. Cross-platform floating results use1e-12 tolerance; hashes
and integers are exact. The measurement host used NumPy1.26.4.

Public hashes/scalars do **not** independently re-establish complete private
membership, FP64 authority, isolation observations or SASS equality. Those were
checked by the executed target/curator flow. The retained raw reports, original
data and CPU references are needed to repeat those checks. This directory is
an engineering experiment artifact, not a self-contained anonymous AE package.
For committed-tree proof, run the public checks from `git archive HEAD` rather
than an unrelated dirty checkout.

## Figures

Use an installed Matplotlib runtime. `STYLE_ROOT` must contain the separately
installed `paper_style.py`; managed skill/runtime sources are not copied here.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/plot.py" \
  --data "$BUNDLE" --out "$FIGURE_OUT" --style-root "$STYLE_ROOT"
```

The numeric CSVs are the rendering contract; external style/font/version/PDF
metadata is not byte-stable across machines. FiguresA/B concern the frozen W2
synthetic stress, C shows three workload points rather than an optimized policy
Pareto, and D uses arithmetic process means so stacks add. Main single-column
figures are3.5in, composition7.2in; PDF/SVG and400DPI PNG accompany CSVs.

## Fresh CPU preparation and GPU execution

Do not replay into completed work directories. Before a new run, freeze a new
registration, verify an idle same-model card, matched NUMA, current tool/library
identities and the stop rule. Existing inputs and campaign evidence are read-only.
The parent is the preserved complete PDX-GPU Gate4 work directory, whose
registration identifies the original Gate2 compile environment, original
GIST1M FP32 input, exact score references and original static mean file.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8 python3 "$BUNDLE/prepare.py" \
  --stage cpu --parent "$PRIVATE_PDX_PARENT" --work "$NEW_WORK"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/prepare.py" \
  --stage build --work "$NEW_WORK" --gpu "$ADMITTED_GPU" --numa "$NUMA"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/campaign.py" --work "$NEW_WORK" --stage static
```

The first step generates deterministic victims/payloads and ordered exact
references, not GPU results. CPU input-preparation sources are bound separately
from the GPU drafts; finalized adapter sources are bound before compilation.
One raw device representation is used; incoming Host payloads are immutable
client requests, not an uncharged live-index mirror. W2's coordinate permutation
is synthetic and must not be relabeled natural data drift.

Only after the frozen static/quality gates, run `campaign.py` stages in order:
`qualification`, `primary`, `query_ncu`, `maintenance_ncu`. The last two require
the installed NCU and explicitly admitted noninteractive profiling privilege.
The controller uses absolute `/usr/bin/sudo`, forwards the frozen mean file,
and never changes GPU clocks/power. All117 allowed starts are counted, with
no automatic retries; any first failure preserves passed/failed/unexecuted
rows and stops. Qualifiers and profilers never replace primary latency samples.

NCU query capture includes all160 formal requests at five windows, not warmups.
Short zero-hit paths may omit later scans/fields; the parser charges all
captured kernels rather than assuming a fixed13-launch path. The maintenance
capture covers the complete INC/W2 update regions. Its kernel time/SM counters
are diagnostic, not update ACK latency or whole-device occupancy.

## Private full revalidation and custody

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/curate.py" \
  --work "$PRIVATE_COMPLETED_WORK" --out "$NEW_CURATED_OUT"
```

This asserts current source/input/binary identities, every complete native
answer and qualification FP64 hit score, all actual transition witnesses,
entire final maps, the executed every-final-device-byte proof, mean policies,
guard ownership, profiler files and process order. It starts no CUDA process.
Private absolute source/input registrations must still resolve; rebasing is a
new registration, not byte-identical historical reproduction.

`evidence/RAW_MANIFEST.json` identifies raw files without publishing their
contents. Custody receipts distinguish the copied raw-measurement archive from
large immutable data/CPU-reference inputs retained externally. A manifest does
not make those payloads publicly available. Never upload vector data, full raw
answers, private placements, command environments, binaries or profiler binary
containers to Git. No manuscript or Overleaf content is part of this delivery.
