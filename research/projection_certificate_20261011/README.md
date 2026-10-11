# Exact-safe projection certificate: frozen-tree kill test

**Decision: LINEAR_PROJECTION_CERTIFICATE_KILLED.** Maximum PCA-8 oracle-gap
coverage is **16.857069%**, below the predeclared 30% kill line. Correctness passed;
no GPU implementation or conditional Stage C was admitted. See [DECISION.md](DECISION.md)
and [evidence/SUMMARY.json](evidence/SUMMARY.json).

## Result and denominator

| Level | C0 residual | Truth residual | PCA-8 residual | PCA-8 gap covered | New pruning / G0 visits |
|---|---:|---:|---:|---:|---:|
| L3 | 83.387500% | 0.587500% | 79.337500% | 4.891304% | 4.106464% |
| L4 | 78.508750% | 0.072500% | 73.075000% | 6.927600% | 5.711470% |
| L5 = leaf | 76.271500% | 0.007500% | 63.415625% | 16.857069% | 14.349396% |

Residuals pool 8,000,000 query-object pairs. Gap coverage is
(C0 remaining - candidate remaining)/(C0 remaining - truth remaining).
G0-pruning denominators are the original visited objects at each SAME level:
7,890,000 / 7,611,000 / 7,167,340. Do not substitute C0 survivors or the whole
8M denominator. Each level is a separate counterfactual, not cumulative savings
across levels. Original full ancestor-path bounds are retained; new metadata is
level-local and never composed across ancestors for free.

Random orthogonal prefixes add zero pruning at all three levels. PCA improves
leaf coverage over the strongest <=64B pivot by 3.330208 percentage points, but
loses at L3/L4 by 3.638285/2.261391 pp. This bounded positive exception is retained;
it does not meet the promotion gate. PCA used every database row (1,000,000),
not a query-conditioned fit or a sample. Its top eight directions account for
47.903783% of database covariance variance, not 47.9% of pruning headroom.

## Correctness and scope

- Exact-rational Gram infinity bounds certify the **stored FP64 matrix** has
  operator norm <=1; no reliance on approximate QR/PCA orthogonality.
- Fixed ordered RN-FP64 separate multiply/add projections; signed outward FP32
  endpoints, analytic envelopes, lower-rounded joint sum/sqrt and original-score
  bridge. [SAFETY.md](SAFETY.md) gives the derivation.
- Stage A: 128 frozen query-region pairs, both families and all four prefixes;
  every object in selected regions independently recomputed (45,518 unique rows,
  including queries; 728,288 coordinates); 1,024 sample bounds checked.
- Stage B: 27 distinct cells, 216 per-query cells; 7,104,000 candidate bounds
  checked against inherited region truth, zero unsafe bounds, zero top-K false
  prunes, nested bounds and C0/ownership bridges passed.
- A supplementary Python-scalar cross-runtime replay checks 260 rows / 4,160
  coordinates bitwise. [evidence/SCALAR_REPLAY.json](evidence/SCALAR_REPLAY.json).

This is deterministic offline evidence on **eight frozen stratified development
queries** and one original tree. It is not a random-query population estimate,
universal rejection of linear summaries, proof of partition failure, CPU/GPU
utilization result, actual DRAM traffic, or end-to-end speedup. The generic
mechanism is established prior art: [PRIOR_ART.md](PRIOR_ART.md). No learned model,
nonlinear embedding, new ownership, new query/threshold, CUDA or latency benchmark was used.

## Figures

All figures use complete frozen counts, no invented confidence bands.

1. [Residual vs dimensions](evidence/figures/figure1_residual.pdf): low-dimensional
   boxes leave a large distance from region truth.
2. [Gap coverage](evidence/figures/figure2_gap.pdf): PCA-8 misses the 30% kill line
   at every level; k=4 and k=8 use 32B and 64B aligned records.
3. [Bytes vs incremental G0 pruning](evidence/figures/figure3_bytes_pruning.pdf):
   the previous GLOBAL and query-oracle REGION pivot curves remain explicit.
4. [Gain over strongest pivot](evidence/figures/figure4_joint_gain.pdf): only the
   leaf obtains a positive difference at 32/64B; this is not an isolated
   sum-vs-max attribution experiment.

