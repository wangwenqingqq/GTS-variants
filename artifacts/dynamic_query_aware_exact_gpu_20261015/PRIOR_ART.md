# Gate0: known mechanisms, an unmeasured dynamic failure question

**No novelty is claimed for this campaign.** PDX-BOND query-aware ordering,
ordinary sum/count maintenance, dense append/swap-delete storage, and safe
partial-distance rejection are not new mechanisms. The current question is
empirical benefit retention and cost, not another ordering algorithm.

The [published PDX source](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/python/pdxearch/index_base.py#L155-L205)
constructs the global mean with its static index. The
[PDX paper](https://ir.cwi.nl/pub/35044/35044.pdf) and
[BOND paper](https://ir.cwi.nl/pub/10425/10425D.pdf) already establish related
layout/partial-distance ordering. The approved fixed-zone and range-predicate
adaptations remain those of the preceding checkpoint; this is not a literal
official GPU implementation.

**Cheap kill test:** an arbitrary stale ordering does not invalidate exact
search, and a mean needs only sum/count deltas, not a full rebuild. For deletion
by ID, obtaining the deleted vector is not free: this adapter reads the actual
device row before swap-delete. Compare STALE against ordinary eager delta
maintenance before attributing any tax to an unavoidable rebuild-scale barrier.
The full ordered score is still the authority regardless of the statistics.

The [GrAND author preprint](https://arxiv.org/abs/2608.21163) studies dynamic
GPU Vamana/CAGRA ANN maintenance, not this inclusive exact-range/global-mean
contract. It prevents generic claims that GPU dynamic update support is new;
it neither proves nor disproves the proposed exact-search drift failure mode.
Failure to locate a matching published experiment is uncertainty, not novelty.

Only a repeatable dynamic-specific failure that survives ordinary low-cost
controls could motivate a future mechanism. Even then, a fresh novelty and
same-contract comparison gate is required. No paper is edited here.
