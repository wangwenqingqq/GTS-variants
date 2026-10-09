# Append-only admission attempts

## R1: full leak-check rejected; zero primary samples

The same-process clone/restore wrapper compiled, preserved all 112 normalized
GPU functions (74,147 instructions), and completed the seven bounded A/B/C,
no-warmup and timing-injection controls. Full `memcheck --leak-check full`
returned error-exitcode 86: 192 bytes in 14 reported allocations, with allocation
stacks at initial `cudaFree(nullptr)` context initialization, not service-owner
allocation sites. A fresh phase-A executable control on the same input and device
reported the identical size/count and initialization stack boundary. Access
sanitizer results from phase A did not previously admit this stronger leak gate.

The six scalar managed symbols and common bounds object are context-owned.
The replacement explicitly tears down this process's CUDA context after complete
output serialization. This is not a physical-GPU reset, suppression or manual
free of a managed symbol. Hot service-owned release remains inside the existing
continuous trace; initial context and its final teardown are separate. Full
sanitizer and affected wrapper checks must pass again before observer or primary
admission. Keep both failed controls and all seven preceding observations in
private raw evidence. Do not relabel R1 as sanitizer-clean.

## R2: explicit context reset reduces report; full leak gate still fails

Explicit process-context teardown reduced the report to 96 bytes/seven
allocations. It did **not** make full leak-check clean. An independent minimal
CUDA program with one `__managed__ int`, one trivial kernel, no service buffer
allocation and explicit `cudaDeviceReset()` reproduced a four-byte initialization
leak report. This localizes the residual boundary to static managed-symbol
lifetime/tool accounting; it does not establish universal leak-freedom or a
vendor bug. The exact initialized symbols in this binary sum to 96 bytes.

Before any observer or primary samples, admission was explicitly amended to the
original supplied access/synchronization sanitizer scope. No suppression file,
binary patch, unchecked pointer free, device setting, input, method, statistical
threshold or primary sample count was changed. Run unsuppressed memory-access
memcheck/racecheck/synccheck, actual clone/restore and target rebuild again.
Keep the enhanced full-leak failure as `UNRESOLVED_CONTEXT_SYMBOLS_NOT_CLEAN`,
with the phase-A and minimal controls. A short diagnostic result cannot claim
complete leak-clean status, long-workload admission or production promotion.

[NVIDIA's sanitizer documentation](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html)
distinguishes ordinary memory-access checking from the separately enabled
`--leak-check full` context-destruction allocation report. The interpretation
of this particular static-symbol report remains a local inference, not an
NVIDIA-confirmed defect.

## S1: static launcher receipt failure, not an admitted speed result

The first initial/FULL static diagnostic executed and serialized its complete
payload, but the unchanged guard failed while hashing its executable because
its command began with relative `env`. The guard requires an absolute executable
path for its final identity receipt. No valid receipt was produced, so this row
is not admitted as a static comparison. Original outputs, monitor, checks and
exception remain in private S1 evidence. No primary sample is affected.

S2 resolves the installed native `env` to an absolute file before launch and
repeats the fixed six static diagnostics in a fresh directory. It changes no
GPU code, inputs, warmup, numeric tolerance, timing or selection rule. The one
unadmitted tooling process is additional to six admitted diagnostics: seven
actual static processes in total, within the plan's maximum-eight external
budget. Optional two-process IVF_ALL is consequently not run in this delivery.
This repair is not a rerun selected because of an unfavorable speed.

## T1: stale primary transport closed after remote checkpoint verification

The original long-lived SSH transport did not deliver its final output. Remote
inspection found all 18 process payloads, six valid completed GPU-guard receipts,
and complete CPU quality output, with no remaining primary process. Its exact
executed driver and raw records were preserved. The task-owned stale local SSH
transport was then terminated; that transport returned 255, not a successful
shell receipt. No remote GPU task or foreign process was signaled.

The final offline hardening replay independently rechecked all full outputs,
CPU oracle/library identities, registered source/rows and every original guard,
then recomputed the fixed summary. It completed successfully. There were no
additional or replaced primary timing samples. The report is admitted from those
complete remote execution receipts and fresh quality replay, not from the failed
transport exit code.

## S2: native import failed before GPU work; retain completed diagnostics

S2 initial FULL/BOUND completed with valid isolated guard receipts. Its first
Flat process failed before GPU construction: resolving the virtual-environment
Python symlink selected the system interpreter, which lacked Faiss. Keep its
failed guard and `ModuleNotFoundError`; it delivered no native timing/payload.
The correction preserves the absolute virtual-environment executable path,
without symlink resolution, dependency installation or backend substitution.

A pre-execution recovery record preserves the exact S2 launcher identity and
retains those two completed GTS rows. Only the four previously missing diagnostics
are executed; the failed native import has a distinct retry guard and is not
silently overwritten. The wrapper allows this recovery only for that specific
pre-GPU import failure, with exactly two existing valid GTS receipts and no native
payload; no generic favorable-result resampling is supported. Totals: six
admitted static GPU diagnostics, one unadmitted S1 GPU process, one pre-GPU import
failure = eight static process invocations. Optional IVF_ALL remains excluded.
