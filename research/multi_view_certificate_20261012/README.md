# Multi-view exact-safe certificate diagnosis
**Result: reject the frozen multi-view family; PCA8 remains the keeper.**

Base ee7851ac046f03242daf78c8bb8a932c0f709987. Unchanged P2, GIST1M D960 K8 B1, eight frozen queries, hard-six primary, 64B/region. Offline counts only; no GPU or latency claim.

At L4 hard alignment is 29.8107% for PCA8, 26.9385% for blocks 2x4, 23.2591% for interleaved 2x4, 14.0105% for Spread32 2x4, and 0% for random. All eleven multi-view configurations lose to PCA8 at L3/L4/L5. Small same-horizon lookahead adds only 0.1080 pp over sixteen frozen parents; not a global upper bound.

## Evidence map
- [Contract](CONTRACT.json), [decision / caveats](DECISION.md), [safety scope](SAFETY.md), [prior art](PRIOR_ART.md), [claim ledger](LEDGER.md).
- [All physical cells](evidence/per_level_summary.csv), [per-query counts](evidence/per_query_summary.csv), [query x view attribution](evidence/query_view_gain.csv).
- [Query prune overlaps](evidence/prune_overlap.csv), [complete per-region common/union-query-count histograms](evidence/region_overlap_summary.csv). Histograms cover every region; private full masks permit identity replay.
- [View manifest / exact proofs](evidence/VIEW_MANIFEST.json). Principal-angle proxy is the **largest cosine**, meaning the smallest principal angle; numerical diagnostics are not contraction proofs.
- [Four vector figures](evidence/figures/multi_view_evidence.pdf): data-driven, final width 7.05 inches, >=7pt; no invented CI for exact fixed-workload counts. Figures 2/3 use the preregistered four distinct 2x4 families at L4.
- [Separate lookahead](evidence/LOOKAHEAD_SUMMARY.json).

Sixteen logical configurations x3 levels deduplicate to twelve physical configurations / 36 cells. D1 layouts alias blocks; D2-8x1 aliases blocks-8x1. Aliases are explicit, not independent evidence. Basis generation, groups, seed/order, queries/U*, samples, gates and denominators were frozen before primary outcomes.

## Reproduce
Use this repository revision and its pinned base helpers, not standalone copied scripts. Use the existing Python/NumPy and g++ installations; the Linux worker also requires numactl, timeout and flock. Plotting requires existing Matplotlib and pypdf; no new framework/dependencies are installed. Construction used Linux x86_64, Xeon Gold 6530, Python3.12.3, NumPy1.26.4, OpenBLAS0.3.26, g++13.3.0. PCA fitting refuses covariance/mean or PCA8-byte drift. No Python -O. The ordered projection/score contract disables FMA, reassociation, FTZ and DAZ; covariance fitting uses the pinned BLAS procedure. Frozen-basis/count replay does not require refitting on another runtime.

Public, data-free replay:
```sh
python3 -m unittest discover -s research/multi_view_certificate_20261012 -p test_views.py -v
python3 research/multi_view_certificate_20261012/replay.py
```

Original data, full projected caches, permutations, NPZ fixtures and binaries are **not published**. Resolve authorized inputs against INPUT_IDENTITY.json, old BASIS.json and previous output manifests. Set DATA, OLD_CACHE, SCORES, PRIOR_RUN, RUN, CPU1, CPUS4, MEM_NODE in your environment. PRIOR_RUN holds the exact old PCA_BALANCED.i32/.npz. Check live users/processes and resource availability first.

Explicit CPU-only run with task-owned advisory lock:
```sh
env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
 numactl --physcpubind="$CPUS4" --membind="$MEM_NODE" nice -n10 \
 flock -n "$RUN.lock" timeout 900s python3 research/multi_view_certificate_20261012/build_views.py \
 --data "$DATA" --out "$RUN/build"

env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 numactl --physcpubind="$CPU1" --membind="$MEM_NODE" nice -n10 \
 flock -n "$RUN.lock" timeout 900s python3 research/multi_view_certificate_20261012/evaluate_multi_view.py \
 --data "$DATA" --old-projected "$OLD_CACHE" --scores "$SCORES" --prior-run "$PRIOR_RUN" \
 --build "$RUN/build" --out "$RUN/eval"

env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 numactl --physcpubind="$CPU1" --membind="$MEM_NODE" nice -n10 \
 flock -n "$RUN.lock" timeout 900s python3 research/multi_view_certificate_20261012/lookahead_probe.py \
 --old-projected "$OLD_CACHE" --scores "$SCORES" --prior-run "$PRIOR_RUN" --out "$RUN/lookahead"

python3 research/multi_view_certificate_20261012/replay.py \
 --private-run "$RUN/eval" --bridge "$RUN/build/bridge_vectors.npz"
```
Regenerate the four figures with existing Matplotlib/pypdf:
```sh
python3 research/multi_view_certificate_20261012/plot.py --evidence "$RUN/eval" --out "$RUN/figures"
```
The optional --style-dir selects an installed plotting helper; the built-in fallback requires no external helper.

For a new run, curate its CSV/JSON/manifests into separate evidence and supply --evidence to replay. Do not overwrite this campaign. Output creation refuses replacement. No GPU program, GPU setting, foreign signal, new workload, or automatic deeper experiment is involved.

## Costs / scope
64B per region; shared basis 61,440B/config, plus 64B/query projection cache. Separate basis storage is not a per-region freebie. Query projection uses 8x960 coordinate updates/query; bound evaluations grow with view count. Physical SASS/cache transactions and wall latency were not measured.

The raw evaluator manifest hashes every private mask, packed record and truth cache. Raw lookahead sort_calls=23232 means **proposal-order sorts**, not every implementation sort. COST_SUPPLEMENT separately accounts for centroid-ID and spread-axis sorts without changing frozen code/results. Symbolic operations are not timings.

No canonical paper source, prior campaign, default branch, device configuration or dataset was edited. Preserve existing visibility; a scoped research branch is not a merge or submission.
