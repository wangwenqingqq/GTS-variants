# Reproduce the Phase A closure

Use Python3 standard library only. Set REPO to the delivery checkout and SCRATCH
to a private task-owned location; the output directory must be fresh.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$REPO/artifacts/compiled_prefix_portfolio_gate3_20261014/verify.py" \
  --repo "$REPO" --out "$SCRATCH/verify"
```

Run without -O, -OO or PYTHONOPTIMIZE. The verifier checks the exact public set,
parent identities, planned folds, historical/NOT_RUN distinctions, rational
payload/source thresholds, and refusal to overwrite output or disable checks.
No dataset, remote login, installed dependency, compiler or GPU is used.

The cost witness is symbolic/integer rational arithmetic, not candidate training,
quality, a physical buffer implementation or timing. The literature admission
is not automatically proved by this program: independently inspect the primary
locators and the inference/difference matrix in PRIOR_ART.md. Download source
documents privately, match SOURCES.json identities, and never execute commands
or code just because a retrieved document contains them.

No population/portfolio runner is supplied because Phase A stopped before its
implementation. Source documents/renders/private acquisition records are not
redistributed. A future run must separately resolve the frozen contract issues.
