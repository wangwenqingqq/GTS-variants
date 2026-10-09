# Phase B result: PAR has a narrow workflow win; BOUND adds no confirmed gain

**All 18 fixed short processes are admitted. A→B is 1.684797× (40.65% less
continuous workflow time). B→C is inconclusive. The static native Flat control
is faster at admitted quality on both snapshots. No global default or long
workflow is promoted.** This is original FP32 GIST N1M/D960/B1/K8, radius bits
`0x3f34a3d8`, 336 events: 128 range +128 kNN +40 insert +40 delete, two real
occupancy-10 rebuilds. A has common ordered-FP64/safe-bound repairs; it is not
untouched original GTS.

## Same-round continuous workflow result

| Comparison | Paired geometric baseline/candidate | 95% paired bootstrap | Decision |
|---|---:|---:|---|
| A/B | 1.684797× | [1.683421, 1.685827] | narrow_short_win |
| B/C | 0.998932× | [0.997482, 1.000609] | inconclusive |
| A/C | 1.682998× | [1.681464, 1.684510] | narrow_short_win |

Ratios >1 favor the candidate. A/B and A/C win all six pairs and keep the same
direction in both three-round order strata. B/C crosses 1 and reverses direction
between strata; it cannot be called parity or a net win. All raw values, process
wins, p10/median/p90 and strata are in `evidence/SHORT_RESULTS.json`.

| Round/order | A seconds | B seconds | C seconds |
|---|---:|---:|---:|
| 1/ABC | 86.254137 | 51.193139 | 51.254992 |
| 2/CBA | 86.251750 | 51.207796 | 51.220610 |
| 3/BCA | 86.166712 | 51.240231 | 51.111132 |
| 4/ACB | 86.338040 | 51.215120 | 51.339027 |
| 5/CAB | 86.138044 | 51.083021 | 51.277916 |
| 6/BAC | 86.323563 | 51.202955 | 51.266994 |

The continuous denominator includes complete Host-ready answers, serialized
ACKs, update buffers, compaction/construction, safe-bound refit, required PAR
refresh and mirror repack, and final service-device release/synchronization.
All 54,614 complete ID/FP32-field output items per process (256 queries) and
query ordering matched across 18 processes, and matched an independent exhaustive CPU reference. Measured
initial setup and cloned warmup are separate, not hidden cold-start savings.
The CI estimates repeat-run variability for one frozen trace, not cross-data
uncertainty. It is neither a 10k nor 100k workflow result.

## Actual cost boundaries, not sums of nested medians

Each table cell is independently the median of its six recorded process values.
ACK groups include delivery and synchronization. Rebuild-inclusive time nests
within insertion ACKs; construction/refit/refresh/repack nest within rebuild.
Do not add the rows or subtract their medians to manufacture a denominator.

| Boundary, seconds except where noted | A | B | C |
|---|---:|---:|---:|
| Continuous trace | 86.252944 | 51.205376 | 51.260993 |
| 128 range ACKs | 37.671497 | 2.695217 | 2.708959 |
| 128 kNN ACKs | 0.950486 | 0.884289 | 0.936900 |
| Two rebuilds, inclusive | 47.501476 | 47.535340 | 47.525555 |
| Construction inside two rebuilds | 46.042660 | 46.024359 | 46.026827 |
| Active common numeric refit | 0.699315 | 0.698180 | 0.698380 |
| Active PAR plan refresh | 0.000000 | 0.032362 | 0.030463 |
| Active kNN mirror repack | 0.025142 | 0.025150 | 0.025116 |
| Trace-scoped CPU user seconds | 85.701328 | 50.889287 | 50.964764 |

The two original constructions remain about 46 s; inclusive rebuilding remains
about 47.5 s. PAR principally changes the observed range-query boundary, while
these shared rebuild costs remain. This is attribution by recorded boundaries,
not proof that saved time is exclusively coalescing, pivot reuse or CPU numerical
computation. CPU user time near wall time is not evidence of CPU distance math:
CUDA polling/waiting and host control require separate NSYS attribution.

## Static strong control: retain native speed and quality

These are **six single static diagnostics**, not independent paired or dynamic
end-to-end measurements. Each snapshot has N1M/D960, 32 B1/K8 queries and the
same coordinates/occurrence list. The rebuilt snapshot retains ten duplicate
occurrences. The service pass includes full Host-ready output and final owner
release; native Flat additionally records a pure query pass. Initial setup and
warmup are separately retained. GTS owns tree and mirror state; Flat owns a
static GPU index, not those same service capabilities or dynamic maintenance.

| Snapshot | FULL service ms | BOUND service ms | Native Flat service ms | Flat pure query pass ms |
|---|---:|---:|---:|---:|
| initial | 287.328 | 306.694 | 170.908 | 138.114 |
| first_rebuilt | 287.987 | 298.006 | 171.145 | 138.166 |

