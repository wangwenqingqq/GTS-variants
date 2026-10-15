# Dynamic exact GPU update critical-path attribution — fresh R2

**Finding:** this append/swap-delete implementation retains a per-row copy/control
path as batches grow. On GIST1M/D960, native B512 delete ACK is **1.407446 ms**,
versus **0.280495 ms** for insertion (median ratio **5.0177×**). This is a
bottleneck diagnosis, **not a new optimization, novelty claim, or universal
GPU-tree result**.

**Strongest caveat:** copy API spans may contain blocking/staging/backpressure;
profiler time is not CPU-compute time. The B512 delete profile is **1.7297×** slower
than native timing. Its copy-API fraction **90.081%** and explicit stream-sync
fraction **0.228%** are diagnostic, not native latency fractions. Exact physical
DRAM/L2 traffic and CPU instruction-versus-wait attribution remain unmeasured.

## Same-campaign evidence

| Evidence | Result | Scope |
|---|---:|---|
| Native D/I B512 median ACK ratio | 5.0177× | 6 processes per cell |
| D/I B512 paired geometric ratio | 4.7289×, 95% CI [4.2277, 5.0546] | matched rounds, 20,000 bootstrap draws |
| Full W2 delete / insert payload | 1.920 GB / 1.920 GB | requested and CUPTI transfer bytes agree |
| Full W2 delete / insert copy API calls | 500,000 / 977 | 977 native ACKs of each kind |
| Full W2 explicit syncs | 977 / 977 | delete / insert; no app update kernels |
| Frozen-PDX update share of service | 91.149% | median of per-process ratios |
| Frozen-PDX query median reduction vs S1 | 20.842% | 160 formal queries/process |
| Frozen-PDX service median reduction vs S1 | 1.524% | events + release, same campaign |
| Service paired ratio | 0.983705, 95% CI [0.942238, 1.022047] | **crosses 1; gain not confirmed** |

Native whole-ACK and amortized results, including finite p95 and throughput:
[TABLES.md](TABLES.md). The full service remeasures immutable S1 and frozen-PDX
parent binaries; historical R1 timings do not enter any R2 headline.

## Workload and implementation

- GIST: **1,000,000 × 960 FP32** coordinates, **3.84 GB** (decimal, excluding header).
- Native append and swap-with-last delete, exact range outputs, stable logical
  occurrence IDs. Means remain frozen; no eager statistics maintenance.
- Micro I/D/R: K=8,192, batches 1/32/512; 8 warmup and 32 final validation queries
  outside micro ACK. R is one delete+insert pair: **2B point updates per pair**.
  Insert has an untimed pre-delete; pure I/D states differ.
- Mixed W2: 500,000 replacements = 1,000,000 point updates, 977 replacement
  batches, 160 formal queries (32 fixed queries reused across 5 snapshots),
  8 warmups. This is **not** the separate final10k or formal100k-event study.
- RTX PRO6000 Blackwell Server Edition, SM120, driver590.48.01, CUDA13.1;
  matched NUMA on a dual Xeon Gold6530 host. No GPU settings changed.

## Gates and retention

All **124 fresh processes** passed: 29 qualification, 84 primary and 11 independent
NSYS captures. Every non-selftest output was independently rechecked offline:
complete members/fields, mutation replay, full final maps and every final GPU
vector byte. Small-N sanitizer scope is explicit; it is not production or
concurrency admission. The public verifier reconstructs scalars and evidence
bindings, **not private membership/vector checks or GPU execution**.

The prior stopped 84-start R1 checkpoint is immutable. One subsequent admission
was refused **before CUDA initialization**, with no GPU results. The authorized
fresh idle-card registration used 124 starts, so the preserved cumulative total
is **209/209**, with no automatic retries. See [AUDIT.md](AUDIT.md).

All 11 NSYS captures retain completeness warnings. Exact expected per-operator
inner NVTX phases, runtime API counts and mutation-derived copy bytes/counts
passed, including the 1,895 query-kernel positive control. This does not prove
complete OSRT, scheduler or driver visibility. GPU metric percentages are
quantized, unweighted samples between first and last operator, not per-ACK
utilization or exact traffic. No fabricated zero-byte NCU entries are reported.

## Deliverables and next action

- [DECISION.md](DECISION.md): seven answers, competing explanations and reopen conditions.
- [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md): exact claim states and evidence limits.
- [REPRODUCE.md](REPRODUCE.md): CPU verification and bounded author-side replay.
- [FIGURES.md](FIGURES.md): four PDF/SVG/PNG figures and numeric CSVs.
- [evidence/RAW_CUSTODY.json](evidence/RAW_CUSTODY.json): verified private raw custody;
  captures, vectors, private paths and administrative configuration stay outside Git.

**Next, not executed:** a cheap dependency-safe copy-granularity falsification
and prior-art check, before any optimized implementation. Ordinary batching is
not novelty. An unordered bulk-copy substitution can violate swap ownership.
No new tree/index/async/storage mechanism or manuscript changes were made.
