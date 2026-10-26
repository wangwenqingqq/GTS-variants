# E1 true-arrival maintenance experiment (unvalidated)

**Remote campaign stopped. GPU admission is deliberately disabled.** Read
[runs/SUMMARY.md](runs/SUMMARY.md) before running anything. No result in this
continuation supports a paper speedup or contribution decision.

The frozen [CONTRACT.md](CONTRACT.md) is unchanged; subsequent authorizations
and the stop are append-only in [AMENDMENTS.md](AMENDMENTS.md). The scope-limited
[AUDIT_RESULTS.md](AUDIT_RESULTS.md) does not clear Linux teardown or the P/G
executed-query-path boundary.

Local checks (no GPU/SSH):

```sh
python3 -m unittest discover -s dasfaa_e1/tests -v
python3 dasfaa_e1/check_no_direct_insert.py
python3 dasfaa_e1/analysis.py
bash -n dasfaa_e1/build.sh
```

`prepare_inputs_v3.py` prepares approved isolated inputs and a complete mixed-
workload matrix. It never silently repairs native ANN query collisions,
shortens infeasible traces, recycles IDs or invents arrivals. Input preparation
is not an oracle pass. `inventory_real_data.py` takes explicit corpus roots and
only inventories real files; it does not admit replacement datasets.

The existing dynamic adapter executes native **range** candidate enumeration,
not patched static kNN. `native_{g,p}/search_v2.cuh` are exact mandatory patch
provenance with `executed=false`. Do not mislabel an unused source patch as a
binary correctness repair. Resolve this boundary before decision-grade work.

No remote action is authorized by the presence of these scripts. Explicit
campaign resumption, guarded Linux cleanup/lock-lifetime validation, fresh
admission and all declared correctness gates are still required. Never bypass
`REMOTE_LAUNCH_READY=False` merely to obtain timing numbers.
