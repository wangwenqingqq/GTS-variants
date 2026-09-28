# 2026-09-24 continuation

The uploaded record ended while GPU 0 sanitizer checks were running. The retained
remote receipts establish that the monitor subsequently detected foreign GPU
activity during Deep `gate_memcheck_R`, terminated only its owned workload, and
stopped the suite. There are 153 complete output runs, 37 successful sanitizer
runs and one interrupted sanitizer run. No primary or sustained timing ran.
The original attempt and its raw files are preserved in `local/interrupted_gpu0`.

The Git branch at `e1ccb98fa2dfb3765e987f2f70a768c06eda0939` did not yet contain
this experiment. Its generator, contract, audit and test were recovered from the
uploaded record. The generated driver, traversal kernels, runner, verifier and
suite match the retained remote files byte-for-byte. Inherited CPU composition,
address bounds, mode and balanced-order checks passed again.

The original GPU remains occupied. Under the existing idle-device scope, physical
GPU 5 was admitted on the same server, using its existing advisory lock. The
pre-run `amendment.json` and `logs/admission.json` are retained in `local/raw`.
No GPU configuration changed. The complete 423-run protocol is repeated on GPU 5;
no GPU 0 observation is pooled, and the executable, fixtures, modes, orders,
timing scope and decision threshold are unchanged.

The binary is reused exactly, with SHA-256
`588a7d2a8690e1c724dc3825dd1b423e854003dc1001dadc405b347652634929`.
Static SASS and resource dumps are retained, with file and selected-function
hashes in `STATIC_EVIDENCE.json`. These are exact cuobjdump-section hashes,
not the normalized hashes from older campaigns. They do not imply dynamic spills.
The final audit also checks NSYS runtime symbols, launch counts and registers.

For the same interrupted artifact, `restart.py PREVIOUS FRESH --gpu-index INDEX
--gpu UUID` verifies all pins, admits the device, records the amendment, creates
a fresh root, and serially executes full/gates/stress/screen/sustained/trace.
It rejects an existing output directory and never deletes or overwrites attempts.
The benchmark child runs as the existing `wxr` account.

The final analyzer verifies all generated/source/fixture/binary hashes, complete
ordered outputs, sanitizer summaries, changing-query hashes, receipt/log equality,
device snapshots, sampled interference checks, runtime launch signatures, all
four primary process rounds and both sustained orders before producing evidence.
Sampled checks do not prove exclusive hardware access; CPU is shared and GPU
clocks remain uncontrolled, as in the original contract.

During the GPU 5 stress stage the controlling SSH command exited with code 255.
A new read-only connection confirmed that the original suite and benchmark were
still running and that the selected GPU had only the owned benchmark process.
All 36 stress runs subsequently completed successfully. The original orchestrator
then exited before starting primary timing. `finish_after_transport.sh` checked
that the prior PID had exited, that all stress receipts matched the complete
stage transcript and passed the existing prerequisites, and that no later-stage
logs existed. It then continued screen/sustained/trace with persistent stdout at
02:28:17 UTC. No run was repeated or replaced, and no benchmark code changed.
