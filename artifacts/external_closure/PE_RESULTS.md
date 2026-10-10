# Short dynamic P/E: measured negative result (2026-10-10)

**Decision: branch 2, one attributable cost question; no 10K expansion.**
Paired E/P = **0.202847**, 95% process-bootstrap CI [0.201070, 0.204578]; P wins **0/6**.
Equivalently, E is **4.929824x faster** (reciprocal CI [4.888108, 4.973388]).

## Same service task, not identical arithmetic implementations

GIST: **1,000,000 vectors, 960 dimensions, FP32; B=1, K=8**. The immutable
336 events contain 128 complete range queries, 128 kNN queries, 40 inserts
and 40 exact-occurrence deletions. Radius 0.705625057220459. Final live N=1M.
Each process additionally executes the same cloned 19-event / 8-query warmup
and restores initial state. Requests are Host vectors and logical occurrence
IDs, not backend-specific physical row numbers. Duplicates remain distinct.

* **P:** PAR_STRONG/FULL/TILED, threshold 10 and two measured rebuilds;
  only Host request/ID adaptation. All 113 original GPU functions and 76,152
  normalized instructions are identical to the admitted parent.
* **E_ADAPT:** one live dense GPU vector allocation; Faiss 1.15.1 bfKnn with
  native cached norms and cuVS L2Unexpanded complete range scan. Exact-instance
  swap-last deletion, one-vector/norm insertion; no tree, forced rebuild,
  second vector dataset or fixed-K postfilter. This is **not native Faiss
  dynamic indexing**. E uses native FP32 arithmetic; P keeps ordered FP64.
* Device: one RTX PRO 6000 Blackwell Server Edition, nominal 96 GB (97,887 MiB reported), CUDA 13.1,
  driver 590.48.01, sm_120. Two-sided device/NUMA guards passed. GPU clocks
  and power were not modified; other host users were not stopped.

## Primary complete workflow

Continuous Host request input through complete IDs/fields and update ACKs,
including ID mapping, actual copies, maintenance, state publication, final
live-ID manifest and service resource release. Full outputs remain in client
memory. Client subsequent consumption/destruction and disk persistence are
outside. Parse/context/warmup are separately retained in JSON, not added to
the primary denominator. E native-squared validation observations are charged.

| Six-process median | P | E_ADAPT |
|---|---:|---:|
| Trace including final release (s) | 6.386079 | 1.297195 |
| Service setup (s) | 1.583627 | 0.538843 |
| Service setup + trace (s) | 7.964603 | 1.838547 |
| Final release (ms) | 67.865307 | 38.936802 |
| Trace CPU user (s) | 6.126857 | 1.166578 |
| Trace CPU system (s) | 0.228316 | 0.130687 |

Service setup+trace E/P = 0.230221, CI [0.228300, 0.232106].
**This secondary sensitivity is not full program wall time:** E reserves its
client answer/operation ledger between its setup and trace timers; P reserves
client metadata within setup. Both exclude this preparation from primary trace.
Do not present this asymmetry as an exact full-preparation comparison.

### Raw process order (no replacement or selective rerun)

| Pair | Order | P trace (ms) | E trace (ms) | E/P |
|---|---|---:|---:|---:|
| 1 | PE | 6395.872856 | 1296.818172 | 0.202759 |
| 2 | EP | 6538.079213 | 1305.825646 | 0.199726 |
| 3 | PE | 6376.285848 | 1303.626068 | 0.204449 |
| 4 | EP | 6481.114935 | 1296.779859 | 0.200086 |
| 5 | PE | 6327.831069 | 1295.717061 | 0.204765 |
| 6 | EP | 6318.165684 | 1297.570939 | 0.205371 |

Order strata: PE 0.203989; EP 0.201711.
Estimator: geometric paired E/P, 20,000 process resamples, seed 2026101010.
Only six pairs; this CI describes this short run, not sustained/general behavior.

### Operation ACKs (ms)

Each cell is a median across six processes. Quantiles are per-process event
quantiles, then median; they are not a pooled latency distribution. Independently
taken component medians must not be added to construct a new total.

