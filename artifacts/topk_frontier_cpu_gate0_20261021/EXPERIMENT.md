# Experiment record

| Experiment | Hypothesis | Contract | Ordinary controls/oracle | Predicted counts | Invariants | Raw evidence | Decision |
|---|---|---|---|---|---|---|---|
| GTSPP_20261021_TOPK_FRONTIER_CPU_GATE0 | Deletion-raised kth distances reopen old pruning decisions;ordinary saved-frontier repair may already eliminate redundant recertification. | CONTRACT.json,frozen before population | Root restart,saved frontier,k+32 reserve,full rank cache,seeded Quickjoin;fixed-tree threshold oracle | If lower-bound priority continuation is already sufficient,it approaches the future-threshold oracle without recomputing old score pairs. | Exact source-ID ties;no future oracle input to online methods;complete outputs,all costs retained. | To be appended after run;source/input/binary freezes required. | DESIGNED;novelty NOT_ADMITTED;0GPU. |

Hardware/software will be recorded from the live CPU host before execution. GPU clock/power,CUDA library selection,SASS,sanitizers and GPU timing are not applicable because no GPU binary is built or launched. CPU bounds/metric fixtures and complete member/score checks are mandatory.

## Completed evidence

Two admitted CPU targets passed without population failure/retry. Source/input/binary/argv and all60 method streams were read-only rechecked;5803 emitted score pairs were independently rederived with DP. Raw custody and the pre-analysis seal are in evidence/. Threshold expansion is observed;near-oracle decision stops the fixed-tree cached-score family. No native/GPU performance admission. See REPORT.md for material cache/oracle limitations.
