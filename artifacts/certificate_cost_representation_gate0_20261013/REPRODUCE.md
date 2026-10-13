# Reproduce the admitted work only

Requirements: Python3 standard library, ordinary unoptimized mode. No NumPy,
Torch, CUDA, dataset, pretrained checkpoint, upstream setup or new dependency is
needed. This artifact deliberately has no training launcher.

```sh
cd "$REPO"
ART=artifacts/certificate_cost_representation_gate0_20261013
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/check_artifact.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/equivalence.py"
# Optional: save a fresh, task-owned fixture receipt; never overwrites.
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/equivalence.py" --output "$PRIVATE/new_fixture.json"
```

`REPO` and `PRIVATE` are operator-supplied paths. Optimized mode (`-O`/`-OO` or
nonzero `PYTHONOPTIMIZE`) is explicitly rejected before required checks run.

The fixture uses exact fractions and dyadic coordinates. It realizes only HN's
prescribed norm assumptions, including identical descriptors, opposite tails,
identical tails and independent directions. Boundary checks retain equality for
inclusive range membership. It does not train a loss, run the author's top-1 code,
or qualify floating-point cancellation/rounding, hardware determinism or timing.

For source review, fetch the primary URLs/version pins in SOURCE_IDENTITIES.json
into private storage and compare hashes. HTML wrapper metadata can change; its
retrieval hash identifies the reviewed snapshot, not a guarantee of a permanent
byte-identical response. Prefer the versioned PDF and pinned code for durable
identity. Never run upstream setup scripts merely to perform this source audit.

All post-stop performance/quality fields are null. Reproduction of nonexistent
training results is not possible or claimed. Public files exclude full upstream
contents, private placement, logs/configuration, raw CIFAR/images, model weights
and the confidential manuscript. Old artifacts and user work are preserved.
