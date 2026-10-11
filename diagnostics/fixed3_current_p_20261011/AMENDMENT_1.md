# Static resource admission amendment (before any GPU runtime)

The first scratch build stopped at the declared 3840-byte shared resource gate.
P0's cuobjdump receipt reports 4864 bytes, while its ptxas receipt reports exactly
3840 bytes of user shared memory. The immutable preceding keeper also reports
4864 bytes in cuobjdump. No GPU runtime or performance sample was collected.
The failure and original recipe remain in the first private scratch archive.

Admit the measured keeper footprint, not a silent pass: ptxas user shared <=3840,
cuobjdump shared <=4864, zero stack/local, and zero spill stores/loads. The extra
1024 bytes are a tool-reported keeper overhead; their origin is not inferred.
A new scratch receives this amended gate; no failed build is overwritten.
All runtime budgets, correctness, timing and acceptance gates remain unchanged.
