# Ownership-safe GPU update transformation

**Complete bounded engineering study;novelty not admitted.** GIST1M/D960(3.84GB),single-card exact range service. FINAL lowers same-campaign CURRENT Frozen-PDX W2 events+release by **63.86%**(2.767x);paired ratio95% interval **[0.3404,0.3699]**. B512 delete mean-ACK reduction versus audited NATIVE is **87.12%**.

The strongest caveat:W2 has **zero within-batch dependencies and zero removed row assignments**. Its gain is an executor/control improvement,not proof of a new ownership algorithm or DRAM-byte saving. Synthetic shape timing excludes plan/set destruction and is not the primary ACK denominator.

- [Full report and tables](REPORT.md),[methods](METHODS.md),[semantic proof](SEMANTICS.md),[novelty boundary](NOVELTY_BOUNDARY.md).
- [Claim/evidence map](CLAIM_EVIDENCE.md),[decision](DECISION.md),[reproduction](REPRODUCE.md),[audit](AUDIT.md).
- 341 preserved attempts,340 admitted targets;all passed samples retained,one invalid isolation attempt replaced only with explicit authorization. The original callback false alarm is retained and rechecked offline.
- [Timing scalars](results/TIMING.json),[shape/calibration detail](results/EXTENSIONS.json),[NSYS](results/TIMELINES.json),[NCU](results/NCU.json).

Run `PYTHONDONTWRITEBYTECODE=1 python3 artifacts/ownership_safe_gpu_update_20261015/verify.py` from the repository root for CPU-only source/manifest/statistical verification. No paper manuscript or raw data is included.

Post-run interpretation:[Host API batching versus coarse GPU execution](ATTRIBUTION.md),including the CPU-utilization caveat and retained insert regressions.
