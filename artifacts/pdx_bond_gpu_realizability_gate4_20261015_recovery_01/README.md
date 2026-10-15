# PDX/BOND GPU realizability — Gate4 completed recovery

**PRIOR_ART_WINS, with the strong secondary flag.** The known PDX-BOND zone
criterion, adapted to the frozen GPU exact-range contract, reduced complete
Host-ready query latency by **20.55%** and all-kernel DRAM by **30.32%** against
the same-campaign P1 progressive keeper. All 6 paired rounds won; the paired
geometric-ratio 95% CI is **[0.79279, 0.79491]**. This closes an adversarial
baseline test, **not a new ordering contribution or a dynamic-workflow result**.

| Same-campaign result | P1_STAGED_COMPACT | PDX_BOND_ZONE32_GPU | Candidate / keeper |
|---|---:|---:|---:|
| Host-ready ms/query, median of 6 process means | 1.14190696875 | 0.90721087500 | 0.794470039878194 |
| All-kernel DRAM, GB/query | 1.119477888 | 0.780022448 | 0.6967734301510384 |
| All-kernel DRAM reads, GB/query | 1.059262280 | 0.738493768 | — |
| All-kernel DRAM writes, GB/query | 0.060215608 | 0.041528680 | — |
| All-kernel L2, GB/query | 1.215927191 | 0.852924271 | — |

**Workload:** GIST1M, 1,000,000 rows × 960 FP32 coordinates (3.84 GB raw vector
payload), B1, 32 fixed exact-range queries, 8 warmups/process. RTX PRO6000
Blackwell Server Edition, SM120, CUDA 13.1, driver 590.48.01. One initially idle
card, matched NUMA, two-sided process/starttime isolation; no GPU setting changes.
The database is resident before requests. The Host-ready denominator includes
online query priority, sorting, both order uploads, all scan/replay/compaction
and waits, native fields, and complete Host output. It excludes one-time means,
build/load/allocation/upload, offline authority exports, and profiler overhead.

The DRAM denominator is the arithmetic mean over 32 queries in one independent
NCU process/mode, **all 416 captured kernels/mode**. It is not DMA-inclusive
traffic, a repeat-process CI, or a profiler-duration latency comparison.

## What is closed

- **26/26 GPU processes passed:** 10 qualification, 12 primary, 2 NCU, 2 event
  breakdown. No failed/replaced GPU samples or automatic retries; cap 26 unchanged.
- Complete membership and native fields passed for every target request,
  including warmups. Each full-N qualification checked 7,711 internal full-hit
  FP64 scores bitwise against original-order authority: zero mismatches, FN, FP.
- The inherited native observer remains FP32 squared score cast to FP64 and
  FP32 sqrt distance. It is **not an emitted full-FP64 score contract**; internal
  authority and native field checks are distinct, with inherited tolerance 5e-5.
- Synthetic 100-iteration/two-stream/pointer-churn and bounded N4096
  memcheck/racecheck/synccheck passed. No full-N sanitizer, CUDA Graph,
  production-sustained, dynamic update, or 100k-event admission is claimed.
- Fresh keeper's five selected normalized device functions match the historical
  keeper. Selected kernels have no Tensor Core instructions. Static resources,
  profiler diagnosis, correctness, and Host-ready timing are separate gates.

## Evidence and decision

- [Decision and the plan's five questions](DECISION.md)
- [Claim–evidence map and prohibited conclusions](CLAIM_EVIDENCE.md)
- [Verification and reproduction boundaries](REPRODUCE.md)
- [Approved contract](GPU_CONTRACT.json), [recovery](RECOVERY.json), and
  [pre-execution NCU routing correction](NCU_ROUTE_PREFLIGHT.json)
- [Timing samples](evidence/TIMING.json), [every captured kernel's metrics](evidence/DRAM.json),
  [event/ordering costs](evidence/OP_BREAKDOWN.json), [quality](evidence/QUALITY.json),
  [source/binary identity](evidence/INPUT_IDENTITY.json), and [raw archive custody](evidence/CUSTODY.json)

The [immutable 47-file CPU checkpoint](../pdx_bond_gpu_realizability_gate4_20261015/README.md)
still records the previous preparation failure and CPU-only status **at that
checkpoint**, not this completed recovery. No old file was rewritten and no
CPU 32M population was rerun. Its source specification remains authoritative:
the official absolute-deviation criterion, top 3 of 30 zones, selected/remaining
groups in physical ascending order; the confirmed complete 30×32 boundary
adaptation is not a literal upstream port or the official PDX GPU software.

### Four planned figures, without rewriting historical evidence

| Figure | Scope |
|---|---|
| [Required coordinates](../pdx_bond_gpu_realizability_gate4_20261015/figures/required_dims.png) | CPU complete 32M-pair population, not GPU latency |
| [Coordinate source model](../pdx_bond_gpu_realizability_gate4_20261015/figures/source_bytes.png) | Stage-rounded logical bytes, not measured traffic |
| [Measured DRAM](figures/dram.png) | All-kernel NCU traffic, no process CI |
| [Measured latency](figures/latency.png) | Six process means/mode; bars median, whiskers p10–p90, dots individual means |

Each figure has vector PDF/SVG and CSV. The latency whiskers are **not** the
paired bootstrap CI. The headline ratio uses medians; the paired geometric
ratio is separately 0.7938580071195104.

**Next action:** stop treating query-aware ordering as a GTSPP novelty source.
Keep this adversarial comparator for future work. Dynamic means/preprocessing,
inserts/deletes, maintenance/rebuild and complete workflow timing require a
separately frozen, authorized follow-up; nothing in this recovery starts it.
