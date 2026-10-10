# Original GTS pivot reuse: qualification checkpoint

**Checkpoint A: final guarded GPU1 diagnostics and qualification are complete;
the frozen six-round confirmation is collecting. No net latency improvement or
production promotion is claimed here.** All timings are new measurements on
the user-authorized idle physical GPU1/NUMA0; the GPU0 service was untouched.

## Redundancy -> mechanism -> module -> effect -> complete cost

1. **Redundancy.** Original GTS already shares one pivot distance among sibling
   nodes and uses encountered pivot distances to tighten the kNN bound. G2 is
   therefore deleted, not implemented by weakening the baseline; G3 equals G1.
   The remaining gap is recomputation when a pivot object reaches leaf checking,
   plus one cross-level object alias in this fixed index.
2. **Mechanism.** G1 caches the full original double distance by query/object
   identity. Distinct IDs remain distinct even when their vectors match. It
   retains the original arithmetic, disk filtering, node priority and bounds.
3. **Module.** An immutable 4,000,000-byte object-to-pivot map is index setup.
   Every B1 query allocates a 44,440-byte valid array and 88,880-byte distance
   array, clears validity, performs cache lookup/read/write, and frees both.
   These query costs are included in the frozen host-ready pass timer.
4. **Measured effect (fixed32 only).** G0 executes 28,442,203,200 distance
   dimensions; G1 executes 28,138,250,880: **303,952,320 fewer (1.068666579%)**.
   G1 avoids 316,585 leaf recomputations and 32 cross-level pivot recomputations.
   All 316,617 cached-hit arithmetic bridges are bit-identical. Both modes test
   3,365,870 nodes, pass 3,262,461 nodes, and visit 2,929,074 leaf nodes and
   29,290,740 valid leaf objects. Their full output bins are bit-identical.
   No earlier candidate-bound benefit or visit reduction was introduced.
5. **Complete cost.** Pending six independent fresh processes per retained mode,
   each returning all 256-query results. The declared paired geometric ratio,
   bootstrap interval, process wins, order splits and raw rounds will be added
   in checkpoint B. A 1.069% arithmetic reduction is not a latency win.

## Added costs and attribution boundaries

- Fixed32 G1 performs 29,627,327 logical map lookups, reads 2,532,936 logical
  cache payload bytes and writes 4,038,660 payload/tag bytes. These are
  **source-level counts, not measured DRAM/L2 traffic**. Validity reads, memset,
  allocation metadata and other memory-system traffic are not included.
- Both counting variants maintain diagnostic tags so unique objects can be
  counted. G0_count lookup/write counters are not overhead in uninstrumented G0.
  Count timing and intentionally duplicated bridge arithmetic are excluded from
  every formal ratio.
- Static mapping took 4.4359 ms in this diagnostic process; setup is reported
  separately, not silently amortized into the query ratio. Final process-specific
  setup values will be retained rather than replacing them with this example.
- Static resource evidence: getDisPQ registers are G0=50/G1=52; leaf kernel
  registers are 48/48. Both retain the inherited 47,528-byte stack declaration
  and zero static SHARED/LOCAL allocation. This is not a no-runtime-local-traffic
  or occupancy certificate. No additional Graph/layout/precision change exists.

## Correctness, failures and scope

`VALIDATION.json` retains the final binary identities, receipt/log hashes,
independent exhaustive quality fields, six clean sanitizer summaries, full-bin
equality checks and the pre-formal implementation/collection faults. Initial
unguarded diagnostics and partial failed orchestration remain raw evidence;
they are not the final qualification or the formal denominator.

Small complete-search tests use N4097 at D96/960, 33 queries including self and
nine vector-equal but identity-distinct objects (an exact K8 boundary tie).
The isolated cache test covers 512 bitwise primitive bridges and 128 cold resets
with alternating queries and fresh allocations. **N<K/root-leaf full search is
not certified:** the existing full-output adapter explicitly admits only
N>=4097, and its four-object cache-component test is not a substitute. Deliberate
last-visited-branch and long-unfilled-candidate full-tree fixtures also remain
uncovered. Thus the broad requested boundary qualification is partial, even
though the admitted fixed-GIST qualification passes. Do not promote this into a
general-purpose original-GTS replacement without those additional gates.

The 256 confirmation IDs are generated only after final code/parameters freeze.
They exclude 15,984 known IDs inventoried from 396 historical query files; generic
unnamed/private earlier query files may be missing. This is not a universally
unseen-query claim. See `QUERY_SCOPE.json` and the retained query-ID files.

There is no dynamic-update, concurrent-batch, arbitrary alias-edited-index,
external-comparator, novelty or distribution-generalization claim. The static
1.0978% no-pruning arithmetic opportunity is not a timing upper bound.
