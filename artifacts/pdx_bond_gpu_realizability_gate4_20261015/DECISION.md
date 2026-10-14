# Checkpoint, not a final GPU verdict

**Phase A/B/C passed under the explicitly approved fixed32 adaptation.** Phase D
is not validated: the first preparation attempt refused a stale/incomplete
dependency snapshot before any compilation or CUDA initialization. Preserve
that failure, the complete CPU pass, and both pending confirmations. Do not
assign PRIOR_ART_WINS, LOGICAL_WIN_PHYSICAL_FAIL, or PRIOR_ART_LOSES from these
CPU numbers. This is not a novelty stop.

## Five required questions

| Question | Evidence and present answer |
|---|---|
| Q1: How much oracle gap is captured? |49.7383118161%, exact490510893/986183236; **LOGICAL_MODERATE**.32M pairs, no sampling.|
| Q2: Is modeled source better than keeper? |711,680,776B/query vs1,014,828,776B/query, ratio0.7012816278; **SOURCE_WIN** under the800M cutoff.|
| Q3: Does actual DRAM realize it? |**UNKNOWN**; no GPU/NCU result.|
| Q4: Does Host-ready latency realize it? |**UNKNOWN**; no same-campaign keeper or baseline timing.|
| Q5: Is any failure logical or physical? |No logical/source failure. Current blocker is preparation provenance, not physical execution evidence.|

The original and oracle comparators are inherited from the matched-input parent,
not rerun this campaign. They are ideal per-coordinate diagnostics, not staged
GPU fetch counts or unrestricted index lower bounds. PDX p50/p90/p95/p99 are
82/206/266/418 coordinates across the complete finite population.

Stage survivor sums across32 queries are8,452,787 at128,1,784,904 at256, and
130,701 at512. Stage payload sums to22,773,784,832B, divided by32 queries.
That model omits authority-restoration rereads, metadata, control, sectors,
compaction, and output. GPU_DESIGN.md charges those costs rather than granting
free reordered full-score reconstruction.

## Preserved stop and next action

evidence/GPU_PREPARATION.json records three stale validation/controller sources
and one missing curator in the preserved dependency snapshot. Kernel, range
service, and guard source hashes matched; GPU work creation, nvcc invocations,
CUDA initializations, and GPU starts were all zero. No old source was overwritten
and no automatic recovery was launched. The candidate/controller are **draft,
uncompiled, unvalidated source**, not a working GPU implementation.

After explicit recovery confirmation, snapshot only the current task dependencies
into fresh scratch, adjust private source routing, preflight imports/libraries,
register source identities, and build the one candidate and keeper. Preserve
this attempt and all CPU evidence; do not rerun the32M pass. The existing GPU
draft must bind the confirmed decision rules **before** preparation registration
and any CUDA launch. Do not mutate a registered source in place.

Then require static selected-function/resource audit, correctness, sanitizer,
pointer/stream stress,12 alternating fresh-process timings,2 independent
all-kernel NCU diagnostics, and2 event-breakdown processes (26 GPU starts maximum,
no automatic retries). Any quality/isolation failure stops; unclassified valid
result bands remain unclassified. No dynamic work, alternative score/layout,
sweep, or paper novelty is admitted by this checkpoint.
