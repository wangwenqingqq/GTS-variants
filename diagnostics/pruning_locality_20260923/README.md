# GTS pivot-locality follow-up

## Decision

**Do not promote R or T under the preregistered screen.** Restoring pivot locality
fixes the previous transpose's cache regression, but does not produce a useful
high-dimensional query gain. Tloc has a small positive hot-query screen; retain
that result rather than calling every comparison a slowdown. Neither candidate
passes the required >1.03 paired lower-bound gate against both E and S.

This is four independent processes per mode, 512 measured queries per process,
64 warmups, with every pair observed twice in each order. Confidence intervals
use the exact 4^4 process-paired log-ratio bootstrap, not independent query samples.
Hardware is physical GPU 5, RTX PRO 6000 Blackwell Server Edition, 188 SMs,
CUDA 13.1.115, driver 590.48.01, unchanged 600-W limit. CPU is shared/unpinned;
clock locking is not independently established. No GPU settings were changed.

## Completed-query screen

Values are medians of process-mean query latency. Positive change means slower.

| Dataset | E (us) | S (us) | R (us) | T (us) | R vs E | T vs E |
|---|---:|---:|---:|---:|---:|---:|
| GIST | 7578.414 | 7597.996 | 7599.969 | 7665.896 | +0.28% | +1.15% |
| Deep | 804.118 | 808.101 | 809.202 | 813.848 | +0.63% | +1.21% |
| Tloc | 62.666 | 62.923 | 61.994 | 62.130 | -1.07% | -0.86% |

| Dataset | Pair | Paired geometric speed ratio [95% interval] | Wins / 4 |
|---|---|---|---:|
| GIST | E/R | 0.997214 [0.996882, 0.997695] | 0 |
| GIST | E/T | 0.988525 [0.988451, 0.988645] | 0 |
| GIST | S/R | 0.999800 [0.999418, 1.000182] | 1 |
| GIST | S/T | 0.991089 [0.990899, 0.991278] | 0 |
| Deep | E/R | 0.993849 [0.993683, 0.994129] | 0 |
| Deep | E/T | 0.988560 [0.988031, 0.989282] | 0 |
| Deep | S/R | 0.998659 [0.998242, 0.999184] | 0 |
| Deep | S/T | 0.993344 [0.992788, 0.993901] | 0 |
| Tloc | E/R | 1.007519 [1.003662, 1.010848] | 4 |
| Tloc | E/T | 1.004665 [1.000088, 1.009013] | 3 |
| Tloc | S/R | 1.012294 [1.007559, 1.015832] | 4 |
| Tloc | S/T | 1.009427 [1.003632, 1.014028] | 4 |

Marginal median ratios and paired geometric ratios are different estimators.
GIST R versus S is close to parity with its interval crossing one; T adds a
repeatable regression. Tloc R wins all four short pairs, but the measured gain
is small. In the longer normal-radius runs, Tloc R remains faster than E but
changes direction against S; T becomes slightly slower than E in both orders.
Thus the short Tloc result does not establish a broadly sustained improvement.

## Why the corrected layouts still do not win

The strongest diagnostic is the restored root-pivot locality. On GIST's first
pruning level, S/U, R/B and T/C each request 1936 L1 sectors and miss on 251;
old L/V requests the same 1936 sectors but misses on 1091. New packing fixes the
old regression without improving on S's original pivot addresses.

The following sums cover the selected first query's two pruning launches:

| Dataset | Stream mode | L1 requested sectors | L1 misses / TEX L2 reads | Warp instructions |
|---|---|---:|---:|---:|
| GIST | D | 18510 | 1656 | 2364001 |
| GIST | U | 18353 | 1616 | 2371216 |
| GIST | V | 10673 | 3176 | 2378401 |
| GIST | B | 18353 | 1616 | 2372426 |
| GIST | C | 18353 | 1616 | 2494786 |
| Deep | D | 2094 | 252 | 239422 |
| Deep | U | 1937 | 212 | 240157 |
| Deep | V | 1169 | 368 | 240862 |
| Deep | B | 1937 | 212 | 240287 |
| Deep | C | 1937 | 212 | 252487 |
| Tloc | D | 133 | 50 | 5108 |
| Tloc | U | 78 | 38 | 5115 |
| Tloc | V | 74 | 38 | 5125 |
| Tloc | B | 76 | 37 | 5122 |
| Tloc | C | 78 | 38 | 5320 |

On GIST, tiled C executes **5.21% more warp instructions than U**, with exactly
the same requested-sector and miss counts. The measured extra instructions are
consistent with additional addressing/control cost; no per-PC causal allocation
is claimed. Its shorter static listing is not less executed work. Compact B
mostly returns to U's traffic, not a new lower-traffic regime.

