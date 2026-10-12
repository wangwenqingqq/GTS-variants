# Claim–evidence ledger

| ID | Claim | State | Evidence / denominator | Counterevidence and allowed wording |
| --- | --- | --- | --- | --- |
| C1 | Original B1 execution reproduced | measured | timing/BATCH_SCALING.json; models/TILE_MODEL_FIT.json; evidence/QUALITY_RECEIPTS.json | Exact original output payloads and function/counters; unpaired fresh-keeper stability, not a speedup |
| C2 | Fixed64 executed-work model | inferred | counters/EXECUTED_WORK.json + models/TILE_MODEL_FIT.json; one selected distance launch/B | Model error 0.03473428%; no direct source constant or full JIT module image |
| C3 | Per-query traffic versus arithmetic | measured | traffic/DRAM_SCALING.json; same NCU denominator and frozen traffic gate | Traffic separation 0.10656802 log2; database reuse is an explicit alternative |
| C4 | Final causal verdict | inconclusive | DECISION.md; frozen CONTRACT.json | Only PARTIAL_PADDING; no silent relaxation of failed conditions |
| C5 | Native batch complete-output throughput | measured | timing/PROCESS_SAMPLES.json and BATCH_SCALING.json; six process means/B | Different invocation shape, B64/128 registered extended pool; p10/p90 are not CI; repeated-single N/A |
| C6 | GTSPP/tree/workflow gain or novelty | unknown | no evidence in this diagnostic | No such claim or paper change; no optimization candidate introduced |

Provenance: base518d846, immutable measurement source/input/library pins and all75 job receipts in evidence/. Publication commit is recorded by Git, not backdated as the measured build revision.
