# Reproduction and evidence boundaries

## CPU structure

Use ordinary Python with an already installed NumPy. No new dependency or
benchmark framework is installed. From this artifact directory, create only new
output paths:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 test_replay.py --out /new/private/replay_fixtures
PYTHONDONTWRITEBYTECODE=1 python3 test_boundaries.py --out /new/private/boundary_fixtures
PYTHONDONTWRITEBYTECODE=1 python3 test_bind.py --out /new/private/closure_fixtures
python3 fetch.py --out /new/private/upstream
python3 replay.py \
  --runbook /new/private/upstream/bigann/neurips23/runbooks/wikipedia-1M_expiration_time_runbook.yaml \
  --out /new/private/replays/wikipedia-1M_expiration_time_runbook
```

Repeat for the other two pinned runbooks without editing their operation order,
ranges or stable-tag replacement semantics. `replay.py` is a strict parser for
these pinned flat scalar files, not a general YAML implementation. Parent output
directories must already exist; final output directories must not.

`capture.py --out /new/private/capture` requests the frozen historical CMS hour
and stores only six metadata fields. The first 500 events in R1 came from a
retained reachability probe, before computing statistics. Subsequent pages obeyed
the registered cap. All nine raw pages and the normalized record are bound.
Historical recentchanges retention is finite; a later fetch may be unavailable
or changed. The privately preserved original, not a refreshed API result, is the
source for this campaign. No public full reproduction of that private record is
implied by its hash manifest.

## CPU planning, not ACK

`cost.py prepare --replays /new/private/replays --out /new/private/inputs`
serializes only the two deletion-bearing 512-subplan sets. The actual compiled
source uses the unchanged parent generic planner and BatchPlan wave builder.
It deliberately rejects cases with conflicts/elimination; it is a diagnostic
for these registered controls, not a general prospective timing harness.

```sh
c++ -std=c++17 -O2 \
  -I../dependency_update_mechanism_20261017 -I../ownership_safe_gpu_update_20261015 \
  cpu_cost.cpp -o /new/private/cpu_cost
taskset -c <selected_core> /new/private/cpu_cost <cases.bin> <round_0_to_5> <new.csv>
```

Use six independent processes per input and both planners interleaved per batch,
forward/reverse by round parity. The measured denominator is CPU plan construction
plus destruction. The final-plan nonalias certificate is included. Signature computation is excluded;
logical replay, raw-input/lifecycle validation,
input I/O, payload copying, metadata H2D, synchronization, Query/Update ACK and
release of an actual service are not part of it. Host allocator scratch peak and
all device/complete-service costs remain UNKNOWN. This is not a substitute for a
same-contract, same-compiler CUDA campaign.

## Admission is stronger than parsing a CSV

`cost.py analyze` is a diagnostic parser, not campaign admission by itself.
`bind.py` additionally requires the frozen contracts/source/input identities,
exact twelve start/command/exit/output receipts, and the complete physical raw
file census. It regenerates all three logical replays and both binary input sets,
recomputes CMS statistics and CPU tables, and recompiles the diagnostic binary
identically before sealing. Tampered self-reported input hashes or a failed
process with a complete CSV are not accepted.

The archived proof binds the actual executed v1 checker. The public checker
replaces its embedded placement with the CPU core from the hash-bound private
BUILD receipt; all other reference sources remain unchanged. Its explicit
archived-reference bridge verifies the original proof SHA and reference set.
The original checker/proof remain immutable in the private archive. The public
checker is then tested against the sealed original without a timed target.

The historical checker is bound to the original registered command paths and
GCC13.3 environment. Run it on the retained registered work root, not by blindly
rewriting paths after relocation. A fresh replay/timing registration is distinct
from admission of the old measurements. Checker sources/reference anchors were
captured **after** measurement, explicitly, rather than called pre-target
signatures. Compiler version and binary identity are recorded; pre-process
runtime-library hashes/mappings are not claimed.

## Preservation and publication

One transfer preflight failed before compilation or any registered CPU target:
macOS tar emitted 102 AppleDouble sidecars, so exact file census rejected it.
All intended payload hashes matched. That transfer was retained; a separate new
portable-whitelist snapshot passed without overwriting or deleting old files.
All twelve CPU targets then passed with no failed target or retry. No GPU was
launched. Unit fixtures intentionally exercise rejected inputs without modifying
actual measurements.

The private archive contains sealed raw observations, the actual checker snapshot
and transfer failure record. Every member was size/SHA-verified remotely and
again locally. Independent regenerated duplicates also remain on the host.
Git contains curated scalar results, complete readable batch/call tables, hashes
and code only. Raw CMS records, large vectors, upstream source copies, private
commands/host registrations, credentials and manuscript files are excluded.