These are 34-pass NCU kernel-replay diagnostics, first query only, unchanged
clock/cache-control settings, not clean query timing or a 64-query average.
Packing changes setup/cache state. GIST/D reports 256 DRAM read bytes; the other
14 dataset/mode profiles report zero. All selected local load/store sector
counts are zero. These predominantly cache-resident N2000 cases do not establish
million-point DRAM behavior.

All E/S/R/T NSYS traces retain **17 kernels/query** and identical downstream
signatures. Loop CPU/wall remains approximately one CPU core, including result
hashing; this is not sampled attribution of CPU distance work. The unchanged
scalar math and limited query parallelism remain untested optimization targets.

## Setup, sustained scope and correctness

| Dataset | R extra bytes | T extra bytes | Median R layout setup (us) | Median T layout setup (us) |
|---|---:|---:|---:|---:|
| GIST | 43128 | 50808 | 83.437 | 75.310 |
| Deep | 5112 | 5880 | 79.606 | 79.565 |
| Tloc | 976 | 1304 | 399.373 | 401.952 |

Tloc's larger measured setup costs are retained, not trimmed. Adding each process's actual layout,
driver setup and first query to its 512 measured queries gives medians of
**66.699 / 67.099 / 67.539 / 67.756 us/query** for E/S/R/T. This removes the small
hot-query advantage in that accounting. It still excludes construction and
benchmark warmups and is not cold full-application runtime.

All **270 measured receipts** complete: 93 full-output runs, 60 sanitizer runs,
18 stress processes (73728 measured queries), 48 primary processes, 24 normal-only
sustained processes, 12 NSYS and 15 NCU profiles. Full outputs match CPU exact
membership/tolerant distances and native ordered float32 bits; 1536 per-level
cases agree across five pruning variants. New R/T stream and Graph paths pass.
Normal-radius forward/reverse sustained runs use 4096 measured queries/process;
all pass the 5% non-regression tolerance versus both E and S, but that does not
satisfy the primary gain gate. No zero/all-hit long-duration matrix is claimed.

Native E normalized SASS exactly matches the previous campaign. S and L retain
identical instruction bodies, excluding their bool-to-int template function
headers. R uses 48 registers, T 44; both retain the common generic 47528-byte
static stack reservation and zero query shared memory. The unused edit-distance
branch explains why static stack/local sites are not dynamic L2 spills.
See [STATIC_EVIDENCE.json](STATIC_EVIDENCE.json).

Actual median process-monitor gaps are 0.372/0.377/0.391 seconds for GIST/Deep/Tloc;
the maximum is 1.971 seconds. No measured receipt detects interference. This is
sampled safety, not guaranteed exclusive access. GPU 5 was idle at closure.
The earlier GPU-0 prelaunch admission failures are retained and excluded from
measured receipts, not silently replaced measurements.

## Negative-evidence boundary

| Statement | State | Allowed scope / reopen condition |
|---|---|---|
| R/T repair the prior root-locality regression | Measured diagnostic | Selected first-query GIST counters; not lower DRAM traffic. |
| R/T provide a useful high-dimensional query gain | Rejected by screen | These fixed N2000 batch-one mappings only. |
| Tloc has no positive observation | False | Preserve the roughly 1% short hot-query gain and its setup/sustained caveats. |
| Layout optimization cannot help GPU trees | Unknown | Larger trees, different lane ownership and different workloads were not tested. |
| Change scalar math or dimension cooperation next | Recommendation, untested here | Separate correctness/rounding and same-contract performance controls required. |

Do not retune tile sizes to rescue this particular screen. A new experiment needs
a new critical-path hypothesis, such as changed work ownership or a larger
working set. [EVIDENCE.json](EVIDENCE.json) retains every pair, order split,
sustained process, setup cost, profile and receipt hash. [CHECKPOINT.json](CHECKPOINT.json)
identifies the private raw archive; no paper claim or production code was changed.

## Scope

The fixtures contain N=2000 points and 64 fixed query IDs per dataset, with
GIST/Deep/Tloc dimensions 960/96/2. This is a bounded layout screen, not a production dispatcher or a claim about
all GPU trees. It tests whether preserving consecutive coordinates avoids the
prior dimension-major packing's cache-locality regression. No arithmetic,
thread ownership, distance reuse, traversal fusion or precision change is added.

| Graph / stream | Pruning layout | Query-time work |
|---|---|---|
| E / D | Native node fields and pivot addresses | Frozen keeper |
| S / U | SoA pid/lower, original pivot addresses | Metadata-only control |
| L / V | Previous 16-parent dimension-major packing | Correctness/NCU negative control only |
| R / B | Compact [11 parents][D coordinates] | Consecutive coordinates retained |
| T / C | Root separate, then [4-parent tile][8-coordinate block][parent][coordinate] | Root/coordinate-block locality retained |

