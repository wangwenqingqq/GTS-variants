# Fixed3 P2 external mixed-service closure — results

**P2 remains 4.179321x slower than the qualified scan adapter on the frozen
336-event GIST service. The excess is predominantly native tree maintenance
(67.04%), then range (32.16%); KNN accounts for only 0.66%.** These fractions are
arithmetic per-process ACK excess divided by arithmetic service excess, not
ratios of component medians, isolated GPU durations or removable-cost predictions.

## Q1. Same logical trace?

Yes: N1M/D960 FP32 L2, B1, K8, radius 0.705625057220459; 128 complete range,
128 KNN, 40 insertion and 40 exact-occurrence deletion events. Both consume the
same immutable vectors/occurrence IDs. Case, data, native oracle, sources, binaries
and libraries were hash-frozen and rebound at closure. Every formal method runs
in a fresh process; order alternates P2/E and E/P2 for six rounds.

## Q2. Same update state?

All per-event accounting follows the common logical replay; full outputs after
updates match that replay. Final live set is exactly 1,000,000 occurrences for
both. Sorted final-set SHA256 is
`e83708c12a7b919146ea9d6a065307f436c09e98309ae850974e3aeeabf7140f`.
Physical final ordering differs, as expected for P2 stable ranks versus E swap-last.
Neither duplicate vectors nor mutable row IDs collapse insertion occurrences.

Twelve current qualification processes passed: N4096 duplicate/base/buffer update
cases, N255 deletion-to-zero then insertion-to-one, three bounded sanitizer tools
per method and the full target trace. Main and restored 19-event/8-query warmup
are separately checked. Empty **live state** passed; cold N0 tree construction
is not admitted. No failure/replacement or implementation repair occurred.

## Q3. Complete range?

Yes on every checked request: full membership, count, IDs and fields, not finite
K filtering. Each formal trace delivers 53,590 range items, plus 1,024 KNN slots.
Total required ID/FP32 payload is 436,912 bytes per backend. E also pays retention
of 436,912 extra native-squared observer bytes. Membership has no tolerance.

## Q4. Exact KNN?

Every qualified request returns complete tie-aware K8 membership and declared
ordering/fields. P2 uses ordered RN FP64 and exact field bits; E uses its native
FP32 squared-distance path with field error <=5e-5 times max(1, reference squared).
No reranking or score correction is applied. This is exact membership on these
frozen fixtures, **not a guarantee for all native-FP32 boundary inputs**. The
N1M oracle is the pinned, previously qualified native-rank oracle mapped to
occurrences; bounded cases use independent exhaustive ordered-FP64 scoring.

## Q5. Whole-workflow ratio?

Primary is the registered **trace-minus-measured-release service metric**. It
includes submissions, copies, native search/maintenance, filtering/top-K, complete
Host IDs/FP32 fields, mapping and serialized ACK fences. Final enumeration/release
is separately charged. A small unisolated post-drain synchronization/clock tail
remains; see METRIC_CLARIFICATION.md. Persistence and oracle checks are outside.

| Metric | P2 | E | P2/E |
|---|---:|---:|---:|
| Service geometric mean | 5234.087 ms | 1252.377 ms | **4.179321** |
| Service median | 5195.166 ms | 1252.238 ms | 4.148704 |
| Service arithmetic mean | 5234.590 ms | 1252.379 ms | 4.179717 |
| Inclusive trace + final enumeration/release, geometric mean | 5307.348 ms | 1290.414 ms | 4.112902 |

Paired process bootstrap (20,000 resamples, seed 2026101112): service 95% CI
**[4.145628, 4.227814]**; P2 wins **0/6**. P2-first ratio 4.196004, E-first
4.162705: neither order stratum changes the result. Inclusive secondary CI
[4.079607, 4.162564]. Raw order/observations are in evidence/SUMMARY.json and
PRIMARY_ROUNDS.csv. CI describes process variability on this **one trace/GPU**,
not confidence across datasets, shapes or hardware. No old ratio was divided by
the Fixed3 internal gain.

### Lifecycle side accounts (not added to service)

Arithmetic per-process means; warmup total includes its own setup/service/release,
so these rows are not all independent costs to add together:

| Side account | P2 ms | E ms |
|---|---:|---:|
| Host data/trace parse | 3183.323 | 3236.135 |
| CUDA context creation | 235.698 | 252.141 |
| Cloned warmup total | 5224.779 | 813.870 |
| Restored measured-state setup | 1553.511 | 539.121 |
| Final enumeration/release | 73.306 | 38.037 |

Disk persistence and retained-client destruction are outside the service timer
and are not separately instrumented; no complete cold-lifecycle latency is claimed.

## Q6. Where is the gap?

Arithmetic sums per full process, ACK scope (query rows already include output):

