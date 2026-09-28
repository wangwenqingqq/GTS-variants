# Dead count-stage candidate

Tloc 1M 的完整正确性门禁、sanitizer 和四轮配对计时现已完成；正式结果见 [TLOC_RESULTS.md](TLOC_RESULTS.md)。下文保留的是更早的探索和中断记录，不用于正式加速比。

The fused batch-one driver performs a CUB reduction of query flags into
`candidate_count`, then calls `getQnodeCount` (another device-side reduction of
the same flags) and a one-element exclusive scan. The latter two outputs are
only read in the unfused branch, which this candidate does not use. The old
count kernel takes about 2.53 ms in million-point profiles; this is 73.4% of
Tloc's query GPU kernel duration after result fusion.

The separate E/P/R/Q executable compiles on sm_120. R skips the dead count
stage with original traversal; Q combines the skip with multi-CTA traversal.
Tloc N=1,000,000 normal-radius R/Q full outputs both passed independent CPU
distance/membership and exact native ordered float32 hash checks. Their output
files have the same SHA-256. Single-process query means, with only the runner's
mandatory first call before measurement, were R **2.165 ms** and Q **1.891 ms**.
These are exploratory observations, not accepted end-to-end speedups; same-
campaign E/P controls, sanitizer and repeated paired timing are still pending.

The first memcheck attempt was stopped at idle-GPU admission when another
user's process entered GPU 6. No sanitizer or timing sample from this attempt
is claimed. The raw records are under ignored `local/interrupted_gpu6/` and
their hashes and local full-output recheck are in
[PARTIAL_EVIDENCE.json](PARTIAL_EVIDENCE.json). Production GTS source remains
unchanged.
