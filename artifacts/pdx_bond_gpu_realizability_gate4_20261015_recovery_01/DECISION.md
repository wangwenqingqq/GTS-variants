# Decision: PRIOR_ART_WINS

**The known PDX-BOND mechanism realizes a material portion of the headroom under
this static GPU exact-range contract.** The strong secondary flag is true.
The approved priority is correctness → PRIOR_ART_WINS →
LOGICAL_WIN_PHYSICAL_FAIL → remaining PRIOR_ART_LOSES → UNCLASSIFIED/stop.
No threshold, query, estimator, or quality criterion was relaxed after timing.

## Q1. How much of the restricted oracle gap is captured?

The inherited complete 32M-pair CPU diagnostic gives original order
167.291614750, query-global restricted oracle 44.018710250, and measured
PDX-BOND-ZONE32 105.977753125 mean required coordinates. Its exact gap fraction
is 490510893/986183236 = **49.7383118161%**, LOGICAL_MODERATE. These are diagnostic
coordinate-crossing counts, not actual GPU work or a universal information bound.
The prior CPU checkpoint and its failed preparation remain unchanged.

## Q2. Does stage-rounded coordinate source beat the keeper?

Yes: **711,680,776 B/query** versus the exact inherited 1,014,828,776 B/query
keeper model, ratio 0.7012816278280228, SOURCE_WIN. Checkpoint survivor sums at
128/256/512 are 8,452,787 / 1,784,904 / 130,701 across the same 32 queries.
This source model does not price all metadata or original-order restoration;
the GPU measurement below charges the executed implementation instead of
treating retention or fallback as free.

## Q3. Does the logical win become a physical traffic win?

Yes: same-campaign **all-kernel DRAM 1.119477888 → 0.780022448 GB/query**, ratio
**0.6967734301510384**, down **30.3226569849%**. The capture includes scans,
ordered-FP64 replay, compaction and output kernels (416 launches/mode). It does
not include DMA traffic and is one independent NCU process/mode, not a DRAM CI.

| NCU family, mean decimal GB/query | Keeper | Candidate |
|---|---:|---:|
| All staged scans/replay | 1.088546168 | 0.758712304 |
| All CUB compaction kernels | 0.030925024 | 0.021303488 |
| Native output fields | 0.000006696 | 0.000006656 |

## Q4. Does the traffic win become complete Host-ready latency reduction?

Yes: medians of six fresh process mean ACKs are **1.14190696875 →
0.907210875 ms/query**, ratio **0.794470039878194**, down **20.5529960122%**.
All **6/6 paired rounds** win. Paired geometric ratio is 0.7938580071195104;
the fixed-seed (2026101302), 20,000 matched-round bootstrap 95% percentile CI
is **[0.7927909123873055, 0.7949113365265615]**. This is a CI for the paired
geometric estimator, not a CI for the primary ratio of medians.

All primary thresholds pass: latency and DRAM ratios ≤0.90; at least 5/6 wins;
paired CI upper <0.97. Both ratios are also ≤0.80, so the secondary
STRONG_PRIOR_ART_WIN flag is set, without replacing the final label.

| Independent event-enabled diagnostic, mean ms/query | Keeper | Candidate |
|---|---:|---:|
| Scan/replay CUDA events | 1.040002002 | 0.802150003 |
| Compaction CUDA events | 0.053060000 | 0.046178000 |
| Field CUDA events | 0.005053000 | 0.005026000 |
| Host output span (contains field work; do not add twice) | 0.029380719 | 0.029524281 |
| Host ACK minus scan/compact/field events | 0.069435373 | 0.075357748 |

Candidate online priority/sort averages **2.788375 µs/query**, plus **3.25071875
µs** for the Host submission of two 30-int H2D uploads. Both are already inside
the complete ACK. The latter is not isolated device-copy time. Event-enabled
ACKs are diagnostic, not substituted for primary timings. The unexplained
Host-minus-events residual is not automatically CPU/control/wait time.

## Q5. Where is failure, if any?

No logical→physical failure is observed in this scope. The strongest supported
attribution is less staged coordinate/metadata traffic and shorter scan time.
The kernel-launch count remains 13/query; **no launch elimination or measured
CPU-utilization reduction** is established. Register differences alone do not
prove the cause, and the experiment does not isolate coalescing efficiency from
reading fewer coordinates.

The scientific consequence is a **negative novelty closure**: do not claim a
new GTSPP ordering mechanism around the 167→44 headroom. This is an engineering
adaptation of known PDX-BOND ordering to our staged exact machinery, not proof
of an optimal GPU PDX implementation or a result covering all GPU trees,
kNN/ANN, FAISS/CAGRA, dynamic updates, or 100k workflows.

## Recovery and quality audit

The old preparation failed before nvcc/CUDA; it is preserved. The approved
recovery used a new current-source snapshot. Before any NCU attempt, a separate
NCU-only frontend corrected argv0 to absolute `/usr/bin/sudo` and forwarded
the same frozen mean file through sudo's environment reset. The original
controller remains unchanged for qualification/primary/breakdown. There was
no binary/algorithm/query/timer tuning, extra start, failed NCU, or replaced
sample. Final source hashes bind all three controllers.

The curator was rerun only to clarify recovery metadata: eight numerical,
quality, static and raw-manifest outputs stayed byte-identical. Full campaign
raw files were copied and all **1,707** identities checked locally; the
67,194,646-byte compressed archive is preserved privately on both machines.
Neither the public scalar verifier nor figures rerun private exactness or GPU
samples. The complete qualified scope is recorded in README and QUALITY.json.

**Next:** retain the stronger adversarial baseline; stop ordering/portfolio
novelty iterations. A dynamic maintenance/workflow comparison needs a separate
contract and is not launched by this result.
