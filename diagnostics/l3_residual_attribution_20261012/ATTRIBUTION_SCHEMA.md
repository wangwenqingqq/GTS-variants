# Attribution schema

## Identity and hierarchy

An occurrence ID is the immutable object identity in the frozen `base.i32`.
Selected split pivots are recovered from the first child's `TN.pid`, mapped
through that snapshot's base array. A parent's own `TN.pid` is an inherited
pivot and is **not** its selected split pivot. Decision L3 parents contain 1000
objects, ten L4 children and 100 final leaves of ten objects each.

Every complete node membership, permutation, leaf cover, child cover and selected
pivot ownership is checked by the reused tree decoder. Exact leaf identity is
SHA-256 of sorted immutable occurrence IDs, retaining the full leaf membership
including non-common objects. Common-live objects are the intersection of PRE
and POST base occurrences and live sets: 999,990 per rebuild. No Jaccard gate.

## Correspondence and grouping

Match PRE and POST L3 partitions by a **unique mutual maximum common-live
occurrence overlap**. A storage slot labels a payload; it does not establish
correspondence. Ambiguity, an unmatched parent or missing evidence would be
UNKNOWN, never forced into SAME or CHANGED. Actual data has 1000 matches and no
UNKNOWN parents in each rebuild.

For each matched POST parent, compare the actual selected pivot occurrence to
that of its matched PRE parent. Each common-live object belongs to its **POST
L3** group, including imported objects. Each POST leaf belongs to its actual
POST L3 ancestor. The two group counts plus UNKNOWN exactly partition total
objects, object churn, leaves and leaf churn. A PRE-cohort object regrouping is
reported as a migration-sensitivity check, not a replacement estimator.

Mechanics use **only common occurrences retained in the corresponding parent**.
Imports, exports and imported object churn are explicit. An imported object
cannot enter that parent's PRE/POST rank or boundary comparison. Objects lacking
correspondence must not silently acquire a zero crossing count.

## L4 survival

Inventory survival counts each PRE L4 selected pivot whose occurrence appears
among the ten selected POST L4 pivots under the matched L3 parent. The denominator
is ten PRE pivots per matched L3 parent. This is hierarchy-local inventory
survival, not global survival and not correspondence equality.

Separately match the ten children using retained common objects and count exact
pivot equality in those corresponding children. Report the number of matched
child pairs; do not turn missing pairs into same-pivot children. The supplementary
SAME-L3/L4 table groups actual POST L4 children by this correspondence, and keeps
UNKNOWN explicit. It is a descriptive extension after the primary measurement,
not an extra admission gate or intervention.

## Ranks, keys and ties

Use actual captured L3 sorted orders, not final leaf order, for ranks. Subtract
each parent's own starting position, then compute absolute PRE/POST differences.
Normalize by the PRE parent size (1000 here). Aggregate occurrence-level
quantiles, not the median of per-parent medians. Input-order ranks are checked
separately. Common-only compressed ranks remove the effect of absent/imported
members before comparing the relative order of retained occurrences.

The native key is the captured encoded double value combining distance and a
partition offset. Exact bit equality across builds is only compared for parents
with the same actual offset/slot; all SAME parents satisfy that in these runs.
No offset-stripped value is called an exact Euclidean distance.

Tie diagnostics use equality of **captured encoded keys** within retained-common
subgroups. An occurrence is non-tied here only if it has no other retained-common
tie partner in either build; it may have had a partner deleted or moved outside
this retained set. Persistent subgroups share both PRE and POST key equality.
Report reordered subgroup count and the number of objects whose **ordinal
position inside that subgroup** changes. This is not all objects participating
in pairwise inversions. The ABC-to-CBA regression explicitly distinguishes them.
No stable secondary key was supplied to native sort and none is invented here.

## Boundaries and gates

Use nine actual split positions, k*100 for k=1..9, under the matched L3 parent.
For each retained occurrence compare its sides of each PRE/POST boundary.
Report counts per boundary, unique objects crossing one or more boundaries, and
objects crossing multiple. The sum of boundary crossings can exceed the unique
object count. Exact child-segment change is verified equal to crossing >=1.

The PIVOT_DOMINANT gate uses integer comparisons (no rounded percentages):
changed-pivot residual shares >=90% for both objects and leaves, SAME within-group
leaf churn <=10%, and complete group evidence, separately for both rebuilds.
All parent details are retained privately; their exact hashes bind the public
aggregate. No threshold is relaxed because R1 is close to 90%.
