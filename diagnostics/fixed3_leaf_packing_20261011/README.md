# Original GTS fixed3 leaf packing

Three variants only: original512-thread one-leaf CTA (G0),32-thread one-leaf CTA
(G1), and32-thread three-leaf CTA (G2). See BASELINE_AUDIT.md, DESIGN_CARD.md,
NOVELTY_GATE.md and CONTRACT.json. This is not a new pruning, arithmetic or
layout algorithm, nor a current-GTSPP or external-baseline experiment.

G2 assigns ten lanes per leaf, but preserves **all20 original result slots** by
slot stride10. This is necessary for sort padding and the pinned size11/13
boundary leaves. GIST's pinned index has only size10 leaves. Every original
distance remains required; tails use the same guarded kernel.

## Replay

Requirements: Linux, Python>=3.11, CUDA13.1/SM120, Nsight Systems, compute-sanitizer,
numactl and the existing NumPy/CuPy oracle environment. No new dependency or GPU
setting is installed/changed. Supply the exact eight upstream source files and
the preceding hash-pinned data, indexes, query/oracle and boundary artifacts.
This collection uses the explicitly authorized physicalGPU1/NUMA0. Verify live
ownership/idle state and UUID before executing; GPU0/foreign processes are not
part of the experiment.

```sh
python3 test_protocol.py "$PINNED_GTS_SOURCE"
python3 test_lock.py
bash build.sh "$PINNED_GTS_SOURCE" "$NEW_SCRATCH"
CUDA_VISIBLE_DEVICES="$VERIFIED_GPU1_UUID" ncu --query-metrics > "$NEW_SCRATCH/NCU_ADMISSION.txt"
python3 "$NEW_SCRATCH/run.py" qualify --root "$NEW_SCRATCH" \
  --reference "$REFERENCE_ROOT" --prior "$QUALIFIED_PIVOT_CAMPAIGN" \
  --data "$GIST_DATA" --python "$CUDA_PYTHON" --gpu "$VERIFIED_GPU1_UUID" --numa 0
```

Use the same arguments for phases `work`, `profile`, then `formal` in order.
Each phase refuses an existing output directory. Formal refuses a failed Gate E.
The controller retains both standard shared GPU locks across all processes in
each phase; children adopt the same open-file descriptions and keep foreign-PID
checks. Never run timing/profiling concurrently. The root-local lock additionally
prevents duplicate controllers; it is not the GPU isolation mechanism.

The actual NCU admission probe returned ERR_NVGPUCTRPERM. Do not bypass it or
modify driver policy. This recorded contract uses NSYS actual grid/CTA counts
and leaf-inclusive duration for Gate E and marks issued-instruction, DRAM/L2,
hardware occupancy and dynamic local-traffic counters unavailable. If counter
access differs in a replay, register an explicit profiling amendment rather
than silently replacing this collection. Profiler duration is never the formal
Host-ready denominator.

Generated source, binaries, complete raw logs/receipts, sidecars and profiler
reports stay outside Git; portable manifests and curated evidence identify
them. Upstream original headers are caller-supplied, not redistributed or
relicensed. Failed or superseded orchestration generations remain preserved.
