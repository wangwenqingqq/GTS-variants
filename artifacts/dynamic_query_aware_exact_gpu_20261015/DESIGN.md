# Pre-execution design and ownership review

This is integration of known mechanisms, not a kernel-tuning campaign. Search
shape is N≤1M/D960/B1/finite FP32 |value|≤16 on SM120. The existing outward
screen and original-coordinate ordered-FP64 replay remain the authority. A
mean is a priority heuristic; its precision is not a relaxation of exact output.

| Object | Owner / live interval | Ready / overwrite edge |
|---|---|---|
| Raw FP32 rows | One service device allocation | Serial mutation ACK before any query |
| Logical forward/reverse maps | Host service | Changed owners checked per mutation; independent complete final replay |
| Query states | Existing two 16B/row stable-CUB buffers | Stage count D2H + stream wait before next stage |
| PDX order/inverse | Existing two 30-int device arrays | Host priority and uploads before same-stream scans |
| Deleted-vector scratch | INC only, max512×960 floats | Gather before any swap; reduce before next batch overwrite |
| Gather row IDs | INC only,512 ints | Current pre-batch positions uploaded; one thread per copied coordinate |
| Sum / mean | INC only,960 FP64 sums +960 FP32 means | One thread per dimension; same-stream update then Host D2H before ACK |

Query CTAs retain 8 warps/CTA, one warp/row, uniform ragged-warp returns and
32-lane shuffles. S0 only changes the template/schedule to full0→960; S1 and
both S2 policies must match the preceding selected query SASS. The gather has
256-thread CTAs over contiguous coordinate slots, no atomics or shared memory.
The mean kernel uses four256-thread CTAs; each live thread keeps one FP64 sum
and walks the batch in row order. It may underutilize the device: no throughput
optimality is assumed. No cross-CTA barrier, async handoff, persistent kernel,
Tensor Core, Graph or second vector representation is introduced.

At query time the critical path remains data reads, safe screening/replay,
stable compaction/count waits, and complete output. For a batch of b rows,
incremental maintenance adds the deleted-row gather, O(960b) reads/additions,
960 sum/mean writes, and3,840B mean delivery. It does not scan N rows. The
deleted scratch cannot be released or overwritten until its reduction has
completed. Host vectors used for asynchronous copies outlive the same-stream
wait. Every map and buffer release is inside the charged release segment.

Expected effects are hypotheses: unchanged query instructions for each fixed
ordering, changed order/survivors under mean drift, extra update traffic/API
work for INC, and possibly update-dominated total service. Data writes, sum
work, synchronization, register/stack/local/shared use, and whole ACKs must be
measured separately. Static zero-spill/no-TC audit is not a latency result.

Numerical checks separate complete members, internal full-hit ordered-FP64 bits,
the inherited FP32-rounded native squared observer, and sqrt distance tolerance.
INC starts from the original FP32 mean anchor; its independently reconstructed
mean check allows2e-7 absolute disagreement from reduction order, not from score
semantics. Synthetic fixtures additionally compare incremental sum/count means
exactly, including empty deletion and re-insertion, before performance runs.

Validation ladder: CPU schedule/replay negative tests → fresh compile/SASS →
100-iteration/two-independent-stream pointer churn and boundary cases → all
three sanitizers for every mode → bounded4096 and complete1M workloads →
six matched process rounds → independent all-query and maintenance NCU. Missing
or failed gates stop the matrix, preserve evidence, and prohibit promotion.
