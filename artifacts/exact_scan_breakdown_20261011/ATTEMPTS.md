# Retained preflight attempts

Items 1–9 below are retained preflight records, written before any GPU measurement. Final outcomes follow; the raw source snapshot is preserved privately.

1. Compiler-only first build failed because CUDA 13.1/CCCL no longer provides
   `cub::TransformInputIterator`. The private source archive, registration,
   command, full compiler log and failed preparation are retained. The corrected
   second source snapshot uses installed `thrust::make_transform_iterator` with
   the same inclusive predicate and CUB reduction. No dependency was installed,
   kernel mechanism tuned, or formal GPU sample replaced.
2. Second probe and Host-only dynamic diagnostic compile passed. The CPU oracle
   extends the original dimension whitelist to 256/512 only; unchanged ordered
   FP64 no-FMA loop bitwise matches NumPy on 513 high-entropy rows at all four D.
3. Original first 8-row calibration is disjoint but unrepresentative. At D960,
   target 10 hits gives radius 0.8382741212844849, exceeding fixed mid radius
   0.705625057220459. Target 2059.375 gives 1.1181020736694336. Original calibration
   records and full reference arrays are retained. They cannot be described as a
   valid low/mid/high measured-query selectivity contrast. The human approved a uniform seeded held-out
   calibration (seed 2026101112), before any GPU timing. R1 calibration gives
   low 0.7045060396194458 < fixed mid 0.705625057220459 < high 0.8515210747718811.
   Attained measured-query counts remain an outcome, not a retuning target.
   R0 contract and CPU calibration remain immutable; R1 READY pins both records.
4. Read-only NCU metric inventory was queried with the authorized administrative
   capability, without changing driver permissions or GPU settings. Current
   DRAM base names are `dram__bytes_op_read`/`dram__bytes_op_write`; unsupported
   old names are not silently substituted by logical payload counts.

5. First matched-reference compilation failed because the included parent
   harness undefines a caller main macro and defines its own main. No GPU ran.
   The repair generates a private support header containing the byte-identical
   parent prefix before its main, records original and generated hashes, and
   leaves the parent source untouched.

6. Before first GPU launch, the explicitly admitted device became occupied by
   an unrelated two-device service. No admission, profiler or timing process was
   launched and no foreign process was touched. A proposed same-model replacement
   was awaiting confirmation at that checkpoint. No replacement was used: the
   original admitted device was idle on the later preflight, and all valid
   samples used it with the same binding. Device identities were never mixed.
7. Read-only preflight review identified insufficient prior-stage receipt
   binding, incomplete metadata/event validation, and a missing fresh-contract
   READY route. These are corrected before GPU launch; negative tests reject
   wrong shape/mode/diagnostic, infinite/incomplete pass intervals, truncated
   payload elements, incomplete COPY rows/events/warmup and deleted qualification
   jobs. Six CPU tests pass. Profiler checks explicitly expect diagnostic mode.
8. CPU reference counts under approved radii are 200.34375 /205.9375 /1644.9375
   for low/mid/high on the fixed32 measured queries. The planned 10 /205.9375 /
   2059.375 selectivity targets are not attained. D128/256/512 reference hit means
   are 1.1875 /16.84375 /103.875, not matched output selectivity. This limitation
   is preserved and cannot be repaired by post-measurement radius retuning.

9. The first remote run of the added negative tests exposed an incomplete
   scratch dependency closure (an existing transitive Python parent was absent).
   It did not launch a GPU process. The complete committed baseline archive
   was added to the task scratch without changing new artifact files; its SHA
   is retained. The failed test log is preserved, not rewritten as a pass.

10. Final primary/diagnostic stages all passed. The first separate matched
    reference attempt lacked BUILD_MAPPING=TILED and failed before CUDA
    initialization, with no timing. The human authorized one registered
    environment correction only; the unchanged binary then passed all 40
    complete members and field bits. None of the previous 103 valid processes
    was rerun or replaced.
11. A separately approved L2 read/write supplement passed runtime, isolation
    and all 40 output checks. Its first CPU postprocessor assumed total=read+write,
    which the captured 10,048 Other sectors falsified. Raw capture and rejected
    interpretation are retained. Offline three-bucket accounting corrects the
    interpretation without another GPU process; Other subtype remains unknown.
12. Final raw audit verifies all primary registrations, exact job sets,
    source/binary/input/guard/output hashes, matched output hashes and current
    dataset identity. 106 top-level starts, 105 valid processes, one retained
    pre-CUDA failure; budget 110. No optimization prototype or paper edit.
