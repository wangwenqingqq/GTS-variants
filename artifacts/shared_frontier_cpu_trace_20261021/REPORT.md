# Shared-frontier CPU trace report

**Decision: NO_GO, 0/12 primary cells pass the frozen 10x gate.** The measured candidate increases both metric work and ownership-aware frontier on Words/DNA. Stop this frozen implementation without CUDA. This is a scoped cheap falsification, not a universal bound on all shared traversal.

## Population, semantics and validity

| Dataset | Source N | Trace initial / delete / append | Query batch and seeds | Radii | Role |
|---|---:|---|---|---|---|
| Words | 611,756 | 65,536 / 32 / 32 | 256; 2026102101, 2026102102 | 1, 2, 3 | Primary, byte Levenshtein |
| DNA_GRCh38_chr1_108 | 1,000,000 | 65,536 / 32 / 32 | 256; same seeds | 2, 4, 8 | Primary, Levenshtein |
| TLoc | 10,000,000 | 65,536 / 32 / 32 | 256; same seeds | 0.01, 0.05 | 2D L2 pressure only |

DNA was provisioned from [UCSC GRCh38 chr1](https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr1.fa.gz): one million uniformly sampled nonoverlapping 108bp ACGT windows. It is not the original GTS DNA read dataset. Source, derivation and sampled-input hashes are retained. Original data/source headers were read-only; protected GIST held-out inputs were not accessed. Full source sizes are not measured sizes.

All nine CPU processes completed without target failure, retry or replacement. Ninety complete method-output streams matched all-pair references, including deletion/append states. Qualification checked 581 edit-distance pairs against independent dynamic programming, plus complete string/L2 fixtures. The full reference shares the metric primitive, not a fully independent arithmetic oracle. Post-run audit rechecked seals, actual deterministic query/delete files, query self-hits and every output stream. The runner lacks launch-time qid/delete hashes: current agreement cannot retroactively prove launch-time immutability.

Hardware: Intel Xeon Platinum 8575C, Python 3.12.3, g++ 13.3.0, one CPU arithmetic thread, nice 10, serial targets. No GPU settings or foreign processes were changed. CPU durations are resource observations, not paired speedup measurements.

## Primary gate, both seeds

Ratios are shared-candidate / cached-GTS costs; above 1 means regression. Distance gates also compare Quickjoin, charging partition work. Frontier requires both allocated bytes (including query-tree ownership) and logical query-node mass, not merely fewer packed records.

| Dataset | Radius | Metric call inflation, min–max over seeds | Frontier byte inflation | Logical frontier inflation, min–max | 10x cells passed |
|---|---:|---:|---:|---:|---:|
| Words | 1 | 4.764–4.846x | 7.115x | 5.896–5.921x | 0/2 |
| Words | 2 | 2.213–2.238x | 1.779x | 2.245–2.250x | 0/2 |
| Words | 3 | 1.672–1.685x | 1.779x | 1.534–1.538x | 0/2 |
| DNA_GRCh38_chr1_108 | 2 | 13.326–13.622x | 14.230x | 18.173–18.483x | 0/2 |
| DNA_GRCh38_chr1_108 | 4 | 3.645–3.687x | 3.557x | 3.826–3.846x | 0/2 |
| DNA_GRCh38_chr1_108 | 8 | 1.543–1.546x | 2.668x | 1.296–1.300x | 0/2 |

## Representative exact counters: seed 2026102101

Rows below use the same frozen query identities. Both seeds and updates are in CSVs/SUMMARY; no sample is selected away. Visits include tested/rejected work. Quickjoin tasks are rectangles/windows, not semantically identical to tree-node pairs.

