# Traversal fusion x pivot layout interaction

Preregistered 2026-09-24 before implementation or GPU execution.
Experiment: `gts_20260924_traversal_layout_l2_2000`.
Status at registration: no live GPU admission; previous host SSH unavailable.

## Question and novelty gate

Does traversal fusion change the marginal value of the two previously tested
pivot layouts when result selection is already fused? This is a requested
engineering interaction ablation, not a new algorithm/novelty claim. Generic
kernel fusion and row-major/AoSoA packing are established mechanisms. Prior
negative layout evidence is preserved, not overwritten by a new hypothesis.

## Frozen workload and controls

Reuse the exact GIST/Deep/Tloc fixtures and CPU oracle from the locality campaign
at 5ff0a7428e5c7c308e1c91f89456d6d553788a30: N=2000, dimensions 960/96/2,
64 fixed query IDs, float32 L2, immutable height 3/fanout 10, batch one,
inclusive radius, complete stable CPU-resident IDs/distances/count.
Reuse pinned original source and result-selection fusion. No changed arithmetic,
precision, pow expressions, accumulation order, child mapping, pivot-distance
reuse, query/leaf-vector layout, capacity, or transfer length.

| Graph / stream | Traversal | Pivot layout |
|---|---|---|
| E / D | Separate init, walk, clear | Native |
| R / B | Separate init, walk, clear | Compact [11 parents][dimension], SoA metadata |
| T / C | Separate init, walk, clear | Root separate; [4-parent tile][8-coordinate block][parent][coordinate], SoA |
| F / G | Fused init + two walk/clear levels | Native |
| X / J | Same fused traversal | R layout |
| Y / K | Same fused traversal | T layout |

All six primary arms use result fusion and CUDA Graph. E/F measures traversal
fusion; F/X and F/Y measure layouts added to both fusions; R/X and T/Y measure
fusion within each layout; E/X and E/Y measure the net combination. Compare the
interaction ratios (F/X)/(E/R) and (F/Y)/(E/T) within each process round, rather
than multiplying numbers from different campaigns. No unfused-result baseline
is included, hence no total speedup against untouched GTS is claimed.

## Design card

Target: same RTX PRO 6000 Blackwell Server / sm_120 and CUDA 13.1.115.
One 512-thread CTA/query, each lane owns its original child test, distance
accumulator, node metadata and flags. No shared-memory pivot cache, cluster,
Tensor Core, vectorization, or warp-cooperative arithmetic is introduced.

Ready graph: init flags -> CTA barrier -> level walk (read parent, write child)
-> CTA barrier -> clear parent -> CTA barrier -> next level. All 512 threads
reach every barrier, including inactive lanes and empty branches. Init owns flag
reset; each child flag has its original thread owner; clearing happens only
after every parent read is finished. No atomics/counters in production paths.
Layout producer finishes before capture; packed buffers remain immutable until
all queries complete. Existing downstream same-stream boundaries remain.

Live set: layout pointers and height survive across levels; accumulator/metric
scratch is per child, dead before clear; loop start/num survives until next level;
flags persist globally until candidate selection. No new shared arrays.
Registers/stack/local usage must be inspected after compilation, not predicted
from source scope. Generic unused metric branches remain for like-for-like code.

Expected launch delta: 17 -> 13 kernels/query for F/X/Y, equal useful scalar
math, four fewer kernel boundaries. Added cost: CTA barriers and longer register
lifetimes; R/T retain packing/setup/bytes and address arithmetic. Counterhypothesis:
barriers, compiler lowering or unchanged scalar math erase the launch benefit.

## Measurement and admission

No device is admitted by this file. First re-establish the SSH topology, verify
host/toolkit/source, active users, all GPU processes, selected physical index and
UUID, and acquire the existing device advisory lock. Default to GPU 0 under the
parent agreement; another idle card requires a recorded pre-run amendment under
the user's existing permission to use idle cards. Never change GPU settings or
signal foreign work. Preserve failed admissions. Same device for every arm.
CPU shared/unpinned; record actual driver/power/clock policy. One lock serializes
all benchmark/profiler processes. Sampled process monitoring is not proof of
exclusive device access. Stop owned work on interference; no silent replacement.

Public denominator: complete hot-query wall time including input/output transfers
and host completion. Exclude build, construction, setup/capture, warmups and
output hashing. Record layout setup, driver setup, first query and their actual
per-process amortization over measured queries separately; not cold full-app time.

Gates, before any promotion:
1. CPU source-transform/mode/order checks and existing address-index tests.
2. CUDA compile; exact container and selected-function SASS hashes/resources.
3. Full outputs at -1/0/normal/all, all 12 stream/Graph arms, native A except -1;
   CPU exact membership/tolerant distances plus ordered native float32 bits.
   Fused/native flag equivalence, poisoned flags and synthetic empty masks.
4. Memcheck/synccheck for all 12 arms; initcheck/racecheck for all six Graph arms.
   Fused-flag boundary audit also runs under all four sanitizers.
5. Stress each arm: 64 warmups, 4096 changing queries, full validated hashes.
6. Primary four fresh-process rounds: ERTFXY, YXFTRE, FXYERT, TREYXF;
   every pair is measured twice in either order. 64 warmups and 512 queries/process.
7. Normal-radius sustained: ERTFXY and YXFTRE, 64 warmups and 4096 queries/process.
   Zero/all-hit have full-output coverage, not long-duration acceptance claims.
8. NSYS all six Graph arms, same scope, verify 17/13 kernels and downstream
   signatures. Profiler latency is diagnostic, never the public denominator.

Report every arm, process order, raw p10/median/p90 and process-mean distributions.
Primary summary: median of process-mean latency. Infer direction with exact 4^4
paired log-ratio bootstrap 95% interval and wins/4, keeping it separate from the
marginal ratio. A layout is a useful combination candidate only if all four pairs
win and paired lower bound >1.03 versus F and E, with <=5% sustained regression
in either order and all correctness/resource gates passed. Smaller positive
observations are retained but not promoted. Missing gates mean unvalidated.

No tile retuning, early favorable stopping, cross-campaign denominators, million-
point claims, universal GPU-tree claims or production dispatch changes. Preserve
negative observations with exact scope and reopen only on a new work-ownership,
working-set or measured critical-path hypothesis.
