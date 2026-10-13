# M2 cheap kill — one CPU replay, not an encoding search

Population: frozen Gate1/Gate2 original32 range queries over all1M initial GIST
rows, original D960 order, original FP32 radius. Use one256-dimension/8-bit code
representation. Boundaries/codes are computed once without query selection.

Numerical guard: interval endpoints are FP64, validated to contain every encoded
coordinate. Query distance-table terms are rounded toward zero with nextafter;
the prefix lower bound is max(0, sum*(1-2^-40)-2^-100). Compile without FMA,
fast-math or reassociation. Check the bound against the independently accumulated
ordered raw prefix on **every row of every query**, at both128/256. Stop on any
violation. Full ordered-FP64 reference answers must be contained in the screen;
fallback answers/scores must equal the complete reference. Boundary and tie
fixtures precede population replay. This is CPU screen/fallback qualification,
not CUDA numerical or sanitizer qualification.

Representation = N*256 code bytes + 256*257*8 boundary bytes. Compare with
N*960*4 raw bytes. The first-two-stage baseline is
512*N + 512*exact_survivors_at128. Candidate raw prefix is
1024*encoded_survivors_at256 (including false positives of the code screen).
Report code reads128*N +128*encoded_survivors_at128 and the512KiB query LUT
separately, plus known later-stage work. Nothing in this logical payload model
is a measured DRAM or latency result.

Numeric gate: representation<=25% raw AND aggregate raw-prefix saving>=50%.
Quality/input/provenance failure -> unvalidated, stop, no automatic replacement.
Pass still fails research admission if the only mechanism is known filter/refine.
No update, encoding sweep, CUDA implementation or external timing is allowed.
