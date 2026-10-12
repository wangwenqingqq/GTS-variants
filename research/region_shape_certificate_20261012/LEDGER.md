# Experiment and claim ledger

## Premeasurement checkpoint

Experiment: `GTSpp_20261012_region_shape_fixedPCA8`; state: designed. Frozen
contract and G5 sample list written before shape construction or mask evaluation.
Base: `be30912f1f82ddca7cb820c5d42f573c942df173`. No old campaign is modified.

| Hypothesis | Strong competing explanation | Cheapest falsification | Required gates |
|---|---|---|---|
| AABB dead space, rather than projected information loss, limits ancestor pruning | All simple enclosing shapes remain loose or PCA8 itself loses critical separation | Full offline four-shape x three-level count matrix plus separate nearest projected-point diagnostic | All G1-G5; exact old AABB bridge; real packed bytes |
| Centroid placement limits balls | Sphere geometry itself is loose | Fixed 64-step query-independent center heuristic with full stored-center radius | Approximate optimization quality disclosed; no ball-family impossibility claim |

Hardware: shared Xeon Gold 6530 CPU, one NUMA-local core, one library thread,
nice10, task-only lock, bounded 900s phases. GPU hidden; no CUDA events, NCU, NSYS,
sanitizer, sustained workload, latency, or end-to-end system claim is applicable.
Any CPU elapsed resource cost is labeled as resource accounting, not performance.

| Claim ID | Exact scope | Before measurement | Required raw evidence | Allowed wording |
|---|---|---|---|---|
| RS1 | 12 physical cells, 8 frozen queries, 6 hard, P2/PCA8/GIST1M | unknown | full masks, original truth, summary integer counts | Measured safe certifiability in this frozen diagnostic only. |
| RS2 | Three enclosing shapes and real 48/80B record strides | theoretical | enclosing-set proof, full coverage, all G1-G5 | Exact-safe under the frozen arithmetic/domain if all gates pass. |
| RS3 | Shape versus point-set gap in this fixed PCA8 | unknown | full nearest-projected-point lower/upper envelopes | Information ceiling and shape looseness are diagnosed separately, not generalized. |

Promotion uses exact integer Fraction ratios with declared precedence. K3 is
checked before K1 so a strong leaf-only gain is not swallowed by an ancestor-only
kill. K2 requires >128B and is not realizable in this frozen matrix (maximum80B).
An 80B ellipsoid is marked metadata-heavy independently of the terminal decision.
Geometry SIGNAL can include it, but strong/matched-budget admission cannot.

Negative attempts, if any, will be appended with immutable source/raw hashes;
none are converted retrospectively into passes. No shape, query, or safety gate
may be omitted just because its implementation is difficult.

## Audit correction and retained attempt 1

Attempt1 built and evaluated all12cells with zero full safety violations, but
was not promoted or used for final decisions: its receipt hardcoded the CPU
model and published physical placement IDs, and its cached RN diameter proxy
was mislabeled as a certified optimization lower bound in documentation.
Keep immutable source1 archive and build1/eval1 raw output privately. Correct
only provenance/field names and wording, refreeze attempt2, then rebuild and
remeasure ALL12cells plus the full G5 gate. No shape formula, query, membership,
gate, or outcome-based selection changed. Attempt1 is an unvalidated checkpoint,
not negative evidence against the shape mechanism.

## Accepted attempt2 evidence

State: correct -> accepted offline diagnostic -> rejected shape replacements.
RS1 measured: all12cells; three alternatives lose at every level; K1 passes.
RS2 theoretical + measured: all enclosing-set/numerical proofs and G1-G5 pass,
3,552,000 full own-truth checks,0 false prunes,24 exact AABB bridges,384 full
original-vector pairs; raw hashes in evidence/OUTPUT_MANIFEST.json.
RS3 inferred from measured projected point envelopes + containment inequality:
fixed-PCA8 optimistic hard6 ancestor ceiling29.8658%/39.5547%, below45% gate.
Allowed wording is limited to these frozen projected Euclidean enclosures.
No GPU, latency, novel indexing thesis or universal linear-summary claim.
Counterevidence: approximate-center quality remains uncertain, diagonality limits
ellipse expressivity, and replacement shapes need not be subsets of the AABB.
Added costs: ball48B / ellipsoid80B; ellipse outside64B matched budget.
Reopen only on an attributable mechanism escaping this frozen projected-distance
ceiling and a new predeclared comparison; keep negative raw results unchanged.

## Final acceptance refinement: attempt3

Attempt2 passed all recorded checks, but its independent G5 AABB validation
checked full coordinate-error coverage and full G4 bridge rather than explicitly
rebuilding FP32 lo/hi in the separate scalar reference. Do not silently narrow
the requested parameter-recompute gate: add independent signed FP32 endpoint
construction, preserve attempt2 raw/source unchanged, refreeze attempt3 and
remeasure all12cells plus all384pairs. No deployed shape/bound formula, query,
partition, projection or promotion threshold changed. Attempt2 is superseded
for final acceptance, not contradictory performance evidence.

## Accepted attempt3 closure

State: measured and safety-accepted offline diagnostic; explicit replacements
rejected by K1. All12cells were rebuilt and remeasured; all384 independent pairs
pass, including exact signed FP32 AABB endpoint reconstruction. G1-G5 pass with
3,552,000 full checks and zero violations/false prunes. All metadata, truth and
bound arrays and aggregate counts are bit-identical to retained attempt2.
Cross-runtime replay of the accepted attempt3 artifacts passes on
Python3.13.12/NumPy2.4.3 against worker Python3.12.3/NumPy1.26.4, including all
12 packed cells and the32-row original-vector fixture. Final evidence identities
are in SOURCE_FREEZE, OUTPUT_MANIFEST and CROSS_RUNTIME_REPLAY; superseded
attempts and uncurated worker bytes remain private and unchanged. RS1-RS3 scope,
counterevidence, costs and reopen conditions above remain unchanged. No GPU or
timing gate was added or inferred.
