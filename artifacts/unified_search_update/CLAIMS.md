# Claim boundary: redundancy -> mechanism -> module -> impact -> end-to-end

| ID | Redundancy / risk | Mechanism and module | Effect | End-to-end evidence / limit |
| --- | --- | --- | --- | --- |
| U1 | Separate kNN/range update owners can diverge | One original update loop; shared tombstones, insertion buffer and occupancy-10 rebuild | Both search kinds observe the same serialized live multiset | Full-output integer oracle, ties/empty/sparse/rollover and mixed10k; scoped functional integration only |
| U2 | AoS verification access and repeated scoring | Reused AoSoA32 ordered-FP64 B1 verification, eligible-seed cutoff and hierarchical lexicographic top-K | kNN evaluates live occurrences, preserves ties and duplicate ranks | BOUND versus FULL output identity; no fresh external timing or generalized speedup claim |
| U3 | Stale layout after compaction | Repack the shared native base inside the triggering rebuild before ACK | Next search uses the current epoch, not the old physical order | Exact refresh counts and full fields after each rebuild; mirror adds maintenance cost |
| U4 | Boundary omissions and malformed input | Strict retained host input, bitmap eligibility and `(-1,+inf)` normalization | Deleted seeds do not corrupt cutoff; empty/fewer-than-K answers are defined | Direct-binary malformed checks before GPU allocation and GPU boundary/sanitizer checks |
| U5 | Integration overhead may regress the admitted PAR path | Fresh legacy/unified alternating pairs (2/1 order split) with all mirror costs included | No timing cost is hidden by a separate executable or deferred maintenance | Frozen <=5% regression screen; measured result and decision in RESULTS.md |

Unification is routine engineering, not a defensible new thesis by itself.
Original GTS already exposes these operations; this artifact does not establish
that all GPU trees have the same redundancy or that every operator is optimized.
The earlier static external comparison remains separately qualified. No paper
manuscript or novelty claim is promoted here. Missing production/external gates
limit scope; they do not erase measured functional evidence.

## Target-size qualification is a separate, not-yet-promoted scope

The D128 integer results above are not inherited as proof for GIST N1M/D960.
The separate [target contract](../unified_target_workflow/TARGET_CONTRACT.yaml)
and [correctness ledger](../unified_target_workflow/TARGET_CORRECTNESS.json)
record the new capacity/numeric/lifecycle qualification. Its mode A is staged
GTS with common repairs, not untouched original GTS. Runtime capacity, ordered
FP64 membership and actual-member bounds do not establish a new research
contribution. Target end-to-end speedups, external Flat comparison, the
18-process short experiment and conditional longer default selection remain
unmeasured unless the target ledger explicitly admits them. No historical
speedup is multiplied into this target condition.
