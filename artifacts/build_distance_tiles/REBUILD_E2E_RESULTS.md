# Build-distance tiling: fixed-workflow evidence

**B1 passed the frozen internal short-workflow gate: paired B0/B1 8.029943×,95% CI [7.955661,8.104259].**
This is an engineering improvement over freshly remeasured PAR+FULL with the original build mapping, not over untouched GTS, CPU trees, IVF or CAGRA.

## Task and denominator

Original FP32 GIST **N1M,D960,B1,K8**,radius bits0x3f34a3d8.336 events:128 range+128 kNN+40 insert+40 delete,2 actual occupancy10 rebuilds.
Twelve fresh primary processes,six alternating direction-balanced pairs. Continuous Host-ready/ACK time includes full outputs,buffer work,all maintenance and final owned-service release. Setup and cloned warmup are separate; no profiler denominator.

| Round/order | B0 seconds | B1 seconds | B0/B1 |
|---|---:|---:|---:|
| 1/B0B1 | 51.256555 | 6.491991 | 7.895352× |
| 2/B1B0 | 51.156551 | 6.479543 | 7.895086× |
| 3/B0B1 | 51.097581 | 6.307164 | 8.101515× |
| 4/B1B0 | 51.232026 | 6.357623 | 8.058362× |
| 5/B0B1 | 51.254760 | 6.329444 | 8.097830× |
| 6/B1B0 | 51.138476 | 6.286125 | 8.135135× |

Candidate wins **6/6**. Order strata: B0-before 8.030984×; B0-after 8.028902×. Marginal median ratio 8.070311×.
Paired elapsed-time reduction is 87.547%. The paired bootstrap estimates repeat-run variation on this one fixed trace, not variation across datasets or100k events.

## Cost boundaries

Every cell is independently the median of its six process values. Rebuild is nested within insertion ACK; build/refit/refresh/repack are nested inside maintenance. **Do not sum these rows or subtract medians to create a denominator.**

| Boundary | B0 | B1 |
|---|---:|---:|
| Continuous workflow,s | 51.194288 | 6.343533 |
| Initial setup,s | 23.925953 | 1.572403 |
| Setup+trace,s | 75.120241 | 7.915134 |
| Cloned warmup,s | 50.001644 | 5.306861 |
| 128 range ACKs,s | 2.703344 | 2.651409 |
| 128 kNN ACKs,s | 0.882908 | 0.867322 |
| 40 insertion ACKs,s | 47.536585 | 2.782910 |
| 40 deletion ACKs,s | 0.015144 | 0.012187 |
| Two rebuilds,inclusive,s | 47.535927 | 2.782255 |
| Build inside two rebuilds,s | 46.037203 | 1.315127 |
| Active numeric refit,s | 0.699616 | 0.693370 |
| Active PAR plan refresh,s | 0.032069 | 0.028796 |
| Active kNN mirror repack,s | 0.025131 | 0.025096 |
| Trace CPU user,s | 50.899819 | 6.082299 |
| Trace CPU system,s | 0.246511 | 0.225676 |
| Sampled device peak,GiB | 20.453979 | 20.450073 |
| Host answer capacity,MiB | 0.790283 | 0.790283 |
| Per-process insertion p99,ms | 23769.207718 | 1395.033215 |
| Per-process deletion p99,ms | 2.858490 | 2.133662 |

Insertion/deletion p99 is a descriptive percentile of only40 operations per process, not a production-tail guarantee. Device peaks are sampled total used memory, not allocator-exact peaks. Setup+trace excludes parse/context/warmup/disk serialization; the raw receipts retain those boundaries.

## Mechanism and exactness

Nine paired qualification cases cover 37 build states and 115 layers per mode. All 1376 complete defined-state files per mode match bitwise, including keys,pids,sort order,occupied topology and refit bounds.
The original midpoint pivot and node_slot composite keys remain; each object has one writer and tile0/thread0 alone writes each splitting-node pivot metadata. The root grid changes1→1954 CTAs for N1M; no task array,allocation,copy or new primary fence is introduced.
All 112 original GPU functions/74,144 normalized instructions are identical. The only added function has 2,008 static instructions. This is static identity,not dynamic work or a coalescing/traffic counter.
Static resources: original42 versus tiled52 registers; both retain47528-byte stack frame and20-byte reported shared allocation; zero compiler spill stores/loads. The stack is not evidence of zero local traffic. No occupancy or sector/byte-saving claim is made.
Four ordinary access/sync sanitizer processes report zero errors/hazards. Every primary process has256 complete query outputs/54614 ID-field pairs with actual parent exhaustive-quality bindings; warmup and operation states also match. Hardened replay requires complete file families and rejects changed keys,geometry,tail bytes and missing qualification evidence.

## Mainline and strongest caveats

Avoidable shallow serialization → explicit object-tile ownership → build_distance_tiles → identical work/state with larger independent grid → measured internal complete-workflow result. This is not repeated-distance elimination and ordinary CTA partitioning alone is not novel.
Trace-scoped CPU user time is measured separately. Its change is consistent with the earlier diagnostic waiting attribution,but this campaign has no new CPU polling or arithmetic profiler evidence; CPU/GPU overlap is not additive.
The old1.684797× A→PAR result is preserved separately,not multiplied into this campaign. Native GPU Flat and CPU Flat counterevidence and unresolved MVPT/GPU_TREE qualification remain in the baseline tables. No new external dynamic or formal CPU/GPU ranking is established.
Inherited96B/seven managed context-symbol full-leak issue remains unresolved. No leak-clean,production/default,1B/100k or long-matrix admission. Next: keep this as the strengthened internal comparator and separately close qualified external static/dynamic and sustained-workflow gates.
