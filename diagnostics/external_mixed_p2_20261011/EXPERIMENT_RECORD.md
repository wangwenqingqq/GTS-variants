# Experiment record (registered before GPU execution)

| Experiment | Hypothesis | Contract | Methods | Expected delta | Invariants | Raw evidence | Decision |
|---|---|---|---|---|---|---|---|
| GTSPP_20261011_EXTERNAL_MIXED_P2 | Fixed3 may or may not close the external mixed-service gap; the remaining gap may be maintenance, search, output/runtime or mixed | CONTRACT.json | Frozen P2 vs native-maintenance scan E | No implementation change; directly measure remaining gap | Same vectors, occurrences, 336 events, full range/exact qualified K8, final live set | Private fresh scratch, immutable INPUTS/REGISTERED, all raw logs/orders/payloads | Pending qualification and 12 primary processes |

The formal estimator is geometric P2/E (>1 is P2 slower), process-paired bootstrap
95% CI with 20,000 resamples and fixed seed 2026101112. P2 wins mean P2<E.
All primary observations remain in order; first failure stops without replacement.
Six fresh processes per backend; three P2-first and three E-first rounds.

Primary scope excludes separately timed final enumeration/release using adjacent
wall intervals, preserving request submission, native maintenance, full output,
ID mapping and serialized ACK synchronization. Original trace-plus-release is
reported separately; cold loading/setup/context and cloned warmup are not mixed
into either service denominator. Disk serialization and checker oracle are outside.

No new kernel, SASS or NCU campaign is needed for frozen qualified binaries.
Current bounded sanitizer checks are mandatory. One fixed B1 trace is neither a
10K sustained gate nor Graph/concurrency admission. NSYS is explanatory only.
Separate CPU mapping/retention timing does not exist in the frozen programs;
report D2H/payload evidence as partial, rather than inventing an output component
or adding overlapping GPU and CPU wait durations.

## Completed evidence (append-only)

All 26 registered processes passed; no replacements or failed observations.
See evidence/{SUMMARY,PROFILE,REMOTE_CLOSURE,LOCAL_CLOSURE,RAW_ARCHIVE}.json.
Primary ratio P2/E 4.179321, CI [4.145628,4.227814], P2 wins 0/6.
External parity/superiority is rejected for this trace; internal Fixed3 remains
qualified. The registered timer has a small unisolated final-fence/clock tail,
clarified without changing the immutable contract or re-running any process.
Private archives retain every source, binary, case, log, output and profiler file.
