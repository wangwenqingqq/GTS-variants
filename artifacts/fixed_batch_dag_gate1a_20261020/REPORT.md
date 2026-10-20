# Gate 1A: frozen inputs, reproducible development anchor

**Result: Gate1A only.** The protocol and128 held-out identities are frozen;
the original28 development cases reproduce exactly. There is **no held-out
scheduling result** and no Gate1 GO decision. BQSI is still a research hypothesis.

## Frozen workload

| Item | Frozen value |
|---|---|
| Database | GIST1M,1,000,000 vectors x960 FP32 dimensions |
| Payload / file size | 3.840 GB /3,840,000,012 bytes |
| Development | Original32 database-row queries,unchanged |
| Held-out | 128 new,distinct IDs;no intersection with original32 |
| Held-out batches | B2:64;B4:32;B8:16;identical members for all strategies |
| Sampling | Identity-only seeded SHA256 rejection sampling and batch permutation |
| Radius | FP32 `0x3f34a3d8`;constant inherited parent distribution |
| Query payload | 491,520 bytes,privately retained;per-vector SHA256s public |
| Duplicate check | No byte-identical query within held-out or versus old32 |
| New query distances / orders / depths / oracle | 0 /0 /0 /0 |
| GPU starts | 0 |

The immutable selection is `QUERY_SELECTION.json`; it was generated before any
new vector read. The source snapshot was frozen before extraction and targets.
The original dataset was hash-checked before and after extraction, and the
exported rows were independently matched byte-for-byte with that authority.
No radius,query or batch was selected using a sharing outcome.

This is independence from the development IDs, **not an independent dataset**.
Queries are still database rows with self-matches. The radius distribution has
one atom; no multiradius or production-workload claim follows.

## Old32 reproduction: complete source cost, decimal GB/query

The re-execution uses the unchanged Gate0 chain/tile/terminal contract. All28
CSV outputs are byte-identical,including every context,weight,witness and bound.
This is an exact finite combinatorial replay,not a new128-query evaluation.

| B | Batches | FANOUT | Oracle lower | Oracle feasible upper | Batch full scan | Strong residual interval |
|---|---:|---:|---:|---:|---:|---:|
| 2 |16|0.753396888|0.671067576|0.671067576|1.920003960|10.9277478194%,exact|
| 4 |8|0.706752120|0.541218968|0.541218968|0.960003960|23.4216703871%,exact|
| 8 |4|0.617970648|0.340882040|0.603455032|0.480003960|2.3489167401% to44.8384739464%|

FANOUT attains the strong simple envelope on all28 development batches.
The earlier weaker LOOKAHEAD primary has not been substituted into the Gate1
control. B8 remains unresolved; no **evaluated feasible** B8 schedule beats the
shared full scan. Its lower bound below full scan does not establish a win.

All317,807 unique weighted contexts and125,000 candidate sectors per batch were
included. The4096/context and2M/batch oracle caps were unchanged. The source
model assumes one hypothetical coordinate-major database and a1024-byte tile;
it does not measure actual DRAM,cache,GPU divergence or service latency.

## Gate1B/C is still pending

FANOUT already rejoins matching ready tiles. `PREFIX_REJOIN` is therefore not
admitted as a distinct mechanism by name. Before any held-out feature derivation,
the next phase must complete a development-only design review,ready-provider
noninterference tests,exactness/cost checks,selection of one primary candidate,
and an immutable implementation/parameter freeze. There is no automatic
held-out evaluation command in this artifact.

The later primary must meet **all** frozen conditions on **each** of B2 and B4:
at least5% aggregate full-source saving versus FANOUT;paired batch-bootstrap95%
lower bound above0;at least25% conservative residual-gap capture;worst batch
loss at most3%;full source below one shared full scan;and no held-out tuning.
B8 is separately exploratory. A missing/undefined quantity cannot be passed.
No thresholds are relaxed to rescue a candidate.

For positive improvement delta and oracle interval[L,U],use delta/(F-L) as the
conservative capture,not delta/(F-U). Extra scheduler metadata is not free:
source inputs/rereads are charged;state traffic,peak live bytes and CPU timing
must be reported separately. The fixed query arithmetic,terminal policy,tile
buffer and parent input costs remain unchanged.

## Execution evidence and limitations

The new CPU execution uses existing Python/NumPy/GCC,actual nice10 and at most4
workers. Existing processes,prior campaigns and all old results remain intact.
Full raw observations,original commands,logs,qualification,query vectors and
execution sources are retained privately under a450-file census. The independent
checker binds exact command/start sets and source identities,rebuilds an
identical binary,repeats the qualification and re-analyzes every context.
All eight sealed-evidence tampering counterfactuals on copies were rejected,
including synchronized payload/receipt modification,empty source maps,missing
qualification,extra attempt/feature files,missing commands,changed logs and
synchronized binary/receipt modification. These test the census/seal boundary,
not independent negative coverage of every semantic-audit branch.
The713-member private archive was checked in full on the execution host and
independently after download. Public manifests expose identities,not raw vectors.

No speed claim compares wall time across the CPU replacement. No held-out
source-saving result,scheduler time,metadata traffic,novelty admission,index
compatibility,arrival SLA or end-to-end benefit has been measured here. The
next action is Gate1B on old32,not GPU or Query-Space Index implementation.
