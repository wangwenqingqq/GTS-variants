# Claim–evidence ledger

Experiment: `GTSPP_20261015_DYNAMIC_UPDATE_CRITICAL_PATH_RECOVERY_01`.
Date:2026-10-15. Host placement is private; hardware/software and input hashes
are frozen in CONTRACT.json and evidence/IDENTITY.json. Final artifact revision
is the containing Git commit; executed sources use the recorded hashes, with
one explicitly bridged documentation-only placement redaction.

| ID | Exact allowed claim | State | Scope / denominator | Evidence and provenance | Material counterevidence / limit |
|---|---|---|---|---|---|
| U1 | B512 delete is slower than insert in all6 rounds; median ratio5.0177 and paired4.7289,95%CI[4.2277,5.0546] | measured | GIST1M,D960,K8192,PLAIN native Host-ready ACK | PRIMARY_SCALARS.json; TIMING.json comparisons;124 receipt bindings | Pure I/D states differ; R retains coupled sub-ACK control; one hardware/workload |
| U2 | Full W2 D/I move equal1.920GB but issue500000/977 copy calls | measured | CUPTI activity and requested payload;977 ACKs/kind | trace_service.csv;TIMELINES.json;mutation-derived per-ACK binding;RAW_MANIFEST hashes | Payload is not exact DRAM traffic; record granularity not optimization |
| U3 | Copy APIs dominate the profiled B512 delete Host partition | partial | 90.081% of profiled ACK;sync0.228% | trace_D_512.csv;DERIVED.json;actual inner-phase/API multiset checks | Profile/native1.7297×; API may block,not pure CPU-compute fraction |
| U4 | No application update kernels or launches occur on the admitted path; DMA remains nonzero | measured | Required native update ranges;kernel/DMA overlay | TIMELINES.json;source transform;query positive control1895 kernels | Internal driver activity not exhaustively visible;not GPU-idle proof |
| U5 | Larger request batches amortize I/D/R µs per point | measured | B1/32/512 native,6 process distributions;R over2K points | TIMING.json;B_batch_amortization.csv | Changed request granularity;not same-contract algorithm gain or SLA |
| U6 | Fine-grained copy/control is a more plausible large-B first target than explicit stream-wait removal or app arithmetic | inferred | Joint U1–U5 + separately measured bulk reference | DECISION.md;full static/dynamic count agreement | Driver/copy-engine backpressure vs CPU dispatch not isolated;bulk is different contract |
| U7 | W2 update/service share is91.149%; query median saves20.842% but service benefit is not confirmed | measured / inconclusive | Median per-process share;events+release;paired CI[.942238,1.022047] | SERVICE_OPERATORS.json;TIMING.json;DERIVED.json;immutable parent binaries remeasured | No historical R1 result reused;6 rounds and order dependence retained |
| U8 | Ownership-safe coarsening will improve full service | unknown | No optimized implementation or same-contract evidence | No evidence;proposed cheap falsification only | Ordinary batching is prior art;dependent swaps may invalidate naive designs |
| U9 | All GPU trees have this bottleneck | unknown | Not studied | No evidence | Only the inherited append/swap-delete exact-scan implementation is measured |
| U10 | CPU instruction time,exact DRAM/L2 bytes or concurrency gains are established | unvalidated | No stack/scheduler profile,no NCU update kernels,no async variant | Missing evidence explicitly recorded | Rusage and sampled percentages do not fill those gaps |

Public reconstruction reproduces statistics and normalized-table consistency;
only author-side raw revalidation rechecks membership, numerical fields, actual
mutations and every final vector byte. These are distinct gates. R1's stopped
source-lifetime deviation is retained, not silently converted to native evidence.
