# L3 residual attribution

**Decision: PIVOT_DOMINANT under the predeclared diagnostic gate, in both captured
rebuilds.** Changed-pivot L3 subtrees contain 90.028% / 92.268% of residual common
object churn and 90.027% / 92.267% of residual leaf churn. R1 only narrowly clears
90%; this is concentration evidence, not a new isolated causal intervention or a
performance result.

Baseline: `955d020a7cf59b12bcc8f210f6da85aa0bb13b6f`, current P2 PAR+FULL,
one million FP32 objects, 960 dimensions, 10-way splits. C3 freezes selected pivot
decisions L0–L2; L3 is the first unfrozen decision level. Both PRE and C3 scoring
records are reused. **New GPU constructions: zero.**

## Read

- [Results](RESULTS.md): all denominators and exact counts.
- [Schema](ATTRIBUTION_SCHEMA.md): correspondence, grouping and rank/tie semantics.
- [Baseline audit](BASELINE_AUDIT.md): inherited evidence versus fresh validation.
- [Decision](DECISION.md): gate margins, limitations and next action.
- [Claim ledger](CLAIM_EVIDENCE.md): permitted wording and counterevidence.
- [Input manifest](evidence/INPUT_MANIFEST.json): 69 selected payload hashes.

## Reproduce without CUDA

Use Python and already-installed NumPy. No build, CUDA runtime, new dependency,
GPU lock, query run or profiler is needed. The script reuses the previous
committed `analyze.py` tree decoder and correspondence helper; run within this
repository at this revision. Inputs are private frozen evidence, not bundled
dataset coordinates or newly generated data.

```sh
TASK=diagnostics/l3_residual_attribution_20261012
python3 "$TASK/scripts/test_attribute.py"
# INPUT_ROOT is the extracted input bundle's inputs directory.
# OUTPUT_ROOT must not exist; preserve old runs rather than overwriting them.
OPENBLAS_NUM_THREADS=1 python3 "$TASK/scripts/attribute.py" "$INPUT_ROOT" "$OUTPUT_ROOT"
cmp "$OUTPUT_ROOT/RESULT.json" "$TASK/summary/RESULT.json"
```

The private input bundle is identified in `evidence/ARCHIVES.json`. It includes
all 69 manifest-listed inputs, actual L3 input/sorted orders, distance keys and
pivot-row captures for PRE_R1, PRE_R2, R1_C3 and R2_C3, plus complete per-parent
results. The selected structure payloads bind to the previous 196-file small
archive manifest; keys bind to the previous full raw manifest. Before analysis,
every payload is rehashed and rebound to those pinned manifests.

**Not done:** C4, freeze-all, stable-pivot implementation, query correctness,
sanitizer/stress, external reruns, dataset changes, or performance measurements.
This result does not repair the previous R2 C1 exception or the failed <=20%
strong structural gate, and cannot be generalized to all GPU tree indexes.
