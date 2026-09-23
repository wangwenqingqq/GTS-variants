# Interrupted-device continuation

Recorded before any GPU-0 execution or timing.

The GPU-1 monitor detected a foreign compute process during GIST
`sustained_all_0_L` and stopped only the owned child group. Keep that receipt,
partial telemetry and the original directory; do not rerun or overwrite it.
All six GIST primary rounds completed on GPU 1. Its remaining all-hit sustained
cases are incomplete, so this campaign cannot promote a GIST candidate.

Fresh admission found physical GPU 0 idle with the same model/toolkit/driver.
Deep and T-loc are restarted in a separate scratch root on GPU 0: all full
outputs, sanitizers, stress, six primary rounds, sustained cases and profiler
cases, using the exact same frozen binary, runner and fixtures. The input and
statistical contracts are unchanged. No ratio pools devices, and every primary
pair has a freshly measured same-device comparator. Original GPU-1 Deep/T-loc
gates/profiles remain historical diagnostics, not the primary denominator.

Use the existing GPU-0 lock and UUID process monitoring. No foreign process or
setting is touched. An additional interference stops the continuation and is
reported rather than silently replacing a run. The suite only gains explicit
dataset/device selection; its per-run execution and measurement are unchanged.
