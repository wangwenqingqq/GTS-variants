# Dependency-aware update attribution

This is a bounded six-way mechanism experiment,not a new production API.
The initial CPU gate is `CONTRACT.json`;GPU admission is separately frozen in
`GPU_CONTRACT.json` and an execution registration containing exact hashes.

## Competing explanations

| Contrast | Invariant | Changed mechanism |
|---|---|---|
| NATIVE vs WAVES | Ordered ownership and all original row moves | Safe CUDA13.1 copy batching |
| WAVES vs GENERIC_WAVES | Same dependency levels and original moves | Standard-library coarse indexed-copy executor |
| GENERIC_WAVES vs GENERIC_DSE | Same Thrust functor | Original moves/levels vs composed final assignments |
| GENERIC_DSE vs TAIL_GENERIC | Same sorted final assignments and Thrust functor | Generic sparse propagation vs tail-specialized planner |
| TAIL_GENERIC vs TAIL_CUSTOM | Same Tail plan | Thrust versus frozen custom row materializer |

All six use the same binary and unchanged frozen query functions;TRACE is the
only difference between timing and diagnostic builds. B1 and single-assignment
cases use a common native-copy fallback. Generic DSE is our transparent semantic
baseline,not an execution of LLVM or a claim that LLVM implements this service.

## Ownership and readiness card

| Phase | Owner / live state | Ready edge / overwrite rule |
|---|---|---|
| Validate | CPU live-ID map and unique batch IDs | Reject before any owner mutation or device work |
| Capture | CPU occurrence/position maps,native mutation witnesses | Sequential swap-delete transitions,descending sources |
| Compile | CPU command vector plus generic map or tail512/map | Resolve original sources;preserve retired destinations |
| Certificate | CPU destination set | Unique destinations,disjoint original sources before in-place parallel copy |
| Metadata | Page-backed CPU plan → 4096B device buffer | H2D on same stream;host plan lives until final stream sync |
| Execute | One independent uint32 coordinate per Thrust iteration;custom oneCTA128/row | Waves serialized in one stream;final plan independent within launch |
| Complete | Host ACK | Explicit stream synchronize,then local plan destruction before return |
| Append | Existing native bulk H2D and owner updates | Starts after delete ACK;fresh monotone occurrence IDs |
| Query | Frozen PDX range kernels | Starts only after earlier updates return |
| Release | Host | Export excluded separately;all Store and common ledgers released in service denominator |

No shared memory,barriers,Tensor Cores or new async handoff are introduced.
Custom coordinates are `j=threadIdx.x+128*t`;Thrust covers the flat rows×960
index space with the installed native policy. Every persistent vector stays in
its original FP32 row-major storage;copies preserve arbitrary uint32 bits.
Expected coordinate address/metadata registers are small,no local arrays in
device functions;actual registers/stack/local usage are audited after compile.
There is no shape autotuning. Admission is D960,B1–512,N≤1M,serial one stream;
two independent streams/pointer churn are correctness tests,not concurrency claims.

## Predicted ledgers

- NATIVE/WAVES/GENERIC_WAVES write `moves×3840` payload bytes.
- Composed plans write `final_assignments×3840`;metadata adds `assignments×8`
  except a common native fallback when there is only one assignment.
- A copy reads and writes payload;payload is not total DRAM traffic. Cache reuse,
  staging,driver copies and write policy require measured counters.
- Tail has fixed512-element stack provenance plus an ordered map. Generic uses
  a sparse hash map with no tail assumption;both add capture,certificate,
  allocation/sort and destructor costs. Complete ACK charges all of these.
- Query coordinate visits and numeric authority must be invariant across
  variants on the same trace. Query runtime need not be statistically identical.

## Harness costs and denominator limits

The common CPU oracle allocates one full-capacity label array before formal
events. Its harness construction/destruction is excluded in every variant;
process peak RSS includes it together with client inputs and exported answers.
Backend ownership, device plan workspace, plan destruction and explicit Store
release remain charged. Events+release is a warm, built-service denominator,
not cold process wall time, input loading, CUDA context startup or index build.
Full offline state validation/export is separately timed between events and
release. No query statistic rebuild is performed; the original mean is frozen.

The capture and construction/certificate subtimers do not include local
destructors. Their stack-plot remainder includes destructors, metadata, CUDA
dispatch, execution, waiting and other ACK costs; it is not GPU-only time.
`cpu_events_user_s + cpu_events_system_s`, divided by events wall seconds,
measures average process core-equivalents, not machine-wide CPU utilization or
pure algorithmic CPU computation. Process RSS is not isolated planner peak
memory, and known device-owned bytes do not account for every driver allocation.

## Gate0 finding and claim boundary

Generic propagation returns the same final assignments as Tail in all exhaustively
tested N≤8 deletion sequences,the random tests,and every batch of16 registered
traces. Thus the proposed assignment-elimination ability is not by itself a
distinct algorithmic contribution. The bounded GPU experiment is still useful
to distinguish coarse execution,dependency elimination and planner overhead.
It does not waive the novelty gate or authorize an unbounded optimization search.
The only defensible A-level route would require an additional concrete,
nonincremental mechanism difference not established by these equivalent plans.

The logical-age stresses are reproducible synthetic cancellation models,not
real production traces. Uniform re-deletion of fresh occurrences is deliberately
kept separate from actual within-batch RAW/WAW and elimination.
