# Ordered authority and reordered rejection

The original FP32 coordinates are promoted to FP64 before subtraction. Each
term is `delta*delta`, with FMA contraction and fast/reassociated math disabled.
Original authority sums these rounded nonnegative terms sequentially in
dimension order0..959. Reordered diagnostics sum the **identical terms** in the
approved zone order; final reordered sums are not authority scores.

Reuse the preserved parent guard with `u=2^-53`, `D=960`:

`G = outward(T/(1-2*D*u))`, followed by one additional positive FP64 nextafter.

Only `partial>G` is a safe rejection; equality remains a candidate. Compare
nominal strict-T crossing and guarded crossing separately. True hits consumeD;
nonhits without a guarded crossing also costD and require authority fallback.
Any false rejection, authority bit mismatch, changed input, or unstable
admission decision stops the campaign, with the failed evidence retained.

The guard relates rounded permutations of the same nonnegative contributions,
not an arbitrary GPU reduction or INT8 approximation. A future GPU candidate
must preserve or rederive that arithmetic and reproduce complete original-order
scores. Reordering does **not** justify free original-order reconstruction.

The requested source model counts coordinate-stage reads only. Retaining
previous coordinates, reloading full rows, spill, compaction, ordering, and
output costs remain separate until implemented and measured. CPU full-score
recomputation and hash/fixture time are diagnostic validation, never Host-ready
search timing. Exactness of a CPU certificate is not GPU qualification.
