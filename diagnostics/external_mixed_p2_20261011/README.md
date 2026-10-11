# Fixed3 P2 external mixed-service closure

One frozen P2 versus one frozen qualified scan service, no optimization in this
campaign. See CONTRACT.json, BASELINE_AUDIT.md and RESULTS.md. Fresh-process
service comparison is distinct from NSYS attribution, prior internal Fixed3
results, and the old external campaign.

## Reproduction inputs

- Base/current-P Fixed3 recipe: commit `ef716de05b42249eea8a6e89458d547267d4cb84`,
  `diagnostics/fixed3_current_p_20261011`.
- Qualified external code/checker and scan build: commit
  `b3ac5ed66e81152a021c9692b4e57ee5cbc16953`, `artifacts/external_closure`.
- The exact frozen compiled P2 and E identities are in CONTRACT.json. Private raw
  archive contains executed sources, binaries, cases, checks and profiler logs;
  a portable/public hash manifest is in evidence. Large GIST data and installed
  native libraries stay outside Git. They must match INPUTS.json hashes.
- Existing lock adapter and owned-process runner are reused from
  `diagnostics/fixed3_leaf_packing_20261011/locked.py` and
  `diagnostics/native_knn_faiss_ivf_20261003/run_locked.py`.

On the intended host, choose **a new empty scratch**, restore the two qualified
prior campaigns and native oracle, then supply real paths (not example data):

```bash
mkdir -p "$ROOT/deps/helpers"
cp CONTRACT.json prepare.py run.py test_recipe.py "$ROOT/"
cp ../fixed3_leaf_packing_20261011/locked.py "$ROOT/deps/"
cp ../native_knn_faiss_ivf_20261003/run_locked.py "$ROOT/deps/helpers/"
python3 "$ROOT/test_recipe.py"
python3 "$ROOT/prepare.py" --root "$ROOT" --fixed3 "$FIXED3_ROOT" \
  --external "$EXTERNAL_ROOT" --reference "$NATIVE_REFERENCE" --data "$DATA"
python3 "$ROOT/run.py" --root "$ROOT" --reference "$NATIVE_REFERENCE" \
  --data "$DATA" --gpu "$AUTHORIZED_GPU_UUID"
python3 analyze.py --root "$ROOT" --out "$SUMMARY_JSON"
python3 profile.py --root "$ROOT" --out "$PROFILE_JSON"
```

A different GPU identity, rebuilt binary, library or fixture is a **new contract**,
not a silently interchangeable reproduction. This runner intentionally stops at
its first failed qualification/isolation/provenance check, does not replace runs,
and does not install dependencies or change GPU settings. It holds two shared
locks over all 26 processes and checks foreign target-GPU PIDs before/during/after.
Only an owned child process group may be stopped.

The registered service metric subtracts measured final state enumeration/release using
adjacent wall intervals. A small post-drain fence/clock tail remains; see
METRIC_CLARIFICATION.md. Both backends retain
full client IDs/fields before each ACK. Trace-plus-release is a separately reported
secondary, not an inferred extrapolation from the old Fixed3 result. Tail values
are pooled requests from six whole-trace processes, not independent workloads.

CPU-only checks: `python3 test_recipe.py` and `python3 test_analysis.py`. Analysis reuses the published fixed3
process-statistics helper, and all new publication files are checked from the
committed tree. Partial D2H attribution is not a complete isolated Host-output
measurement; cold N0 construction, Graph, other workloads and 10K are not admitted.
