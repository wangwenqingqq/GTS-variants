# What a final assignment means

Rows are opaque entry-state symbols. For each native command `X[dst]=X[src]`,
the generic planner applies `origin[dst]=origin.get(src,src)`. Induction over
the command sequence shows that every tracked destination names exactly the
entry-state row containing its final bytes. Keeping its last nonidentity
assignment preserves the entire allocated array,not merely the live prefix.

Tail-Provenance represents the same map more specifically. All native sources
are distinct,strictly descending rows in `[N-B,N)`. A destination outside this
tail cannot become a later source,so its current final origin can be recorded
directly. Destinations within the tail require a mutable origin array. At the
end,changed tail entries must also be emitted,even when those rows have retired.
These are two representations of the same provenance transformation,not two
different final assignment sets.

In-place parallel execution needs an additional condition. An original row
symbol used by a final assignment must have been read from its original row
before it could propagate elsewhere. That row cannot have been overwritten
before that read:strict downward copies cannot restore its original symbol.
After that read,all remaining sources and destinations are lower,so the row
cannot be overwritten later either. Thus required original sources remain
unchanged and are disjoint from changed final destinations. Both implementations
also check this certificate at runtime before launching parallel copies.

This is not an unrestricted data-movement lower bound. Equal vector bytes,
compression,indirection,another storage contract,or a different primitive can
change the work. Counts here are nonidentity provenance row assignments for
arbitrary entry contents. The arbitrary-copy generic CPU test uses an entry
snapshot for its semantic oracle;the GPU executor only admits certified,
nonalias plans from the declared swap-delete workload.

Every delete batch validates unique live occurrence IDs before mutation.
Reinsertion creates a fresh monotonically increasing occurrence ID;it does not
revive an erased occurrence. Newly inserted occurrences can be deleted by later
batches. Within a delete ACK,the original native operation order is preserved
in logical maps and mutation witnesses even when intermediate vector writes are
eliminated. The subsequent native append and frozen query observe that state.

Qualification checks every changed allocated destination after each ACK and
all final allocated bytes. Arbitrary-bit tests inspect the entire allocation
immediately after delete,including duplicates,NaN payloads and retired rows.
Those bits are injected after a valid finite build solely to test copying;
NaNs are not admitted as exact-search inputs. Search self-tests separately
cover empty/boundary answers,two sequential stream slots,and pointer churn.

The common offline oracle and input buffers are harness resources,not backend
work. Their construction/destruction is excluded from the service denominator;
their memory is included in process RSS. Backend planning,metadata,ownership,
device work,waits,and Store/answer/operation-ledger release are included.
