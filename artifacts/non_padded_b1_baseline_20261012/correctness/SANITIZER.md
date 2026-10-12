# Correctness and sanitizer scope

All three tools passed with zero reported errors/hazards: memcheck, racecheck,
synccheck. Each used the same compiled candidate `--fixtures`,100 iterations,
two independent stream slots and fresh pointers, N0/1/7/8/9/31/32/33/513,D960,
duplicate vectors, empty answers and exact/adjacent inclusive boundaries.
Fixture max ordered-FP64 score error7.6050418e-8. Raw tool stdout/stderr and
guard/output receipts are retained externally and hash-indexed.

Separately, bounded N4096 and full N1M candidates passed all40 original queries
against complete ordered-FP64 arrays; target candidate max field-scale error
9.6225663e-8, native-scale difference2.0785190e-6,0 FN/FP. Native complete three
payloads match the immutable historical keeper; N1 field bits differ as declared.
Every primary/NCU process repeats complete membership/field validation.

This is not full-N1M sanitizer coverage, Graph qualification, a threshold proof
for all inputs, or all-shape production admission. Compilation/SASS audit,
correctness, sanitizer and timing are separate evidence gates.