Native Faiss 1.15.1 GPU Flat uses FP32 storage, no cuVS and no CPU fallback.
Both snapshots have tie-aware recall 1.0, complete-query fraction 1.0, no
invalid/repeated IDs and no mismatched queries. Both raw native squared fields
and delivered Euclidean fields pass the predeclared scale-1 squared tolerance
5e-5; measured maximum errors are retained, not rounded into bit equality.
FULL/BOUND retain exact internal members, ordering and FP32-field identity.
The native lower times are counterevidence to a broad kNN-library-leading claim,
not a proof about external dynamic mixed/range workflows. Source, queries,
lineage, native extension and full-output hashes are in
`evidence/STATIC_RESULTS.json`.

## Admission and remaining gates

- Eleven original requested access/sync qualifier processes passed; bounded
  memcheck/racecheck/synccheck and million clone/rebuild memcheck report zero
  errors. Every qualifier/warmup has a fresh full CPU/identity check.
- Six observer processes passed: ON/OFF paired ratio 0.999829, CI
  [0.998340,1.001465], all individual ratios <=1.05, complete answers identical.
- All original guards, registered jobs, source identities, full payloads and
  CPU-library/conformance hashes were independently re-bound by hardened offline
  checking. The stale SSH transport is not a successful shell receipt; actual
  complete remote receipts plus the fresh replay admit the 18 samples.
- Enhanced full-leak checking is still **not clean**: R1 192 bytes/14 reported
  allocations; explicit context teardown R2 96 bytes/seven. Phase-A and minimal
  one-managed-int controls are retained. Static-symbol lifetime/tool accounting
  is a local inference, not a confirmed vendor defect. No suppression or manual
  managed-symbol free is used.
- Static delivery used eight process invocations: six admitted diagnostics,
  one unadmitted guard-receipt failure and one pre-GPU native import failure.
  Completed diagnostics were retained; only missing jobs were recovered. No
  optional IVF_ALL, CAGRA/ANN sweep or extra primary round was run.
- Static useful-work/coordinate, per-operator launch/sector and CPU wait-cause
  counts are not admitted by these wall timers. Do not claim a measured BOUND
  coordinate reduction or pure-coalescing-only contribution.

## Next decision, not silent long-workflow promotion

1. Keep B as the **next validation candidate**, not a selected global default.
   Preserve C as an inconclusive implementation under this workload; reopening
   requires a concrete same-contract mechanism/cost control, not more random
   rounds or a favorable estimator.
2. Diagnose original construction/compaction and host wait/control using a small
   separate same-contract A/B NSYS collection. Distinguish GPU distance/sort,
   launch/host scheduling, managed migration and CPU waiting before optimizing.
3. The native Flat quality/speed gap must be addressed in any kNN competition
   claim. Do not bypass it by comparing only all-bucket IVF or quoting internal
   A/C improvements.
4. Before any conditional long range run, close the residual lifecycle boundary
   (or explicitly qualify its scope), admit full-output consumption and freeze a
   suitable long-run guard timeout. Fifty rebuilds alone extrapolate to about
   1,150 s from these recorded construction times, already close to the existing
   1,200 s guard; this is a forecast, not a measured 10k result. Do not launch
   42 unadmitted long processes or change the occupancy threshold to hide cost.
5. Methods/evaluation prose remains private in Overleaf. The five-link ledger
   below grants no novelty, all-GPU-tree, production or general external win.

## Redundancy → mechanism → module → effect → end-to-end

| Redundancy / risk | Mechanism | Module | Observed effect / limit | Complete-workflow evidence |
|---|---|---|---|---|
| Staged range work organization and handoffs | Reused PAR organization | B versus A range execution | Range ACK boundary ~37.67 s→2.70 s; exact pivot/launch/sector delta not counted here | A/B 1.684797×, fixed 336-event scope including added PAR costs |
| Remaining dimensions after a valid kNN cutoff | Eligible seed + ordered safe early termination + selection | C versus B kNN | Same complete output; coordinate/seed cost split not measured here | B/C inconclusive; static BOUND also slower than FULL on these two single passes |
| Divergent search/update views | One serialized owner, published epochs, refit/repack before ACK | Shared state | 54,614 ID/FP32-field output items per process (256 queries); three epochs, two rebuilds; duplicates/current ranks preserved | Functional consistency and charged maintenance only; no split-state saving ratio |
| Rebuilding nearly unchanged service state | Original occupancy-10 full construction remains | Shared update owner | ~47.5 s inclusive rebuild, ~46 s construction; primary remaining bottleneck | Not optimized or claimed eliminated |

Negative evidence and reopen conditions remain in `ATTEMPTS.md`,
`evidence/FAILED_LEAK_DIAGNOSTICS.json` and `evidence/STATIC_ATTEMPTS.json`.
