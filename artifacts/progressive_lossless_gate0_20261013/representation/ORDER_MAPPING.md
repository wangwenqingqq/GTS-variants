# Ordered FP32 keys

For raw uint32 bits u, `K(u) = ~u` if sign=1, otherwise `u XOR 0x80000000`.
For key k, inverse bits are `k XOR 0x80000000` when its high bit=1, otherwise `~k`.
All operations have uint32 width. The mapping is a permutation of all 2^32 bit
patterns. Numeric x<y implies K(x)<K(y) for finite FP32 values; negative bits
reverse order, positive bits preserve it. Negative and positive zero remain
bit-distinct adjacent keys but compare numerically equal. Subnormals are untouched.

NaN payload/sign/signaling bits and both infinities are recoverable verbatim.
NaNs have no numeric ordering assertion. The finite search domain is exactly
key [0x00800000,0xff7fffff]; outside this domain are infinities and NaN tails.
Finite L2 service rejects nonfinite inputs/queries at admission, rather than
making an arbitrary NaN-distance decision. Integer-only recovery still accepts
all bit patterns. No normalization, scaling, clipping, or approximate reconstruction.
The sign transform is existing radix-sort practice, not a contribution.