| Component | P2 ms | E ms | Excess ms | Share of service excess |
|---|---:|---:|---:|---:|
| Insert (40), including real rebuild/refresh | 2659.747 | 0.537 | 2659.210 | 66.78% |
| Delete (40) | 10.692 | 0.288 | 10.404 | 0.26% |
| Complete range (128) | 1690.711 | 409.848 | 1280.862 | 32.16% |
| KNN (128) | 868.100 | 841.688 | 26.412 | 0.66% |
| Between-ACK/timer residual | 5.339 | 0.017 | 5.322 | 0.13% |

Mean service excess is **3982.211 ms**. P2 has two measured native rebuilds;
rebuild-inclusive total is 2656.728 ms (nested inside inserts). Inclusive host
subintervals: compaction 631.180, construction 1288.117, reset 2.977 ms; numeric
refit 678.754, KNN packed refresh 25.095, PAR plan refresh 30.596 ms. They explain
that rebuild is not just the tree-construction kernel; do not add them again to
the ACK or add them to overlapping GPU measurements. E appends/norm-updates and
swap-deletes; it has **zero artificial tree rebuilds**.

One NSYS process per method, diagnostic only: P2 launches 3,684 kernels, including
~1145.343 ms tiled pivot work, ~664.451 ms numeric refit, ~487.501 ms compaction,
~801.742 ms Fixed3 range verification and ~781.495 ms parent traversal. E range
pairwise kernel total is ~400.793 ms. P2 still does material range work, but this
alone does not establish an inherent tree/pruning lower bound. Raw SQLite and
exact copy/kernel ledgers are retained.

### Output/materialization and the CPU-wait trap

| NSYS explicit client output | P2 | E |
|---|---:|---:|
| D2H bytes | 436,912 | 865,632 |
| Device copy duration | 0.439 ms | 0.372 ms |
| Inclusive output-copy API duration | 835.920 ms | 5.556 ms |

P2 KNN output memcpy API time alone is 832.588 ms, but **828.571 ms overlaps
preceding query kernels**. The synchronous D2H call is the observation point for
asynchronous verification/top-K completion. It is not 833 ms of independent CPU
output computation or data transfer, and cannot be added to GPU compute again.
E waits at different APIs; E native KNN squared fields are converted on Host,
so its extra KNN observer bytes are retained without an extra D2H transfer.

These are partial copy-materialization measurements. Host mapping, allocation,
retention and sqrt are charged in ACKs but not separately isolated in the frozen
binaries. Therefore no exact standalone total output cost or output-removal
speedup is claimed. Observed data-copy durations do not explain the fourfold gap.
CPU user time (trace plus release) averages P2 5.053 s versus E 1.163 s; CUDA
busy-wait can contribute, so this is **not proof of algorithmic CPU work**.

### Request tails

Pooled requests from six fresh trace processes; linear-interpolated quantiles,
not independent request-level confidence intervals:

| Method/op | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|
| P2 range | 14.471 | 16.114 | 17.257 |
| E range | 3.184 | 3.373 | 3.395 |
| P2 KNN | 6.649 | 7.599 | 7.744 |
| E KNN | 5.864 | 5.934 | 5.947 |
| P2 insert | 0.030774 | 66.045 | 1329.897 |
| E insert | 0.013033 | 0.015454 | 0.019435 |
| P2 delete | 0.079563 | 1.760735 | 2.356227 |
| E delete | 0.006099 | 0.015304 | 0.017852 |

P2 insert p95 lies between the fast-insert and rebuild populations under linear
interpolation; it is not a typical 66 ms operation. E's rare first KNN reaches
98.407 ms and is below 1% of the pooled sample; its measured NSYS service includes
~91.524 ms lazy pinned-host allocation after restored setup. Totals retain it;
p99 alone must not hide it or justify removing native service costs.

## Q7. External positioning?

**No external superiority or parity is supported.** Fixed3 remains a valid
internal range module, but the present system is materially slower on this
same-logical-service comparison. The dominant next question is maintenance,
with range traversal/verification second—not FULL KNN or another packing factor.

The plan's >3x diagnostic branch is not itself evidence that pruning is the root
cause. Here measured maintenance explains two thirds of the gap. A next research
mechanism must first pass novelty/prior-art Gate 0 and a cheap same-contract kill
test; this campaign does not optimize rebuild, pruning or packing.

## Scope and provenance

12 qualification + 12 primary + 2 NSYS processes, all passed; full receipt and
payload closure, source/library/data/reference pins, target GPU clear after.
Target is authorized GPU1 on RTX PRO6000 Blackwell sm120, driver 590.48.01, CUDA
13.1.115, NUMA0; clocks/power unchanged. GPU0's service was untouched. Other GPUs
had shared-host work at preflight; target GPU was isolated with parent-held locks
and foreign-PID checks. No host-wide exclusivity is claimed. Bounded sanitizer
success does not certify full-N1M sanitizer cleanliness; no 10K, Graph, concurrency,
other K/D/radii, cold N0, or universal field/membership admission.
