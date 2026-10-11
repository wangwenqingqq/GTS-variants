# Fixed3 on current PAR/FULL/TILED P

This is a **range-only engineering attribution** against the modern logical P,
not a repetition of the original-GTS experiment. The human selected current P.
FULL kNN no longer uses the old single-leaf verifier and is untouched.
No new pruning, precision change, layout transformation or Graph is introduced.

Read CONTRACT.json, BASELINE_AUDIT.md, DESIGN_CARD.md, NOVELTY_GATE.md and
AMENDMENT_1.md before running. The first failed static admission is preserved;
no runtime observation is silently replaced. New scope is D128/D960 real-leaf
qualification plus the D960/B1/K8 mixed target, not the original D96/K1/K32 set.

## Dependencies and preparation

- The matching GTS-variants repository's external-closure branch at
  `b3ac5ed66e81152a021c9692b4e57ee5cbc16953` supplies the established logical-P
  preparation, CPU oracle and frozen target fixtures.
- An exact prepared logical P directory must contain `source/`, `bin/target`,
  and `PREPARED.json`, matching all hashes in KEEPER_PINS.json. Never use the
  old static native-rank adapter, Safe-C1 or an archive as this keeper.
- CPU Python 3.11+/NumPy, CUDA13.1, sm_120, compute-sanitizer, NSYS, NCU,
  cuobjdump and numactl. No new benchmark framework or dependency installation.
- Reuse the pinned lock adapter from the preceding task and the native runner:
  `diagnostics/fixed3_leaf_packing_20261011/locked.py` and
  `diagnostics/native_knn_faiss_ivf_20261003/run_locked.py` at `094961b6`.
  Stage them as `$RUN/deps/locked.py` and `$RUN/deps/helpers/run_locked.py`.

Use a NEW external scratch (`$RUN`), never an existing campaign directory.
Copy this recipe's Python/CUDA/JSON files and amendment to its root. Copy the
exact prepared P directory as `$RUN/keeper` (the generator does not alter it).
`$PARENT` is the completed current-P campaign root with `campaign/cases` and the
bound `campaign/REGISTERED.json`; `$REFERENCE` is the frozen native-rank P output
prefix from its qualified external campaign; `$CHECKER` is the canonical
external-closure checkout above. `$DATA` must match the GIST SHA in the contract.

```sh
python3 "$RUN/test_recipe.py"
python3 "$RUN/prepare.py" --root "$RUN"
python3 "$RUN/run.py" --root "$RUN" --parent "$PARENT" \
  --reference "$REFERENCE" --checker "$CHECKER" --data "$DATA" \
  --gpu "$ADMITTED_GPU_UUID"
```

The runner enforces the registered physical GPU1 UUID and NUMA0. Another GPU
requires a new hardware contract, not a command-line override. It holds both
shared GPU locks for the WHOLE qualification/work/profile/formal campaign,
passes the same open descriptors to each preserved process runner, and rejects
foreign GPU activity before/during/after every process. Other services are not
signaled. No clock/power setting is changed.

Three production variants, counter-only forks and real-production-TU unit
binaries are built. Units exercise ALL leaf sizes 1..20, tails/inactive groups,
equal-vector different IDs, radius boundaries, deletions and pointer churn.
Bounded mixed outputs use the full exhaustive CPU oracle; target outputs use the
pinned already-qualified native reference with exact result/field bits. Warmup
and measured traces are checked independently. The target is 336 serialized
events: 128 range, 128 kNN, 40 inserts, 40 deletes and two rebuilds.

NCU permission denial is retained as an explicit unavailable diagnostic, never
an isolation/runtime pass or a substitute hardware measurement. NSYS checks
actual grids and uses only the SECOND `native.trace` range. Public timing is
unprofiled `summary.trace_ms`, not NSYS/NCU duration. The six formal rounds are
gated on same-work leaf improvement in both reverse profiler orders.

## Evidence boundary

Large data, output payloads, profiler reports, binaries, full source forks and
private commands stay outside Git. Durable curated evidence/manifests and
source/binary hashes document the gates. Full results and accepted claim scope
are in RESULTS.md and DECISION.md; complete paired P0/P2=1.171413, not the
original-GTS 2.56x ratio. No external-baseline closure,
universal GPU-tree claim, all-shape production admission or novelty claim.

The first controller's mutable-log failure and bounded offline continuation are
documented in AMENDMENT_2.md. Fresh replay uses run.py; resume.py applies only
to the exact retained failure, not arbitrary partial runs. Maximum 48 main
processes + 1 NCU admission probe. close.py is CPU-only and additionally binds
the parent registration to its prior archived SHA; verify_unit_payload.py
independently reconstructs all unit bytes. Public view changes and measured
recipe identities remain explicit in PUBLICATION_VIEW.md.
