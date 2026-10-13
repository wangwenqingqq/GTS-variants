# Reproduction boundaries

## CPU-only published artifact check

From a complete repository checkout with Python/numpy installed:

```sh
python3 artifacts/progressive_dynamic_gate3_20261013/test_gate3.py
python3 artifacts/progressive_dynamic_gate3_20261013/check_artifact.py
python3 artifacts/progressive_dynamic_gate3_20261013/build_report.py
```

The last command requires matplotlib and writes the report, CSVs and PDF/SVG/600-DPI PNG plots. This is postprocessing only and never runs CUDA. Generated figure bytes may differ across font/library versions; scalar tables and contract decisions must agree.

## GPU remeasurement (separate authorization and registration)

This published run is closed at UNCLASSIFIED. Do not run B, reuse/overwrite its work directory or automatically retry. A new remeasurement needs its own approved budget and idle same-model GPU. The harness expects an accepted Gate2 prepared workspace (including the strengthened keeper's original336 trace) and the complete hash-matched GIST1M raw FP32 file plus frozen parents/references; hashes are in `evidence/INPUT_IDENTITY.json`. Missing private inputs are not fetched or reconstructed from scalar receipts.

```sh
export G3=artifacts/progressive_dynamic_gate3_20261013
# Set an unused directory outside the repository and the verified Gate2 parent.
python3 "$G3/prepare.py" --work "$NEW_WORK" --parent "$GATE2_WORK" --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 "$G3/static.py" --work "$NEW_WORK"
python3 "$G3/campaign.py" --work "$NEW_WORK" --stage qualification --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 "$G3/campaign.py" --work "$NEW_WORK" --stage A --gpu "$GPU_UUID" --numa "$NUMA_NODE"
```

These commands are documentation, not authority to execute. Preparation freezes sources, generated shared native bodies, input vectors/event order, ordered CPU references and transitive guard imports; it compiles both variants and does not initialize CUDA. Static comparison binds exact selected SASS/full binary containers. Each campaign process uses shared advisory locking, two-sided PID/start-time isolation observation and NUMA affinity. The first failed guard/quality gate stops the campaign without an automatic retry. Apply `analyze.py`'s fixed priority; B is structurally blocked unless A is GO. The original budget is 29; this run's human-approved one-failure recovery cap is 30, total observed starts 23.

The preserved recovery was argument-only: empty fixture probe pool, unchanged data/binaries/query order/timers/quality, new work registration and retained first failure. Do not use recovery support as a general rerun mechanism. The measured source set remains immutable; report/curation changes are explicitly separate CPU postprocessing.

For full private revalidation, freeze `curate.py`'s SHA256 in a JSON file `{"curate.py":"<sha256>"}`, then use `curate.py --work "$EXISTING_CLOSED_WORK" --out "$UNUSED_EXPORT_DIR" --analysis-freeze "$FREEZE_JSON"`. It rechecks registrations, source/binary/library/input/output hashes, complete result/order and guard receipts before publishing only scalar evidence. The full ordered references/payloads are needed to independently recompute the original GPU quality checks; public hashes alone cannot do that.