| Dataset | Radius | CPU method | Node-pair/task visits | Distance calls | Candidate pairs | Max records | Frontier allocated bytes | Query-tree bytes | Output |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| DNA_GRCh38_chr1_108 | 2.0 | GTS_LITERAL_CPU | 351336 | 1247792 | 896712 | 166382 | 2359296 | 0 | 257 |
| DNA_GRCh38_chr1_108 | 2.0 | GTS_PARENT_CACHE_CPU | 351336 | 931820 | 896712 | 166382 | 2359296 | 0 | 257 |
| DNA_GRCh38_chr1_108 | 2.0 | SHARED_ANNULUS_CPU | 5087079 | 12693219 | 7641092 | 2426667 | 33554432 | 17408 | 257 |
| DNA_GRCh38_chr1_108 | 2.0 | QUICKJOIN_FAMILY_CPU | 7383 | 3460715 | 676314 | 2014 | 3052952 | 0 | 257 |
| DNA_GRCh38_chr1_108 | 4.0 | GTS_LITERAL_CPU | 1069976 | 5403968 | 4334248 | 757652 | 9437184 | 0 | 259 |
| DNA_GRCh38_chr1_108 | 4.0 | GTS_PARENT_CACHE_CPU | 1069976 | 4441220 | 4334248 | 757652 | 9437184 | 0 | 259 |
| DNA_GRCh38_chr1_108 | 4.0 | SHARED_ANNULUS_CPU | 5087097 | 16372763 | 11320618 | 2994513 | 33554432 | 17408 | 259 |
| DNA_GRCh38_chr1_108 | 4.0 | QUICKJOIN_FAMILY_CPU | 32158 | 12106396 | 3358581 | 9865 | 12484788 | 0 | 259 |
| DNA_GRCh38_chr1_108 | 8.0 | GTS_LITERAL_CPU | 2372446 | 15320128 | 12947938 | 2187308 | 18874368 | 0 | 270 |
| DNA_GRCh38_chr1_108 | 8.0 | GTS_PARENT_CACHE_CPU | 2372446 | 13185157 | 12947938 | 2187308 | 18874368 | 0 | 270 |
| DNA_GRCh38_chr1_108 | 8.0 | SHARED_ANNULUS_CPU | 5087111 | 20388813 | 15336654 | 3614350 | 50331648 | 17408 | 270 |
| DNA_GRCh38_chr1_108 | 8.0 | QUICKJOIN_FAMILY_CPU | 113454 | 40128299 | 12234124 | 31023 | 35882020 | 0 | 270 |
| TLoc | 0.01 | GTS_LITERAL_CPU | 10816 | 12944 | 2384 | 630 | 8192 | 0 | 274 |
| TLoc | 0.01 | GTS_PARENT_CACHE_CPU | 10816 | 3440 | 2384 | 630 | 8192 | 0 | 274 |
| TLoc | 0.01 | SHARED_ANNULUS_CPU | 674017 | 2085705 | 1430485 | 255604 | 3145728 | 17408 | 274 |
| TLoc | 0.01 | QUICKJOIN_FAMILY_CPU | 627 | 750804 | 43919 | 133 | 527892 | 0 | 274 |
| TLoc | 0.01 | GRID_2D_CPU | 2304 | 291 | 291 | 1 | 8 | 0 | 274 |
| TLoc | 0.01 | SPATIAL_DUAL_AABB_CPU | 15503 | 949760 | 949760 | 7880 | 65536 | 2560 | 274 |
| TLoc | 0.05 | GTS_LITERAL_CPU | 12106 | 16834 | 4984 | 1127 | 12288 | 0 | 562 |
| TLoc | 0.05 | GTS_PARENT_CACHE_CPU | 12106 | 6169 | 4984 | 1127 | 12288 | 0 | 562 |
| TLoc | 0.05 | SHARED_ANNULUS_CPU | 678125 | 2099270 | 1439951 | 257989 | 3145728 | 17408 | 562 |
| TLoc | 0.05 | QUICKJOIN_FAMILY_CPU | 675 | 752626 | 45741 | 143 | 529476 | 0 | 562 |
| TLoc | 0.05 | GRID_2D_CPU | 2304 | 1124 | 1124 | 1 | 8 | 0 | 562 |
| TLoc | 0.05 | SPATIAL_DUAL_AABB_CPU | 15657 | 968448 | 968448 | 7996 | 65536 | 2560 | 562 |
| Words | 1.0 | GTS_LITERAL_CPU | 744396 | 3597856 | 2853716 | 495858 | 4718592 | 0 | 304 |
| Words | 1.0 | GTS_PARENT_CACHE_CPU | 744396 | 2928130 | 2853716 | 495858 | 4718592 | 0 | 304 |
| Words | 1.0 | SHARED_ANNULUS_CPU | 5085131 | 14189572 | 9139393 | 2627108 | 33554432 | 17408 | 304 |
| Words | 1.0 | QUICKJOIN_FAMILY_CPU | 19191 | 7505119 | 1844138 | 5020 | 6774376 | 0 | 304 |
| Words | 2.0 | GTS_LITERAL_CPU | 1512836 | 9007790 | 7495210 | 1271558 | 18874368 | 0 | 1153 |
| Words | 2.0 | GTS_PARENT_CACHE_CPU | 1512836 | 7646468 | 7495210 | 1271558 | 18874368 | 0 | 1153 |
| Words | 2.0 | SHARED_ANNULUS_CPU | 5086567 | 17109172 | 12057557 | 3080280 | 33554432 | 17408 | 1153 |
| Words | 2.0 | QUICKJOIN_FAMILY_CPU | 61963 | 21426484 | 6262847 | 13971 | 16544652 | 0 | 1153 |
| Words | 3.0 | GTS_LITERAL_CPU | 2020716 | 12973127 | 10952667 | 1844943 | 18874368 | 0 | 12838 |
| Words | 3.0 | GTS_PARENT_CACHE_CPU | 2020716 | 11154713 | 10952667 | 1844943 | 18874368 | 0 | 12838 |
| Words | 3.0 | SHARED_ANNULUS_CPU | 5086989 | 18794888 | 13742851 | 3345826 | 33554432 | 17408 | 12838 |
| Words | 3.0 | QUICKJOIN_FAMILY_CPU | 99286 | 31967170 | 10103393 | 22633 | 24654516 | 0 | 12838 |

