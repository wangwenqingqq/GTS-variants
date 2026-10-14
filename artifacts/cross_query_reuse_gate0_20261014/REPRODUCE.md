# Reproduce the CPU-only falsification

Python standard library is sufficient for simulation and checks. No GPU, CUDA,
server, dataset download, third-party executable, dependency install or credentials
are required. Run without -O/PYTHONOPTIMIZE; every entry rejects optimized mode.
Run from the repository root with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/cross_query_reuse_gate0_20261014/test_model.py
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/cross_query_reuse_gate0_20261014/check_artifact.py --repo .
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/cross_query_reuse_gate0_20261014/replay.py --repo . --out /tmp/cross-query-gate0-replay
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/cross_query_reuse_gate0_20261014/check_artifact.py --repo . --raw /tmp/cross-query-gate0-replay
```

The four immutable seeds,100k queries/rate, exact50/50 tags,1ps gap rounding,
timer equality priority, cap and drain policy are frozen in CONTRACT.json.
The generator uses Python's standard Random and math routines; compare hashes
under the registered Python3.9.6 environment. Other runtimes must retain their
own hash results rather than silently replace published traces. Raw CSV.gz
headers/timestamps/mtime are deterministic. Complete traces remain outside Git;
their names, compressed sizes and SHA256 identities are in EXECUTION_CLOSURE.json.

The checker reconstructs every synthetic output row when --raw is supplied.
It checks modeled source accounting, not vector-distance exactness. report.py
regenerates scalar JSONs from RESULTS.json into a required fresh --out directory;
it is postprocessing, not measurement. Never regenerate over the frozen artifact.
The executed primary source hash is retained in EXECUTED_SOURCE_IDENTITY.json.
The delivered replay adds only an optimized-mode guard after audit; its algorithm,
contract and raw results are unchanged and the primary run was not repeated.

Optional figure recreation requires an existing matplotlib environment and the
installed paper-figures helper, not a redistributed runtime skill:

```sh
python3 artifacts/cross_query_reuse_gate0_20261014/plot.py --style-root "$PAPER_FIGURES_SCRIPTS" --out /tmp/cross-query-gate0-figures
```

Use the helper's scripts directory and a fresh scratch output, never the frozen
figures directory. The plotter refuses an existing output directory. Reproduced
figures have their own hashes and QA and do not replace the published manifest.
The delivery used matplotlib3.11.0 with
Python3.13.12; no dependencies or hooks were installed. PDF/SVG/PNG and CSVs
are already supplied. Source literature snapshots remain private; inspect the
pinned public URLs in PRIOR_ART.md/SOURCE_IDENTITIES.json instead.

Never infer GPU performance from this replay, mix it with historical offline
batch timing, or launch Gate1 under this NO_GO artifact.
