# NCU privilege-path correction

State: completed, diagnostic-only; initial plan and amendments retained below.
This is a separate follow-up to the original non-elevated `ERR_NVGPUCTRPERM` attempts, not a replacement of their logs.

## Correction and frozen retry

A sudo-group membership does not make an ordinary process privileged. The earlier
campaign established that its **non-elevated invocation** was denied, not that
counters were disabled or unavailable to the account. An existing passwordless
sudo policy and effective profiling-capable privileges were verified before this
retry. No driver setting, container capability, clock, service, or permission is
changed. The previously omitted elevated invocation is the correction.

- Same byte-identical original binary and source hashes as `EVIDENCE.json`.
- Same Words N=2,000 / 32 checked query IDs, r=4, query-only update entry.
- Same NCU 2025.4.1, CUDA 13.1.115, driver 590.48.01, admitted physical GPU 0.
- GPU 0 idle with no compute applications before admission; another device has
  an existing foreign workload and is excluded. Reuse the GPU-0 nonblocking lock.
- Invoke the existing inspected harness under `sudo -n`; this lets its timeout
  handler terminate only its own now-elevated profiler process group if needed.
  The profiler target remains the same trusted original executable. The harness
  explicitly sets `CUDA_VISIBLE_DEVICES` to the admitted device's UUID.
- First retry exactly the earlier target: `getQresultCount`, one matching launch,
  no skip; SpeedOfLight, LaunchStats, Occupancy, SchedulerStats, WarpStateStats.
  `--clock-control none --cache-control none`. Stop after 180 seconds or foreign
  GPU-0 activity; never signal another user's process.
- Oracle must match all 32 native range counts; retain stdout/stderr, the NCU
  report, receipt and hashes. Old failed receipts remain untouched.
- NCU duration and hardware metrics describe replayed selected kernels, not
  clean end-to-end latency or a fusion speedup. No optimized kernel is run.

The plan above was recorded before collection; results are appended below. Raw
machine identities and policy output stay in excluded local evidence, not in
the public report.

### Pre-launch lock correction

The first elevated harness attempt stopped before launching NCU: append mode
uses O_CREAT, and the existing user-owned shared lock in the sticky temporary
directory was protected against a different owner's O_CREAT open. Preserve that
file and its ownership/permissions. Open an existing lock with `r+` instead, and
create only a missing lock; keep the same nonblocking `flock`. Send the updated
harness under a distinct scratch filename and retain the original harness. This
is not a GPU-counter failure and no GPU work ran in this attempt.

### Successful permission probe and bounded kernel extension

The elevated `getQresultCount` attempt completed with 16 replay passes, a saved
NCU report, a successful 32-count oracle, and no runtime error. Counter access is
available through the existing authorized sudo path. The earlier account-wide
availability conclusion was too broad.

Before further collection, add exactly three selected first-match kernels:
`findNextRnn` and `leafProcessRnnUpdate` in the same Q=32 update workload, and
`dataProcessKnn` in the existing Q=4,096 batched-kNN workload. Keep the same
binary, device lock, five sections, clock/cache policy and timeout. Revalidate
native outputs after each separate run. These selected-kernel diagnostics are
not steady-state throughput samples or a fusion experiment.

## Results: counters are available through sudo

All four selected-kernel collections completed successfully. Each report records
16 replay passes. Native output checks passed for all 32 update-query counts or
all 4,096 kNN kth distances. Original source and binary hashes are unchanged.
The lock correction changes only how the profiling harness opens an existing
lock, not GTS, permissions or the driver's counter policy. GPU 0 returned to
14 MiB / 0% with no compute applications; the foreign job on the excluded device
was still present at closure.

| Selected first matching kernel | Grid blocks | NCU achieved occupancy | NCU compute/SM throughput | Active threads per warp | Replayed duration |
|---|---:|---:|---:|---:|---:|
| `getQresultCount` | 1 | 2.13% | 0.02% | 1.80 | 46.24 us |
| `findNextRnn` | 1 | 2.78% | 0.02% | 12.30 | 4.93 us |
| `leafProcessRnnUpdate` | 96 | 6.97% | 1.20% | 20.48 | 8.58 us |
| `dataProcessKnn`, batched Q=4,096 | 409,600 | 27.31% | 27.37% | 20.33 | 4.27 ms |

