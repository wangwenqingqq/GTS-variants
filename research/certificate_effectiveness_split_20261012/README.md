# Fixed-PCA8 certificate-effectiveness split probe

Offline local-greedy diagnosis starting at `6c0932f`. No GPU code, timing claim,
new projection, certificate, queries, or score semantics. See `CONTRACT.json`
for frozen thresholds and `DECISION.md` for the measured outcome.

## Reproduce

Use the original restricted GIST inputs through the preceding campaigns; this
repository does not redistribute vectors, projected coordinates, score caches,
index membership, or serialized certificates. Their immutable identities and
raw output receipts are in `evidence/INPUT_IDENTITY.json` and
`evidence/OUTPUT_MANIFEST.json`. Obtain/regenerate them with the preceding
campaign's scripts and check hashes before invoking this worker.

The construction worker requires Linux, installed Python/NumPy and the native
`numactl`, `flock`, and `timeout` commands. Unit tests and public integer replay
are portable. Do not run any safety check with Python `-O`: assertions are part
of the contract and the inherited certificate module rejects optimized mode.

From this repository root:

```sh
TASK=research/certificate_effectiveness_split_20261012
python3 "$TASK/test_oracle.py"
python3 "$TASK/replay.py" --evidence "$TASK/evidence"
# Choose new, nonexistent output directories: writers refuse replacement.
python3 "$TASK/freeze.py" --out "$FREEZE"
env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  numactl --physcpubind="$CPU" --membind="$NUMA" nice -n 10 \
  flock -n "$OWNED_LOCK" timeout 900s \
  python3 "$TASK/oracle.py" --freeze "$FREEZE" --prior-run "$PRIOR_PARTITION_RUN" \
    --projected "$PROJECTED_CACHE" --scores "$ORIGINAL_SCORE_CACHE" --out "$RUN"
python3 "$TASK/evaluate.py" --freeze "$FREEZE" --run "$RUN" --out "$RESULTS"
# Copy the public-safe parent diagnostics from RUN to RESULTS for plotting.
cp "$RUN/parent_split_regret.csv" "$RESULTS/"
python3 "$TASK/plot.py" --evidence "$RESULTS" --out "$FIGURES"
```

`$PRIOR_PARTITION_RUN` contains the exact P0/P2 `.i32`/`.npz` files listed in the
preceding output manifest. `$PROJECTED_CACHE` is the unchanged 1M x 16 FP64
cache (PCA8 columns 8:16). `$ORIGINAL_SCORE_CACHE` is the header plus 8 x 1M
ordered original squared-distance scores. Freeze writes 712 independently
sampled parent/oracle ordinals before outcomes: all 100 parents producing L3,
and 128 distinct parents at each of L4/L5, per oracle.

The measured construction runtime was Python 3.12.3 / NumPy 1.26.4. Construction
uses stable, explicit floating reduction order for the radial proposal. Final
count evaluation is replayable on other runtimes; CPU resource times are not
portable performance claims. The complete constructor sort accounting (including
centroid-ID and spread-axis orderings beyond the proposal sorts) is recorded in
`evidence/COST_ACCOUNTING.json`. Matplotlib and pypdf are required only for figures.
An optional `--style-dir` may point at a locally installed publication-style
helper; the plotting script includes a dependency-independent style fallback.

## Evidence semantics

- `parent_split_regret.csv`: every parent of P3/P4 at child levels 1..5.
  `baseline_box_diagonal` is the mean of the ten **S0 child stored boxes**, not
  the parent diameter. The separate `parent_box_diagonal` is the unexpanded
  parent-coordinate diameter. Gains compare proposals on the same oracle parent,
  not the independent P2 hierarchy.
- `proposal_scores.csv.gz`: complete 266,664 proposal rows with all eight query
  counts and all/hard objectives. Duplicates remain in the family.
- `per_query_alignment.csv`: all 96 primary per-query cells, including six hard
  queries and exception 660835; no outcome-based query selection.
- `regret_summary.csv` / `proposal_frequency.csv`: every level, including root
  construction. Lowest-ID ties favor S0; a frequency is not an intrinsic ranking.
- `region_contamination.csv`: all truth-retained pairs at three inherited
  diagnostic thresholds. It never controls certificate pruning.
- `PARTITION_AUDIT.json`: full ownership, P0/P2 byte bridge, every-candidate safety,
  and independently enumerated G4 checks from cached projected coordinates.
- `CERTIFICATE_VALIDATION.json`: full final 12-cell bound safety and 64 B record
  roundtrip. Candidate and final bounds have separate denominators.

A local-greedy oracle is not a global hierarchy optimum. A negative result does
not prove that every tree in the proposal family is bad; a positive result does
not identify a query-independent deployable construction. External performance,
GPU execution, and population generalization remain untested. Generic
workload-aware split optimization is established prior art (`PRIOR_ART.md`).

## Attempt provenance

The first attempt's reference radial centroid did not strictly implement the
frozen sequential fold: Python 3.12+ builtin float `sum` differs under cancellation.
It is retained under `evidence/attempt1/`, explicitly **unvalidated at G4**, not
an admitted keeper. Its `.py.txt` files are forensic snapshots, not imports or
test targets. The accepted second campaign uses the repaired explicit scalar fold
and cancellation regression; all permutations, metadata, proposal tables and final results byte-match the
first attempt (`REFERENCE_REPAIR_BRIDGE.json`). Only attempt 2 is admitted. Raw runs remain outside Git.