T pads the root to a multiple of eight floats, child-parent count to 12, and
coordinate blocks to eight. These are fixed choices, not a tuned optimum. Both
new candidates retain S metadata. S/R and S/T attribute packing; E/R and E/T
measure net query benefit. Historical L latency is never reused as a denominator.

The paired denominator is complete hot batch-one query wall time, including
input/output transfers and host completion. Build, layout construction, driver
setup, capture and output hashing are excluded. Setup/first-query costs are
recorded separately. The common driver already uses result fusion and Graph:
this is not a comparison against the wholly untouched GTS executable.

## Reproduction

See [CONTRACT.md](CONTRACT.md) for the frozen fixtures, order, stop rule and scope.
Use a fresh scratch root. Python/NumPy, a C++17 host compiler, CUDA 13.1.115,
compute-sanitizer, NSYS 2025.5.2 and NCU 2025.4.1 are required. No dependency or
GPU setting is installed/changed by these scripts. Fetch pinned author source
separately, and use the source/data roots from the prior layout manifest.

```sh
D=diagnostics/pruning_locality_20260923
export PATH="$CUDA_HOME/bin:$PATH"
python3 "$D/test_cpu.py" --source "$AUTHOR_SOURCE_ROOT"
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$SCRATCH"
python3 diagnostics/pruning_layout_20260923/fixtures.py "$DATASET_ROOT" "$SCRATCH/data"
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/static"
for ds in GIST Deep Tloc; do ln -s ../../bin "$SCRATCH/data/$ds/bin"; done
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 \
 -rdc=true -lineinfo -Xcompiler=-fno-omit-frame-pointer \
 -Xnvlink=--ignore-host-info -Xptxas=-v -Isource/include \
 graph_bench.cu -o bin/graph_bench >logs/build.txt 2>&1)
# Read-only GPU identity record; verify idle physical GPU 5 and its existing lock.
python3 - "$SCRATCH" "$ADMITTED_UUID" "$CUDA_HOME/bin/nvcc" <<'PY_ADMISSION'
import datetime,json,re,subprocess,sys
from pathlib import Path
root,gpu,nvcc=sys.argv[1:]
s=subprocess.check_output(['nvidia-smi','-i',gpu,
 '--query-gpu=index,uuid,name,driver_version,power.limit,compute_cap',
 '--format=csv,noheader'],text=True).strip().split(', ')
assert int(s[0])==5 and s[1]==gpu
assert not subprocess.check_output(['nvidia-smi','-i',gpu,
 '--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
toolkit=subprocess.check_output([nvcc,'--version'],text=True)
x=dict(gpu_index=int(s[0]),gpu_uuid=s[1],gpu_name=s[2],driver=s[3],power_limit=s[4],
 arch='sm_'+s[5].replace('.',''),cuda=re.search(r'V(\d+\.\d+\.\d+)',toolkit).group(1),
 clocks_locked=None,clock_policy='unchanged/uncontrolled',
 verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
Path(root,'logs/admission.json').write_text(json.dumps(x,indent=2)+'\n')
PY_ADMISSION
for stage in full gates stress screen sustained trace; do
 python3 "$SCRATCH/suite.py" "$SCRATCH" "$stage" --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/$stage.txt" 2>&1 || exit 1
done
# Existing counter authorization only; no permission/driver changes.
sudo -n env PATH="$PATH" python3 "$SCRATCH/suite.py" "$SCRATCH" ncu --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/ncu.txt" 2>&1
python3 "$D/summarize.py" "$SCRATCH" "$SUMMARY_JSON" --allow-rebuild
```

For exact historical evidence reconstruction, omit `--allow-rebuild` and use the
archived raw root/binary identified by CHECKPOINT. A fresh compilation can change
the whole-binary hash (including debug/build metadata). The explicit rebuild flag
permits measurement replication but marks a differing binary as awaiting a new
static/SASS audit; it cannot acquire follow-up/promotion status from the historical
static report. All source, fixture, output, safety and measurement checks remain.

The historical run copied hash-identical fixture files from the previous private
campaign rather than rereading million-row source files. The pinned generator
above reproduces them. Failed prelaunch setup/admission logs are retained; no
GPU-0 measurement is included. All selected runs use GPU 5 with its advisory lock.
The lock/process checks cannot prove the absence of unsampled transient activity.

No original author source or production dispatcher is modified. Raw inputs,
process details, machine configuration and profiler dumps are not published.
Generic row-major/AoSoA packing is established engineering, not a novelty claim.