Each block has 512 threads, on a 188-SM device. Preserve the metric denominators:
occupancy is `sm__warps_active.avg.pct_of_peak_sustained_active`, whereas SM
throughput is `sm__throughput.avg.pct_of_peak_sustained_elapsed`. Neither is
`nvidia-smi` utilization or whole-query GPU-work coverage. Active threads per warp
is `smsp__thread_inst_executed_per_inst_executed.ratio`, not a count of occupied
SMs. The raw metric names, values, units, receipts and artifact hashes are in
[NCU_PRIVILEGED_EVIDENCE.json](NCU_PRIVILEGED_EVIDENCE.json).

### Interpretation and limitations

- `getQresultCount` has both a one-block grid and very little per-warp active
  work; this supports investigating a cooperative result-count/compaction
  rewrite, not merely removing its surrounding launch. Its scheduler has no
  eligible warp in 95.30% of measured scheduler cycles. Long-scoreboard state
  contributes about 78.31% of the reported average warp cycles per issued
  instruction. This identifies a dependency class, not the producing source PC.
- The first traversal instance is the first tree level, not a representative
  sample of every level. The leaf instance belongs to the first query and uses
  96 candidates; candidate counts vary in the parent workload. The leaf profile
  has 90.47% no-eligible cycles; barrier state is about 38.27% of average warp
  cycles per issued instruction. This does not prove which barrier is causal.
- Batched kNN is not saturated either: its selected distance kernel reports
  27.37% SM throughput and 38.46% DRAM throughput. But it is not suffering from
  the one-block launch geometry. Its long-scoreboard share is about 65.79% of
  average warp cycles per issued instruction; CPU launch fusion alone is not
  established as the fix for this different path.
- These stall shares are derived from named raw warp-state ratios divided by
  `smsp__average_warp_latency_per_inst_issued.ratio`; they are not percentages of
  application wall time. PC sampling was not collected, and the profiler warns
  that the optional PC-sample metric is missing. Do not invent source-PC evidence.
- `--clock-control none --cache-control none` preserves shared-host settings but
  emits profiler consistency warnings. Replay/warmup can change cache and UVM
  state; these are **not** clean kernel-duration comparators to the earlier NSYS
  trace. In particular, do not divide NSYS leaf time by NCU leaf time and claim
  a speedup. No confidence interval or repeatability claim is made from one
  selected report per kernel.
- Do not publish NCU's heuristic “Estimated Speedup” messages as achieved or
  promised gains. The raw exports retain them, but the curated metrics exclude
  those suggestions and unrelated device-configuration fields.
- The Launch Statistics stack field is not used to overwrite the prior
  per-function compiler stack ledger; identical context/runtime stack settings
  are not proof that every selected kernel has the same static stack frame.
- Correctness here remains counts/kth distances, not full materialized IDs and
  distances. The fusion plan's stronger correctness gates remain required.

NVIDIA documents the authorized elevated invocation for restricted counters in
[its permission guide](https://developer.nvidia.com/ERR_NVGPUCTRPERM).
Metric/replay interpretation follows the
[Nsight Compute profiling guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#metrics-reference).
No driver reconfiguration was required.

## Reproduction and evidence preservation

After live admission and verification of the existing sudo policy, the public
harness now supports this invocation without changing lock ownership:

```sh
sudo -n python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" \
  --gpu "$ADMITTED_UUID" --label ncu_sudo_update_count_r2 \
  --kind update --mode ncu --kernel getQresultCount
# Distinct labels for findNextRnn and leafProcessRnnUpdate; same kind and mode.
# For dataProcessKnn, use --kind knn --long and a distinct label.
ncu --import "$REPORT" --page details --csv > "$RUN_DIR/metrics.csv"
ncu --import "$REPORT" --page raw --csv > "$RUN_DIR/metrics_raw.csv"
python3 diagnostics/original_flow_20260923/summarize_ncu.py "$RAW_ROOT" "$OUTPUT_JSON"
# With the preserved four-run archive, verify exact summary regeneration:
cmp "$OUTPUT_JSON" diagnostics/original_flow_20260923/NCU_PRIVILEGED_EVIDENCE.json
```

Never reuse an existing run label. The original non-elevated errors and this
retry's pre-launch lock error are preserved separately. The new raw archive
SHA-256 is `8cfb3389fe6febab069a58dc7d9338c8b6f9a5b9590c6a2c416e59e7bfdfad5c`.
Raw NCU reports, policy output, process identities and logs remain excluded from
Git. This follow-up supersedes the earlier **current availability** statement,
not the historical fact that the non-elevated runs were denied.
