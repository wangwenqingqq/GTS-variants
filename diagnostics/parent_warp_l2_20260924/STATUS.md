# Parent pivot reuse: exploratory negative screen

The million-point GIST and Deep normal-radius Q/W full-output runs passed the
CPU-validated ordered float32 result hashes, and the host assertion checked
the sibling pivot identity on both constructed trees. Q assigns children to
threads; W computes one pivot distance per parent on warp lane zero, broadcasts
it, and lets ten lanes test the children. A single unpaired process per arm
gave the following complete-query means on GPU 2:

| Dataset | Q | W | Q/W |
| --- | ---: | ---: | ---: |
| GIST 1M | 391.152 ms | 400.623 ms | 0.976× |
| Deep 1M | 45.843 ms | 46.553 ms | 0.985× |

The parent-distance work reduction did not turn into an observed speedup in
this screen. With one scalar lane producing each distance, the warp loses
parallel distance producers while neighboring child distances had abundant
thread-level parallelism. No sanitizer or paired timing was run for W, so this
is a rejection of the candidate for further investment, not a formal claim
about every parent-owned mapping. The raw output receipts are under ignored
`local/full_gpu2/`; production source remains unchanged.
