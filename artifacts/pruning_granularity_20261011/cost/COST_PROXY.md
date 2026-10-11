# Paid metadata and verification work

Each query uses4 full-D query-pivot distances and checks every tile. Pivot scores are reused from the qualified immutable campaign, not newly timed here. Endpoint reads=8*tiles, checks=tiles (or4*tiles pivot-interval checks); stored endpoints=64*tiles bytes. Full-filter logical endpoint payload/query equals stored metadata bytes, **not** measured traffic or per-query transfer/allocation. A common FP32 pivot payload is4*960*4=15360 bytes; pivot IDs32 bytes, query3840 bytes and tile mapping/compaction/output costs are separate. No equivalent-distance price is assigned to a scalar endpoint.

| Snapshot | Target size | Tiles | Endpoint reads/query | Endpoint metadata bytes | Ratio vs256 |
| --- | --- | --- | --- | --- | --- |
| initial | 512 | 2048 | 16384 | 131072 | 0.5 |
| initial | 256 | 4096 | 32768 | 262144 | 1.0 |
| initial | 128 | 8192 | 65536 | 524288 | 2.0 |
| initial | 64 | 16384 | 131072 | 1048576 | 4.0 |
| initial | 32 | 32768 | 262144 | 2097152 | 8.0 |
| first_rebuilt | 512 | 2048 | 16384 | 131072 | 0.5 |
| first_rebuilt | 256 | 4096 | 32768 | 262144 | 1.0 |
| first_rebuilt | 128 | 8192 | 65536 | 524288 | 2.0 |
| first_rebuilt | 64 | 16384 | 131072 | 1048576 | 4.0 |
| first_rebuilt | 32 | 32768 | 262144 | 2097152 | 8.0 |

Verification work is surviving_objects; modeled full-D distances add the common four query-pivot distances. This is not latency, cache/DRAM traffic or a whole-system cost ledger. More fine tiles increase checks, metadata and potential scheduling cost.

## Prespecified sensitivity, not GPU time

normalized_proxy=surviving_objects/N + lambda*tiles/tiles256. Only lambda=.01,.05,.10 are checked. No coefficient is fit to timings or chosen for admission. Lambda has no inferred GPU calibration.

| Snapshot | Target size | Lambda | Mean normalized proxy |
| --- | --- | --- | --- |
| initial | 512 | 0.01 | 0.704439437 |
| initial | 512 | 0.05 | 0.724439437 |
| initial | 512 | 0.1 | 0.749439438 |
| initial | 256 | 0.01 | 0.698981156 |
| initial | 256 | 0.05 | 0.738981156 |
| initial | 256 | 0.1 | 0.788981156 |
| initial | 128 | 0.01 | 0.700529250 |
| initial | 128 | 0.05 | 0.780529250 |
| initial | 128 | 0.1 | 0.880529250 |
| initial | 64 | 0.01 | 0.713628188 |
| initial | 64 | 0.05 | 0.873628188 |
| initial | 64 | 0.1 | 1.073628187 |
| initial | 32 | 0.01 | 0.747223031 |
| initial | 32 | 0.05 | 1.067223031 |
| initial | 32 | 0.1 | 1.467223031 |
| first_rebuilt | 512 | 0.01 | 0.695575750 |
| first_rebuilt | 512 | 0.05 | 0.715575750 |
| first_rebuilt | 512 | 0.1 | 0.740575750 |
| first_rebuilt | 256 | 0.01 | 0.688735687 |
| first_rebuilt | 256 | 0.05 | 0.728735687 |
| first_rebuilt | 256 | 0.1 | 0.778735687 |
| first_rebuilt | 128 | 0.01 | 0.689172531 |
| first_rebuilt | 128 | 0.05 | 0.769172531 |
| first_rebuilt | 128 | 0.1 | 0.869172531 |
| first_rebuilt | 64 | 0.01 | 0.701709156 |
| first_rebuilt | 64 | 0.05 | 0.861709156 |
| first_rebuilt | 64 | 0.1 | 1.061709156 |
| first_rebuilt | 32 | 0.01 | 0.735008281 |
| first_rebuilt | 32 | 0.05 | 1.055008281 |
| first_rebuilt | 32 | 0.1 | 1.455008281 |

| Snapshot | Lambda | Lowest-proxy target (coarsest tie) |
| --- | --- | --- |
| initial | 0.01 | 256 |
| initial | 0.05 | 512 |
| initial | 0.1 | 512 |
| first_rebuilt | 0.01 | 256 |
| first_rebuilt | 0.05 | 512 |
| first_rebuilt | 0.1 | 512 |

These conditional proxy optima do not establish a measured sweet spot. Lower survivor counts plus higher metadata are a tradeoff, not free acceleration.
