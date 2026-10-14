# Decision: SUBSUMED_PRIOR_ART

Scope:the broad core mechanism, not proof of an identical INT8 ordered-FP64 L2
implementation. The strongest direct source and its metric/numerical assumptions
are explicitly scoped in PRIOR_ART.md. No external performance or correctness
claim is adopted as our experiment result.

## Q1. How many non-hits are safely rejected?

**Unknown / NOT_RUN.** The prior-art stop precedes quantizer, residual-bound and
population execution. It is invalid to claim 90%/95% certification,0FN/FP, or an
empirical failure below those thresholds. All numerical fields are null.

## Q2. Is fallback concentrated near the threshold?

**Unknown / NOT_RUN.** No interval widths, margins or buckets were measured.
The mathematical interval can be ambiguous at the boundary; the local rational
witnesses show conservative ties and selective refinement logic only. They do
not validate the FP64 or stored-FP32 residual bound.

## Q3. What are complete modeled source bytes per query?

**Not measured.** The frozen design is 968,000,000+3840*F, where
F=|AMBIGUOUS union all final hits|. Membership-certified hits still need an exact
score; ambiguous hits are never double-counted. Query/control/ID/output costs
would be separate. No measured mean, DRAM, latency or end-to-end result exists.

The historical progressive source model is 1,014,828,776B/query. With F=0, the
new first pass could reduce that model by only 4.614451%; positive fallback
reduces the margin. This denominator warning does not alter the original GO
threshold, nor establish a performance ceiling for a future different GPU design.

## Q4. What persistent storage/update overhead is added?

**Theoretical payload arithmetic:**968 MB sidecar + 3.840 GB raw = 4.808 GB total;
ratio601/480=1.2520833333. Sidecar generation/maintenance adds 968B per vector;
raw + sidecar insert payload is 4808B. Same-row delete/swap and metadata ownership
must stay synchronized. No actual storage files or dynamic trace were produced,
and no O(1), cheap update, ACK latency or rebuild benefit is claimed.

## Q5. Does prior art cover the core precision-routing mechanism?

**Yes at the core-thesis level; final label SUBSUMED_PRIOR_ART.** Category 4
is decisive, not approximate-recall evidence. The requested metric, accumulator,
metadata layout and physical costs are not asserted identical to the precedent.
Those engineering differences alone do not establish a non-incremental mechanism.

Implementation status: NOT_IMPLEMENTED. Numerical mechanism effectiveness:
UNKNOWN. Thesis admission: stopped. Steps 3-9 and GPU Gate1 are NOT_RUN/NOT_ADMITTED.
Do not rescue the direction through dtype sweeps, GPU porting, packaging or small
speedups. A future reopening needs a clearly distinct mechanism and a newly
frozen same-contract comparison against both the closest prior art and the keeper.
Nothing in this verdict disproves the usefulness of certified low precision.
