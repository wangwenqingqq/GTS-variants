# Qualification and sanitizer boundary

All11 registered qualification jobs passed in exact order: synthetic; boundedP1; targetB1; targetP1; boundedREAD_ONLY; synthetic memcheck/racecheck/synccheck; boundedP1 memcheck/racecheck/synccheck. Six sanitizer summaries reported zero errors/hazards.

Synthetic qualification uses100 iterations, two independently allocated streams/pointer sets, N0/1/7/8/9/31/32/33/513/1025, zero and duplicates, inclusive equality, nextafter in/out, reject at each checkpoint, ragged/tail rows, empty/all-hit, hashed high-entropy tails, subnormal differences and repeated pointer churn. All complete checkpoint IDs and fields are checked, not just checksums. The same candidate binary runs synthetic and target jobs.

Target qualification: fullN1M/D960/B1, original8 warmup +32 measured, complete ordered membership/multiplicity and declared fields versus original ordered-FP64. Every retained P1 score is the exact FP32 cast of ordered960 recurrence; FP32 sqrt field tolerance5e-5. BoundedN4096 sanitizers still use the original32 queries loaded from full data, with only the target population bounded.

No full-N sanitizer, Graph, dynamic update, hostile concurrent writer or production stress claim is made. Hashes of all original guard stdout/stderr, process-identity checks, GPU snapshots, commands and raw outputs are in evidence/QUALITY_RECEIPTS.json and evidence/RAW_IDENTITY.json; raw locations/content stay private. The first pre-CUDA import failure remains in the recovery record and is never converted into a pass.