## Construction and bounded updates

Persistent DB construction is separate from query-plan+search metric calls. All initial 65,536-object GTS trees have 11,111 nodes, 273,254 metric calls and 1,363,088 payload bytes on this compiler. The candidate query tree adds 2,048 calls and 17,408 resident bytes per primary execution. Quickjoin has no persistent tree but charges every recursive partition call; grid/spatial construction is separately reported. Payload accounting is not allocator/RSS usage.

| Dataset | Initial build seconds, update S0 | Delete-32 rebuild calls | Delete mutation+release+rebuild seconds | Append-32 rebuild calls | Append mutation+release+rebuild seconds |
|---|---:|---:|---:|---:|---:|
| Words | 0.041398 | 273126 | 0.036031 | 273254 | 0.034878 |
| DNA_GRCh38_chr1_108 | 0.251371 | 273126 | 0.219837 | 273254 | 0.219533 |
| TLoc | 0.014797 | 273126 | 0.014350 | 273254 | 0.013973 |

Timer starts at active-ID mutation and ends after old-index release and replacement-tree publication. Input loading, construction of the deletion lookup set, query/reference validation, final export and concurrency are excluded. These are single CPU full-rebuild observations, not native GPU update ACKs, fine-grained updates or a 100k-event workflow. Incoming objects are 32 pre-reserved sampled IDs, not an application update trace.

## Interpretation and scope

1. **Observed:** eliminating repeated sibling-pivot evaluations is an old/simple reuse, not new query sharing. Cached-GTS keeps identical tree, pruning, candidates and frontier to literal GTS while computing parent distance once. It is the strongest metric-call control in every primary cell here.
2. **Observed:** the candidate pays more bound work and verifies more candidates. At DNA radius 2, seed1 cached-GTS uses 931,820 calls versus 12,693,219 shared calls, despite only 257 output triples. This implementation provides no 10x opportunity warranting CUDA.
3. **Inferred diagnosis:** query covering radii loosen source-annulus rejection while cardinality-driven query splits occur late. Extra query/source node pairs and verifications erase savings from one center distance serving multiple queries. No bound-slack instrumentation or alternative-split ablation was run; this is mechanism-consistent attribution, not isolated causal proof.
4. **Competition pressure:** TLoc grid verifies only 291/1,124 point pairs at seed1 radii 0.01/0.05, versus 2,085,705/2,099,270 candidate metric calls. Spatial AABB also loses to grid here. This does not measure native JZ Morton/plane traversal or GPU Gowanlock. Such coordinate filtering is unavailable for arbitrary edit metrics without a separately proved embedding.
5. **Novelty:** [Quickjoin](https://www.cs.umd.edu/~hjs/pubs/jacoxtods08.pdf) already establishes metric partition joins; [JZ](https://arxiv.org/abs/2604.05885) provides collaborative dual-tree GPU traversal. Classical shared frontiers alone are not a distinct index contribution. No native eD-index was run; generic AABB is not faithful JZ reproduction.

Reject the tested candidate under this frozen CPU subset contract. Native external executables, other partition/split mechanisms, independent application DNA queries, full populations and GPU end-to-end effects remain unmeasured. Missing evidence is not failure of those other designs. Do not rescue the result by dropping query-tree costs, using DFS/packed records as a memory denominator, comparing only repeated literal sibling work, tuning observed queries or relaxing 10x.

## Evidence map

- CONTRACT/SOURCE_FREEZE/PREPOP_REVISION: frozen choices and pre-population revision.
- results/*/COUNTERS.csv and BUILDS.csv: every counter and construction/update component.
- results/*/PROCESS.*: nine exits, raw textual logs and full-output proofs.
- evidence/POSTRUN_AUDIT.json, RUN_SEAL.json, RAW_MEMBERS.json: read-only audit and raw custody.
- check.py --test: data-free integrity/decision replay with mutation rejection; no target starts.
- REPRODUCE.md: fresh replay, custody boundaries and retained acquisition/transfer incidents.
- CLAIM_EVIDENCE.md: implementation/mechanism/thesis decisions and reopen boundary.
