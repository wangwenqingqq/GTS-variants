# Reproduction and scope

## Data-free replay

Run check.py --test from this artifact in a full repository checkout. It checks
exact published file identities,the five frozen execution dependencies,the raw
seal/custody chain,all72 output-identity bindings,all scalar rows and the decision.
It rejects isolated-copy manifest/summary/counter tampering. It does not start
C++,read private vectors,recompute distances,or claim a new hardware validation.

## Author-side CPU replay

Linux,Python3.12,g++ C++17 with128-bit unsigned integers;one arithmetic thread,
nice10,serial targets. No installation,benchmark framework,CUDA or GPU required.
Resolve PARENT_INPUTS to the previously sealed sampled Words/DNA traces and
selections whose hashes match the sibling shared_frontier artifact INPUTS.
The original populations are Words611756 and real GRCh38-derived DNA1000000;
only a uniform4096-object subset plus32 reserved incoming is measured here.

~~~sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
nice -n 10 python3 run.py --parent-inputs "$PARENT_INPUTS" --out "$NEW_RUN"
python3 summarize.py --run "$NEW_RUN" --parent-inputs "$PARENT_INPUTS" --out "$NEW_SUMMARY"
~~~

Output directories/files must be new and outside the repository. Source/input
identity mismatch aborts. The driver registers inputs/IDs before each start;
the C++ process emits all calibration radii before any evaluation distance.
Nearest-rank calibration uses separate32 queries;all inclusive ties and repeated
radii remain. No evaluation-guided tuning or retry is permitted. Qualification
is one remote synthetic CPU process;population is exactly two native CPU
processes,one per dataset,600-second limit each and256MiB raw budget.

The build extracts the earlier pinned CPU helper up to,but not including,its
main function. It invokes only metric primitives,cached independent GTS and
Quickjoin. It does NOT invoke shared/query-ball/annulus traversals or the old
self-test that included those paths. Parent helper remains unmodified.

## Timing,quality and missing gates

- Point-pivot values are exact integer edit distances;immutable pivot strings
  are explicitly copied and kept after removing their database occurrences.
- Slot-to-authority IDs and sidecar owner/value swaps are executed. Raw string
  payload movement is symbolic,so the update seconds are NOT full physical
  copying/Host-return ACKs. Index byte fields are declared payload,not RSS.
- Query time includes bound checks,query-pivot distances,survivor verification,
  sorting and materialized full results. Binary20-byte-triple serialization is
  separate,without fsync/durable-storage latency. Validation/export is excluded.
- Native diagnostic checks rederive98048 live certificate entries across both
  datasets/states;these calls are separate,not falsely counted as zero.
  Every query/radius separately pays64*4 query-pivot distances.
- Full outputs are byte-equal to shared-primitive all-pair reference.581 pairs
  use independent DP arithmetic. Complete live ID/score/self-hit checks are
  repeated by the post-run audit without a population rerun.
- Envelope/generation fixture lines are mathematical witnesses,not implementations
  of block repair,generation-aware reuse rejection or mutable-object support.
- No paired CPU latency experiment,p95/p99 claim,native SPB-tree,SFC/B+tree/RAF,
  native GTS update,AV-tree,RECAST,GPU,concurrent-reader or production gate.
  Source-column work alone cannot establish the requested5x/10x full Gate0.

## Preservation

Run seal fixes every raw file before analysis. RAW_MEMBERS and RAW_RECEIPT pin
the private146-member archive;all members were independently hashed/extracted
locally after transfer from persistent remote storage. Complete outputs,sampled
strings,selection files,binaries,launch paths and compiler logs stay outside Git.
Public files contain scalar results,source/input identities and complete output
hashes,not private payloads or original GTS headers.

A local pre-population fixture initially detected an overwritten maintenance-call
counter. The failing source archive/freeze was preserved;the minimal accounting
fix passed fixtures before any calibration/evaluation. PREPOP_REVISION records
this. No population failed,retried,or changed its source/threshold after results.
