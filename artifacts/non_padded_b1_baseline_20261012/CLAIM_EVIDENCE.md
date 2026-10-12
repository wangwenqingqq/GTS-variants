# Claim–evidence ledger

Experiment: GTSPP_20261012_NON_PADDED_B1_BASELINE; base682c404; verified
2026-10-12 on the same privately pinned RTX PRO6000 Blackwell/188SM, CUDA13.1,
driver590.48.01, cuVS26.8.1. Public scalar receipts bind source, binary, data,
libraries, guard, raw output and profiler hashes. Full raw evidence stays private.

| ID | Claim / status | Exact scope and denominator | Evidence / quality | Strongest caveat / allowed wording |
|---|---|---|---|---|
|B1|Complete-output baseline established — measured|GIST1M/D960 FP32 B1 initial, fixed32 queries;8 warm+32 measured/run|CONTRACT; correctness/QUALITY; evidence/INPUT_IDENTITY and QUALITY_RECEIPTS|Exact tested membership; N1 field tolerance not native bits. No all-input/all-shape proof.|
|B2|ACK reduction23.1861%,1.301847× — measured|Six fresh processes/mode; medians of process means; Host ready→complete Host output|timing/BASELINE_TIMING; paired ratio0.767830 CI[0.759850,0.775864],6/6 wins|Same-campaign native slightly slower than historical band; no profiler/old keeper timing substituted.|
|B3|Inflation64.022230→1.045155× — measured|One independent main-kernel NCU capture/mode; FADD+FMUL+2FFMA /2.879G useful ops|profiler/NATIVE_METRICS and NON_PADDED_METRICS; no membership change|Proxy excludes control/integer work; no CI;64× arithmetic is not64× recoverable latency.|
|B4|93.6846% latency recovery — measured|Same six-round triples, primary median ACKs; R0 structural control|timing/GAP_ACCOUNTING; matched-round recovery CI[93.2798%,94.1160%]|READ_ONLY is checksum/reduction, not search or universal lower bound.|
|B5|Near streaming frontier — inferred|Same dataset/shape; N1/R0=1.020771 and residual2.0348% N1|B2/B4 plus1530.511 vs1532.455GB/s independent NCU|Supports bounded memory-frontier interpretation, not compulsory-byte proof or all-GPU-tree limitation.|
|B6|Bandwidth recovery99.4780% — measured|Total real DRAM bytes/same NCU duration, one capture/mode|profiler raw-CVS hashes and scalar metric fields|No confidence interval or ACK throughput claim.|
|B7|Short integration trace reduction7.7132% — partial|One old→strengthened336-event pair,40I/40D/128R/128K, initial1M/D960|timing/DYNAMIC_INTEGRATION;256+8 full queries/final state each|Single forward pair; original reference false failure and authorized recovery retained; no stable/sustained system claim.|
|B8|Baseline repair is not GTSPP novelty — rejected novelty thesis|Direct B1/small-M specialization|PRIOR_ART immutable current/release routes and cheap novelty kill|No matching inspected API does not mean no prior direct vector reduction. Ordinary engineering cannot be repackaged as novelty.|
|B9|Safe representation can reduce charged bytes — unknown|Future separately frozen Gate1, including refinement/update/consumer costs|No implementation/evidence this round|May enter falsification only; no current byte-saving, tensor-core or compression claim.|
|B10|Old PARTIAL_PADDING should become CONFIRM_PADDING — rejected|Prior causal contract, not this replacement comparison|Old failed traffic gate retained at base682c404|New ownership/reduction/schedule changes do not retroactively validate unconfounded padding causality.|

All point classification gates and CI estimators were frozen. Negative/failed
preflight/postprocessing/reference observations remain in ATTEMPTS and raw hash
index. Graph/full-N sanitizer/sustained workflow are not missing evidence hidden
as a pass: they are outside this qualification scope and forbid promotion there.
