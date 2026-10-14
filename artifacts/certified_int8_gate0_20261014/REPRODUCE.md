# Reproduce the admission artifact, not an unadmitted experiment

Only Python 3 standard-library checks are needed. Use the checkout root as REPO;
no dependencies, GPUs, original dataset, SSH access or tool installation are
required. Include the three exact parent files listed in CONTRACT.json.

```sh
PYTHONDONTWRITEBYTECODE=1 python3   "$REPO/artifacts/certified_int8_gate0_20261014/check_artifact.py" --repo "$REPO"
```

The checker validates the frozen workload schema/radius relationship, source and
admission identities, explicit NOT_RUN fields, exact storage/update arithmetic,
INT32 limits and tiny rational interval/metric witnesses. It reads no corpus and
cannot run quantization or a candidate population. This is not a residual-bound,
original-FP64 quality, profiler or performance test.

To re-audit prior art, inspect the linked primary texts at the versions/identities
in evidence/SOURCE_IDENTITIES.json. The direct source's metric/precision and
conditional finite-precision assumptions must not be generalized to an identical
ordered-FP64 implementation. Adjacent partial snapshots are labelled partial;
primary live web extraction, not an incomplete HTML file, supported their review.
Full snapshots/PDFs remain outside Git and are not required for the scalar checker.

The declared older parent is preserved as the workload reference; the delivery
base is its verified descendant with byte-identical parent inputs. Do not reset
or rewrite user history. Never run Steps 3-9 or GPU Gate1 from this stopped artifact
without a separate, newly admitted mechanism and contract. No runner, quantizer
or plotting script is deliberately supplied for those cancelled stages.