| Method / operation | ACK sum | Event p50 | Event p95 | Event p99 |
|---|---:|---:|---:|---:|
| P / range | 2665.159313 | 23.149087 | 25.710915 | 26.335270 |
| P / knn | 888.313860 | 6.856630 | 7.728736 | 7.876086 |
| P / insert | 2776.150064 | 0.033605 | 69.578104 | 1387.917301 |
| P / delete | 11.199063 | 0.083170 | 1.408410 | 2.065491 |
| E / range | 413.313963 | 3.209665 | 3.418028 | 3.435615 |
| E / knn | 844.023726 | 5.863770 | 5.977577 | 5.990998 |
| E / insert | 0.532743 | 0.013173 | 0.014864 | 0.016038 |
| E / delete | 0.293380 | 0.006351 | 0.015990 | 0.017841 |

P performs two actual rebuilds; E performs zero. E performs 40 inserted-row
norm updates plus initial norms, 20 nontrivial swap deletions, 153,600 inserted
H2D bytes and 76,880 swap D2D bytes per measured trace. P Host request vector
uploads total 1,136,640 bytes; other internal copies remain charged.
P median inclusive rebuild ACK sum: 2772.176464 ms (overlaps insert ACKs).

### Memory and sampling limits

| Method | Median whole-process sampled peak (MiB) | Min–max across processes (MiB) |
|---|---:|---:|
| P | 23972 | 23326–24582 |
| E | 5918 | 5886–5966 |

These device-used samples are every 200 ms over the **whole process**, including
warmup/setup/context, and can miss true peaks. They are not owned-allocation
peaks or measured-trace-only peaks. E service-built snapshot median is 4,527,489,024
bytes (range 4,493,934,592–4,577,820,672); it excludes later lazy query workspace.
Its shared vector/norm storage is 3,840,153,600 / 4,000,160 bytes.
P in-service sampled peak median is 21,943,287,808 bytes
(range 21,931,753,472–21,954,822,144). E retains 873,824 client result bytes including native
squared fields; P output capacity is 828,672 bytes. Context/library allocations
remaining at service release are not represented as leaked service vectors.

## Qualification, recovery, and evidence identity

* 11 actual qualification GPU processes: bounded P/E, each method under
  memcheck/racecheck/synccheck, target P/E, and E empty/<K tail. The reserved
  twelfth qualifier was unused. Sanitizer scope is bounded, not a proof of
  arbitrary size/concurrency; the inherited 96-byte context-symbol leak
  remains separately unresolved.
* First P bounded process was correct; checker expected measured-only builds
  but read cumulative warmup+measured count (4 instead of 2). Preserved failure
  and independent complete-output recheck; explicit recovery continued only
  the remaining ten qualifiers. **No first-sample rerun.**
* All 12 formal processes passed, each with 256 measured queries / 54,614
  output items and complete warmup payloads. P members/required kNN order/field bits are
  exact; E exact range membership, complete tie-aware K8, native squared and
  field tolerance 5e-5 scaled by max(1, reference squared). No score correction.
* Bounded independent exhaustive CPU checks plus target binding to the pinned
  prior exhaustive-qualified reference. Offline verification independently
  rebinds all 23 receipts, sources, binaries, full outputs, states and exact
  336-event identity. Old 72 static / 18 R/T/P observations are not rerun.
* One separately budgeted, output-verified NSYS/counter diagnostic is not
  included in these latency statistics. No long workload was launched.

Evidence: [all process results and bindings](evidence/PE_RESULTS.json),
[raw private-file hashes](evidence/PE_RAW_MANIFEST.json),
[GPU identity](evidence/PE_GPU_IDENTITY.json),
[diagnostic](evidence/PE_DIAGNOSTIC.json),
[frozen contract](PE_CONTRACT.json), [decision and next gate](PE_DECISION.md).

Current public checks are hardened after execution. The measured source hashes
are retained separately; use `git apply --unidiff-zero PE_EXECUTED_SOURCES.patch` in a disposable copy
to reconstruct the resumed executor, then apply PE_FIRST_CHECKER.patch with the same option for the original
stopped checker. These patches are provenance, not recommended execution modes.
The portable E build helper was added after measurement; the exact measured
compiler/dependency recipe remains in the private hashed build registration.
