# Original leaf-kernel audit

Baseline: original GTS at `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`, with
the unchanged complete-ID adapter from `e90290af`. Audit before implementation.

`dataProcessKnn` has no shared storage, barriers, reductions, shuffle/vote, or
block-wide collective. Each object distance is thread-local. Its only geometry
dependencies are `bid=blockIdx.x`, `tid=threadIdx.x`, the slot loop's stride
`THREAD_NUM=512`, and the launch. Changing the global THREAD_NUM would also alter
other kernels and is forbidden. G1 changes this leaf launch alone to32 threads.

Let `C=size_list[cur_level]/(3*MAX_SIZE+3)`, `P=offset_p`, and `b` be the original
compacted leaf task. Input node/query indices are `p_list_k[P+C+b]` and
`p_list_k[P+2*C+b]`. The original slot is `s=b*MAX_SIZE+did`. Outputs are slot ID
at `P+3*C+s`, distance at `P+(3+MAX_SIZE)*C+s`, and sort code at
`P+(3+2*MAX_SIZE)*C+s`. Distinct `(b,did)` pairs own disjoint locations. The
following Thrust sort consumes **all20 slots per leaf**, not only valid objects.
Padding must remain initialized to the original sentinel, slot ID and sort code.

`disk`, nodes, ID permutation, qid_list and input vectors are read-only in this
kernel. It neither changes a bound nor performs global top-k. The preceding
merge is device-synchronized; the following sort starts after the existing
device synchronization. No new stream or synchronization dependency is needed.

MAX_SIZE is20, but the pinned GIST index has100,000 ten-object leaves. The
unchanged N4097 boundary indexes have sizes4,5,11,13. A literal ten-slot-only
implementation would lose real objects AND leave padding stale. G2 therefore
assigns ten lanes to each leaf and uses slot stride10: each lane visits its
original slot and slot+10. For GIST the latter is padding; for boundary leaves
it can contain a real object. This is one fixed kernel, not a new candidate or
shape-tuned fast path. All original20 slots and all original distances survive.

G2 maps `b=3*blockIdx.x+threadIdx.x/10`, `tid=threadIdx.x%10`, rejects lanes30/31
and `b>=lnum` before reading task arrays, and launches `ceil(lnum/3)` CTAs of32
threads. The only new argument is the original `lnum`, already known on host.
The distance body and three result-write formulas remain byte-identical.
No packing buffer, index rewrite, new predicate, cache, layout or arithmetic
change is allowed. All upper tree stages and all sort/materialization stages
remain unchanged. Gate A passes: no block-wide dependency prevents this mapping.
