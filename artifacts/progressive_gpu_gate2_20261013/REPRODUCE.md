# Reproduce without disclosing placement

This is an evidence-complete bounded prototype in the existing repository, not a standalone dependency installer or production artifact. Use the full checked-in source tree at this revision; the preserved guard's six transitive Python files must be present. Do not repeat the historical import failure to reproduce it.

Prerequisites: the original GIST1M fixture (12-byte header960/1000000/2 plus unchanged FP32 row-major payload; dataset SHA in CONTRACT.json); the original32 full ordered-FP64 reference arrays; the accepted strengthened keeper preparation directory; Gate1 required-dimension arrays and private registrations; installed CUDA13.1/CUB/cuVS and exact linked-library hashes. Their content is not redistributed. The parent accepted artifacts describe generation. Select a genuinely empty same-model single GPU and verify its NUMA locality; no GPU setting or foreign process modification.

CPU tests (no GPU starts):

```sh
cd artifacts/progressive_gpu_gate2_20261013
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_gate2 test_evidence
```

Keep all work directories outside the repository. Bind `$KEEPER_WORK`, `$GATE1_WORK`, `$COST_WORK`, `$WORK`, `$GPU_UUID` and `$NUMA_NODE` to private inspected destinations, never credentials or hidden defaults. The CPU cost screen must finish/admit before preparing CUDA:

```sh
python3 pre_cost.py --work "$COST_WORK" --keeper "$KEEPER_WORK" --gate1 "$GATE1_WORK"
```

For exact identity reproduction, compare the scalar proof to cost/REPLAY_SCREEN.json (including source/compiler/binary identities); fresh reruns have their own registration/time identities and must be prospectively frozen rather than relabeled as the original proof. `prepare.py` intentionally binds the admitted CPU result to its public frozen receipt. For a new campaign, freeze its admitted receipt before the first GPU start.

```sh
python3 prepare.py --work "$WORK" --keeper "$KEEPER_WORK" --gate1 "$GATE1_WORK" --cost "$COST_WORK" --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 static_evidence.py --work "$WORK"
python3 campaign.py --work "$WORK" --stage qualification --gpu "$GPU_UUID" --numa "$NUMA_NODE"
# Continue only after all11 qualification jobs pass; first failure stops.
python3 campaign.py --work "$WORK" --stage primary --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 campaign.py --work "$WORK" --stage ncu --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 campaign.py --work "$WORK" --stage breakdown --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 campaign.py --work "$WORK" --stage nsys --gpu "$GPU_UUID" --numa "$NUMA_NODE"
```

NCU permission uses the existing authorized sudo environment; do not embed passwords or change driver settings. Independent all32-query/all-kernel capture has no kernel-name filter/launch count. `nsys` is a registered conditional stage: this campaign correctly skipped it because latency ratio<=0.80 and CIupper<0.90. Fresh campaigns that miss these gates require actual trace-based causal attribution before any control-bottleneck claim.

Freeze postprocessing source hashes (curate.py, analyze.py, test_evidence.py) in a private JSON before curation, then export only scalar/hash records:

```sh
python3 curate.py --work "$WORK" --out "$SCALAR_EXPORT" --analysis-freeze "$ANALYSIS_FREEZE"
python3 report.py --figure-skill "$FIGURE_SKILL"
```

For the original recovery only, `prepare.py --recovery "$APPROVED_RECOVERY"` validates the preserved failed guard ledger/result, human approval, old1/new33/global34 budget. A clean fresh campaign omits this argument and has the original33 ceiling. Never create fictitious failed samples/approval or auto-retry a failed process.

Raw private source/build registrations, all guards, payloads, checkpoints, selected SASS/resource dumps, NCU reports, samples and stage CSVs are hash-indexed in evidence/RAW_IDENTITY.json. The committed scalar export can be reanalyzed/plotted without raw deployment paths. `PUBLIC_MANIFEST.json` covers the complete public ship set; do not upload raw dataset files, device configuration, credentials, conversations or vendor report binaries. Four vector PDF/SVG plots and PNG previews have final-size, grayscale and600DPI QA. No manuscript/Overleaf content is part of this delivery.
