# Gate7 decision

**Final: CONDITIONAL_PACKING. Stop without a GPU registration.**
Base:1f4486c3685be80076efcf6ae47483f59912bd7e. Prior-art admission is
DISTINCT_ENOUGH_TO_TEST for one diagnostic, not a novelty verdict.

## Q1. How much locality loss is repaired?

At the same nominal 16x32B source budget, P1 reduces survivors from
118,012.12500 to91,846.90625 per query:26,165.21875 fewer, or 22.171636%.
Selected-sector C1-demand purity increases 3.785156->4.259766/8;
held-out C1 top128 recovery is53.247070%. Packing repairs some locality loss,
not enough to meet the declared margin. The affinity primitive itself is old.

## Q2. Does P1 remove at least30% versus S1?

No. Total P1 = 2,939,101 versus S1 = 3,776,388; P1/S1=0.778283640346278.
The exact gate10*P1<=7*S1 fails. The exact linearly interpolated p90 is
12740595/10486024=1.2150072324839234; <=4/5 also fails.
Because the mean ratio lies in(0.70,0.85], the frozen label is CONDITIONAL,
not an invented GO or a relabeled NO_GO. No threshold was loosened.

## Q3. Is the strong20% source-byte margin reached?

No. Conditional modeled total=26,165,328,128 B for 32 queries;
mean=817,666,504 B/query. Strong reference=1,014,828,776 B/query;
ratio=0.8057186821434792, reduction 19.428132%. Exact required mean is
811,863,020.8 B/query. The candidate exceeds it by 5,803,483.2 B/query.
This source-only model is9.624580% below historical S1's 904,744,352 B/query.
Mapping, retaining selected coordinates, original-order reconstruction and
spills are unpriced unknowns; the model is not measured traffic or latency.

## Q4. Is it stable on independent evaluation queries?

The training pool is disjoint and the permutation was frozen before evaluation
vectors/outcomes were read. Demand coverage transfers partially: training mean
0.5712509155 versus evaluation0.5324707031. However, 21 queries improve, 3 tie,
8 regress; the p90 survivor ratio 1.215007 fails the robustness target.
Do not infer absence of generalization or claim robust dominance. The scope is
this fixed 32-query pool, not 10k-query, dynamic or multi-dataset validation.

## Q5. Final action

Retain code, permutation, raw-proof hashes, all queries and negative evidence.
Do not run another greedy, change the group/budget, implement fallback, start
CUDA/profiling or modify the paper. Reopen only with a separately authorized,
non-subsumed mechanism/contract; this result does not admit tuning on evaluation.
Implementation is complete and correct for the diagnostic. Mechanism admission
is conditional; the generic packing novelty thesis is not established. Existing
progressive keeper and Gate6 decision remain unchanged.
