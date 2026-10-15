# Strict contract and nonalias lemma

A batch has B distinct live occurrence IDs,1<=B<=min(N,512),and no observer inside its Host-ready ACK. The native implementation validates all IDs before mutation. Duplicated coordinates are allowed;duplicated IDs in a batch,empty batches,nonlive IDs and oversize batches are rejected. Insert remains contiguous append with fresh IDs.

Primary compatibility includes the **entire allocated database vector array**,including retired/inactive rows,not just the live prefix. The exact native occurrence/position maps,mutation order,next-ID state and subsequent append behavior also remain unchanged. Thus observable equivalence follows without weakening the primary contract. Exceptions/CUDA failures terminate the process;no new transactional rollback claim is made.

## Why a native sequence can become independent final copies

Every nontrivial native copy has source `last` and destination `row<last`;the successive `last` values strictly decrease. A row that is overwritten before it becomes a later source no longer contains its original row:follow its provenance to an earlier,higher source instead. Such an original source cannot have been overwritten earlier(otherwise it would have different provenance),and cannot be overwritten later(future destinations are below the then-decreasing last).

Therefore original rows used by the composed final state are never in its written-destination set. Composing all writes,including writes into subsequently retired rows,yields:

- distinct final destinations;
- original sources in the old tail `[N-B,N)`;
- **source/destination sets disjoint**,even when two destinations read the same source;
- identical allocated-capacity bytes under arbitrary parallel execution of those final copies.

Only B tail provenance entries and at most B destination mappings are needed;no O(N) per-batch vector scan or query indirection is introduced. `plan.hpp` checks the certificate instead of assuming it. CPU model and C++ tests compare all allocated row labels after every batch;GPU qualification compares actual bytes and complete queries. The kernel uses integer loads/stores,so all FP32 bits are preserved,including NaNs in synthetic bit-pattern tests.

## Baseline and costs

WAVES preserves every native physical copy and partitions RAW/WAW/WAR conflicts into stream-ordered CUDA batch calls. It is a **safe ordinary batching baseline**,not a direct unsafe unordered copy batch. FINAL removes overwritten intermediate copies by materializing only the final provenance map. At B1 the native path remains;one final move uses native memcpy;more than one final move uses an8-byte/row metadata upload and one128-thread CTA per row. One final stream sync preserves ACK visibility. No vector staging,tombstones,lazy materialization or changed query layout is used.

All validation,mapping,plan construction,metadata upload,execution,counters and required wait are inside ACK. Scratch creation and release follow the inherited build/events/export/release segmentation and are separately accounted. Final state verification remains outside event time,identically labeled. The noalias proof does not apply across insertions,concurrent observers,arbitrary permutations or unsupported B>512.

For native descending-last copies,WAR is structurally impossible:every later destination is below every earlier source. WAVES validates decreasing sources and only needs prior writers for RAW/WAW ordering. Edge-count diagnostics are CPU-offline only,not charged to the ordinary GPU batching comparator.
