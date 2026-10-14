# Gate3 prospective clarification 01

**Two contract clarifications are accepted for a separately registered future
run. The closed SUBSUMED_PORTFOLIO admission is unchanged and not waived.**
No dataset, compiler, portfolio, router, sidecar, population or GPU was run.

1. Use exact keeper1,014,828,776B and conservative NO_GO precedence. Only
   capacity PASS admits moment-route evaluation; failed router conditions give
   PORTFOLIO_ONLY after NO_GO checks. Uncovered outcomes remain UNCLASSIFIED
   and stop, rather than being forced into a favorable label.
2. Derive top4 Block32 prefixes only from each fold's24 training queries.
   Candidate identity is source qid. Keep duplicate coordinate subsets, charge
   all four buffers, and materialize coordinates in original ascending order.
   Held-out queries do not enter compilation or tuning.

The CPU lower-bound reasoning requires identical nonnegative terms and
sequential FP64 additions in original relative order. This is not a new quality
pass or a GPU reduction qualification. Other unresolved registration/estimator/
ownership issues remain explicit in [PROSPECTIVE_RULES.json](PROSPECTIVE_RULES.json).

This sibling addendum preserves the original26-file manifest and all executed
source/evidence identities. Nothing retrospectively changes the prior outcome.

## Static identity check

Set REPO to the delivery checkout. This check reads only small public files and
does not start the prospective experiment:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - "$REPO" <<'PY'
import hashlib, json, sys
from pathlib import Path
repo = Path(sys.argv[1])
root = repo/'artifacts/compiled_prefix_portfolio_gate3_20261014_amendment_01'
manifest = json.loads((root/'PUBLIC_MANIFEST.json').read_text())['files']
for name, record in manifest.items():
    raw = (root/name).read_bytes()
    if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise SystemExit('Addendum identity mismatch')
rules = json.loads((root/'PROSPECTIVE_RULES.json').read_text())
for name, digest in rules['parents'].items():
    if hashlib.sha256((repo/name).read_bytes()).hexdigest() != digest:
        raise SystemExit('Closed evidence drift')
if rules['prior_art_gate_waived'] or rules['population_or_GPU_authorized_by_this_amendment']:
    raise SystemExit('Admission boundary changed')
print('PASS: prospective addendum identities;no population/GPU admission')
PY
```
