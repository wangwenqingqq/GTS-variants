# M3 — shared range/kNN progressive state

Hypothesis: the same row owner, raw FP32 store and partial-sum/ID state can reduce
exact k8 coordinate consumption by>=40%, without a separate GPU kNN kernel.
Range supplies a fixed inclusive radius; kNN supplies a valid upper bound on
the exact eighth neighbor. Strict partial>threshold can safely eliminate a row;
equality stays alive. Candidate selection and threshold construction are not free.

Expected benefit directly addresses Gate3's dominant kNN query component. Added
costs would be initial complete candidate distances, exact tie-safe top-k/threshold
maintenance, state selection/synchronizations and numerical replay. Those costs
are excluded from the ideal-byte estimate but explicitly prevent claiming a
latency or mixed-workflow win from it.

No independent kNN kernel, layout, stage change or query-mix change is admitted.
Both APIs already have a shared progressive execution precedent in matrix S04/S12.
Sharing raw storage/state and replacing the threshold is not by itself a new
non-incremental abstraction. This test evaluates headroom, not external superiority.
Reopen only with a genuinely different mechanism and a registered same-contract
external qualification/comparison.
