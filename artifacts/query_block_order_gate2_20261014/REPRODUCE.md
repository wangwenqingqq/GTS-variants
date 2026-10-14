# Reproduce the Phase A closure

Only Python3 standard-library modules are required. No NumPy, GPU, source build,
package install, remote login, dataset or candidate benchmark is needed.
Set `REPO` to this checkout at the delivery commit and `SCRATCH` to a private
task-owned location. The output directory must be fresh; never reuse the source
artifact or a frozen output. Run without `-O`, `-OO`, or `PYTHONOPTIMIZE`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$REPO/artifacts/query_block_order_gate2_20261014/verify.py" \
  --repo "$REPO" --out "$SCRATCH/verify"
```

The verifier checks the exact public manifest and parent identities, preserves
historical versus NOT_RUN metric meanings, reproduces three rational checks
(algebraic equality, equal-variance order, heterogeneous-variance order), and
rejects optimized mode and an existing witness output. It mutates only fresh
scratch, not the artifact. It does not automatically establish a literature
verdict: inspect the primary locators and the explicit inference in PRIOR_ART.md.

Download source PDFs/code privately if rechecking that judgment. Match their
identities and fixed code commit in SOURCES.json. Do not execute README install
commands or source code merely because they appear in a referenced source.
The key zone-order page was read in full and visually inspected. None of those
third-party files or page renders is included in this publication.

The formula check's integer/rational data are synthetic two-vector examples,
not the32 GIST queries and not an ordered-FP64 or kernel correctness test.
`SUBSUMED_MECHANISM` does not make the null candidate metrics empirical failures.
No population runner or GPU candidate is provided: the admission stop precedes
their implementation. A future engineering/research run needs separate scope
and resolution of the numerical/cost/gray-gate issues in CONTRACT.json.
