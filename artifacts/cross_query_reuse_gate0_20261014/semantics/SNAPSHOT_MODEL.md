# Dispatch-epoch visibility: design only

No update benchmark, GPU implementation or original workflow-equivalence test
was run. This protocol is a construction, not a claim of cheap maintenance.

## State machine

1. An update prepares an unpublished version with one consistent vector/ID/live
   mapping. Insert and delete must change all relevant ownership metadata.
2. A short commit operation publishes epoch E+1, then ACKs the update. A batch
   dispatch atomically pins the newest published epoch E and its immutable
   mapping. The shared commit/dispatch order defines visibility.
3. Every query in that dispatched batch reads E. All updates ACKed before its
   dispatch are visible. Updates published later are absent from that batch and
   visible to the next dispatch that pins their epoch.
4. Writers must not mutate pinned rows in place. Copy-on-write blocks/versioned
   directories are one possible realization. Old versions are reclaimed only
   after every batch reference is released. Query completion includes complete
   output materialization and only then releases the snapshot.

Long scan execution need not hold the writer commit lock. But block-copy,
version-directory, memory growth, snapshot pin, release and reclamation costs
are all UNKNOWN. This note proves neither an implementation without rebuild
nor a latency bound on updates. A read pin taken at enqueue is not equivalent
to a pin at dispatch when an update commits during the collection window.

## Serial workflow is not the same as request linearizability

A query enqueued before an update may see that update if the update ACKs before
dispatch. This is consistent with the requested dispatch-epoch rule, but may
change a reference trace whose Q/I/D events are strictly ordered at arrival.
For a fixed serial workflow, never merge Qs across an I/D barrier: split the
batch or establish an explicitly authorized reference ordering. The model has
no updates and makes no equivalence claim; such barriers could reduce reuse.

## Mixed range and kNN

For each query q and row x in E, the same exhaustive distance phase can feed
either inclusive range membership or top-k ordering. They share database x,
not query-specific arithmetic. Each query needs independent accumulation,
threshold/top-k state, tie order, output ownership and complete output buffers.
The authoritative ordered-FP64 expression must remain unchanged; replacing it
with reassociated GEMM is not automatically the same exact score.

No k, radius distribution, hit cardinality, compaction or selection cost was
evaluated. The 50/50 tags only test grouping ownership in the synthetic model.
The supplied progressive source reference is measured on range queries only;
its cost for this mixed workload remains UNKNOWN.
