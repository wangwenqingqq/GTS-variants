# Reproduction boundaries

## CPU-only public verification

From this repository root, with Python3 and NumPy:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s artifacts/non_padded_b1_baseline_20261012 -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/non_padded_b1_baseline_20261012/verify.py
```

The tests cover scheduling, complete-output parser rejection, gray/gate
boundaries, estimators, NCU units/categories and logical-ID/live-rank ownership.
verify.py validates the exact public manifest/frozen sources, re-derives every
static estimator/CI from all public query ACKs and NCU scalar counters, and
recomputes dynamic operation totals/trace ratios. It does not run CUDA or claim
to recover full private payloads from hashes.

Regenerate three tables/figures with existing matplotlib and an installed figure
helper (runtime skill files are installation-owned, not copied into this repo):

```sh
python3 artifacts/non_padded_b1_baseline_20261012/report.py \
  --figure-skill "$FIGURE_SKILL"
```

Authoring is3.5-inch print size; PDF/SVG vector plus300DPI PNG; figure1 p10/p90
process whiskers are not a CI; figures2/3 have one diagnostic each. The shipped
plots and CSVs suffice without the optional local plotting helper.

## GPU reproduction requires a newly authorized isolated campaign

No command below is an automatic continuation or permission to exceed the
completed31-start budget. Keep vendor sources/settings/other users untouched.
Validate idle physical device, NUMA, toolkit, exact loaded libraries and
data/oracle identity first. Reuse the parent query-tile-padding and exact-scan
work registrations; they supply the original native/READ_ONLY binaries and
ordered-FP64 reference arrays. Their portable recipes are in the corresponding
parent artifact directories. Large GIST vectors/payloads are not redistributed.

Dataset manifest: FP32 row-major `.f32bin`,12-byte int32 header[D=960,N=1M,2],
3,840,000,000 payload bytes; SHA256
`f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7`.
Exact query IDs/reference hashes, native/candidate/library hashes and frozen
source closure are in evidence/INPUT_IDENTITY.json. Do not substitute another
normalization, query pool, radius, metric, field contract or timing scope.

`prepare.py` is CPU-only: private generation replaces one distance call in the
original Scan and adds a fixture entry to the original B1 driver. Build flags
are inherited unchanged: C++17,O2,lineinfo,sm_120, same cuVS/RMM/logger libraries.
The generated source diff/compile log/binary hash remain private and indexed.

```sh
python3 artifacts/non_padded_b1_baseline_20261012/prepare.py \
  --work "$NEW_WORK" --padding "$PADDING_WORK" --roof "$ROOFLINE_WORK" \
  --gpu "$GPU_UUID" --numa "$NUMA"
# Run each stage only after the preceding gate passes, under the shared guard.
python3 artifacts/non_padded_b1_baseline_20261012/campaign.py \
  --work "$NEW_WORK" --stage qualification --gpu "$GPU_UUID" --numa "$NUMA"
python3 artifacts/non_padded_b1_baseline_20261012/campaign.py \
  --work "$NEW_WORK" --stage primary --gpu "$GPU_UUID" --numa "$NUMA"
python3 artifacts/non_padded_b1_baseline_20261012/campaign.py \
  --work "$NEW_WORK" --stage ncu --gpu "$GPU_UUID" --numa "$NUMA"
python3 artifacts/non_padded_b1_baseline_20261012/analyze.py \
  --work "$NEW_WORK" --out "$NEW_ANALYSIS"
```

The existing four shared device locks, campaign flock and two-sided process
starttime ownership guard serialize every run. NCU uses an already authorized
profiling account; no driver setting changes. Public latency excludes replay.
29 static starts,8 warmup+32 measured queries/process,6 alternating round triples;
bootstrap20,000 seed2026101212. First quality/runtime/isolation failure stops.

## Conditional dynamic integration and retained recovery

dynamic.py preserves the **original failed attempt's exact source**, not a
recommended fresh-run orchestration. The device kernel was unchanged; only
the host ceiling was extended to trace capacity1,000,040. The old binary and
new binary retain Faiss kNN, native norms, insertion/swap deletion/bookkeeping.

Its reference was already in stable logical IDs, whereas the supplied-reference
branch of the inherited pe_check.py expects live ranks. Do **not** intentionally
rerun this known false failure or silently edit frozen parent evidence.
recover.py documents the explicit CPU bijection and stopped-output recheck, and
contains the separately human-authorized one remaining process. That GPU
recovery is closed at31/31 and must not be rerun.

For a future dynamic campaign, preflight the reference ownership using the
tested CPU normalization before freezing a **new** contract. Reuse retained
outputs rather than repeating passed samples. The present short pair has no
CI/sustained gate and does not establish all-workflow benefit.

## Publication and raw evidence

PUBLIC_MANIFEST.json enumerates the exact ship set. evidence/RAW_EVIDENCE_IDENTITY
indexes full external evidence without disclosing deployment identifiers,
vectors, payload contents, vendor reports or raw SASS. Keep negative evidence.
Only task-owned additive code/scalar/figure files are uploaded; no manuscript,
credentials, session transcript, host configuration or library binary is public.