The primary matched-budget comparator is the strongest GLOBAL/REGION_ORACLE cell
with aligned bytes <= the PCA budget, including Pareto ties at smaller bytes.
This matches the plan's explicit budgets; the wording “same or larger” is
inconsistent with its REGION4=48B example at 64B. The strongest unlimited-budget
pivot is also reported, so the ambiguity cannot create a favorable comparison.
REGION uses the same eight queries for oracle selection and is deliberately an
optimistic adversary, not a deployable query-independent baseline.

## Cost ledgers (not latency)

At PCA-8 the fixed native-first accounting predicts 61,440 query-projection
coordinate updates, done once for all eight queries. Separately, L3/L4/L5 avoid
311,040,000 / 417,312,000 / 987,331,200 original coordinate updates under fixed U*;
metadata-read proxies are 426,944 / 4,019,648 / 39,051,008 bytes. These values do
not measure issued instructions, cache misses, DRAM bytes or GPU time. The offline
validator computes all regions; the cost model charges only C0 survivors in a
hypothetical native-first implementation. FP64 shared basis (61,440B at k=8)
and query cache (64B/query) are separate from per-region metadata. Logical/aligned
bytes are 8/16, 16/16, 32/32 and 64/64 for k=1/2/4/8. Serialized record lengths,
FP32 endpoints and zero padding are verified.

## Reproduction

Use this repository at the recorded base plus this task, Linux x86_64, Python,
installed NumPy and a C++17 compiler. No dependency install or GPU is needed.
Do not use Python -O: assertions are correctness gates. All inputs must match
[evidence/INPUT_MANIFEST.json](evidence/INPUT_MANIFEST.json). Large data, tree,
score matrices, full projected coordinates and metadata binaries stay outside
Git; hashes and portable labels are in [evidence/RAW_MANIFEST.json](evidence/RAW_MANIFEST.json).
The inherited campaigns provide their generators/manifests; obtain the GIST data
and original tree legally and do not substitute a fresh, differently built tree.

```sh
TASK=research/projection_certificate_20261011
RUN_ROOT=${RUN_ROOT:-$TASK/local/reproduce1}
mkdir -p "$RUN_ROOT"
FREEZE="$RUN_ROOT/freeze"; RUN="$RUN_ROOT/worker"; EVAL="$RUN_ROOT/eval"
SCALAR_RECEIPT="$RUN_ROOT/scalar.json"; FIGURES="$RUN_ROOT/figures"
LOCK="$RUN_ROOT/cpu-campaign.lock"
# Set DATA, INDEX, SCORES, ANCESTORS, CPUSET and NUMA_NODE explicitly first.
# Use a new RUN_ROOT for each replay; existing results are never overwritten.
python "$TASK/test_projection.py"
python "$TASK/freeze.py" --index "$INDEX" --scores "$SCORES" \
  --ancestors "$ANCESTORS" --out "$FREEZE"
# Inspect live users/processes first; choose four admitted CPU cores and NUMA node.
# No fixed core IDs or private host settings are supplied by this artifact.
env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  numactl --physcpubind="$CPUSET" --membind="$NUMA_NODE" nice -n 10 \
  flock -n "$LOCK" timeout 600s python "$TASK/build_projection.py" \
  --data "$DATA" --index "$INDEX" --ancestors "$ANCESTORS" \
  --freeze "$FREEZE" --out "$RUN"
python "$TASK/replay_bridge.py" --run "$RUN" --out "$SCALAR_RECEIPT"
python "$TASK/evaluate_projection.py" --freeze "$FREEZE" --run "$RUN" \
  --ancestors "$ANCESTORS" --out "$EVAL"
python "$TASK/plot_projection.py" --analysis "$EVAL" \
  --pivots research/certificate_compression_20261011/evidence/per_level_summary.csv \
  --out "$FIGURES"
```

An ordered 8,192-row mean pass precedes the centered covariance pass. BLAS may
choose directions with its own arithmetic; exact saved coefficients, not the
BLAS implementation, define the certified projection. Pin BASIS.json when
replaying counts across library versions. Eigendirections can change after a
construction-library change; numerical safety must be recertified and counts
remeasured. The measured worker used NumPy 1.26.4/OpenBLAS, four low-priority CPU
cores and inherited NUMA binding; the scalar projector uses one admitted core.
Resource elapsed times are receipts only, never performance comparisons.
