# Correctness scope and receipts

All 22 successful processes pass complete range IDs/multiplicity, tie-aware k=8 membership, declared native-field tolerance, mutation ownership and final state. Formal timing has six matched pairs; qualification and warmup are not extra performance samples.

- Ordinary measured/warmup queries checked: 4,400; plus 128 separate diagnostic probes.
- Mutation witnesses/replay transitions checked: 2,002.
- Actual final GPU vector bytes directly compared to independent CPU replay: 107,524,753,920.
- Range is inclusive ordered-FP64 membership, no false positive/negative. Equal vectors retain distinct logical occurrences. kNN permits exact-distance ties at kth, never drops a strictly closer member; native FP32 fields use frozen 5e-5 scale1 tolerance.
- Actual local mutation witnesses plus the frozen native mutation body support full independent map/live-set induction after every update. This is **not full actual-map export at each mutation**. Actual final full forward/reverse maps and every final vector byte are directly checked, not merely hashed.
- N65/D960 synthetic fixtures cover duplicate deletion, inserted-then-deleted rows, swap-last, row reuse, inclusive boundaries and later-stage coordinates. Both variants pass fixture memcheck/racecheck/synccheck. Full A dry checks run on 1M/D960; there is no full-1M sanitizer, CUDA Graph, unbounded churn or B qualification.

The first fixture guard failed before CUDA initialization because it received out-of-range probe IDs. Its failed record remains preserved; the approved recovery passed an empty fixture probe pool, changed no binary or input and repeated no passed sample. `evidence/RECOVERY.json` binds the original failure and the 30-start cap. One CPU-only resource-export assertion was corrected separately; all GPU observations remain unchanged (`evidence/POSTPROCESSING_CLOSURE.json`).

Public receipts contain hashes and scalar quality details; complete raw answer payloads, ordered score arrays, binary/vector contents and private placement are retained outside Git. Public scalar consistency checks are not a substitute for private full-payload revalidation.
