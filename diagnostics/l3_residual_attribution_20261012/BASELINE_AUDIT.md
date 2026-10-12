# Baseline audit

The live baseline repository HEAD and public baseline branch were verified as
`955d020a7cf59b12bcc8f210f6da85aa0bb13b6f`. The original host's final closure,
result and raw manifest still match the frozen hashes in `CONTRACT.json`.
The original GPU 1 construction evidence is reused; no GPU process is started
in this task and no device settings or foreign processes are changed.

## Fresh CPU validation

- All 69 selected files: 185,499,494 bytes, independently rehashed.
- 44 structural/process/decision payloads bound to the original 196-file small
  bundle manifest; 20 actual L3 key/order/pivot payloads bound to the full raw
  manifest; five baseline metadata/manifest files retained and pinned.
- PRE order, all native node bytes and empty arrays equal frozen PRE snapshots.
- Complete permutations, node/leaf coverage, native arity, selected pivot
  ownership and actual captured decision occurrence equality checked.
- L3 input/sorted physical-row permutations; finite sorted keys; bitwise
  key-to-row preservation through sorting; per-parent membership closure;
  selected pivot agrees with device pivot-row capture.
- Complete structure-derived C3-versus-PRE result recomputed and exactly equals
  the previous result, not merely its leaf percentages.
- Primary group counts, total churn, L3 retained counts and crossings reconcile
  exactly. Hierarchy-local L4 inventory also reconciles to previous L4 survival.
- A separate read-only audit independently decodes structure and actual L3
  key/order evidence without importing the analysis implementation. Group
  attribution, migration sensitivity, L4 inventory/paired survival, ranks and
  all nine boundaries agree.

## Inherited, not re-tested

The previous full host closure established identical common occurrence FP32
coordinates and bit-exact packed/AoS inversion. Coordinates are **not** read
again here. Only actual L3 scoring evidence is transferred; this task does not
claim a new all-level raw-key validation. The original ten construction processes,
hardware/software calibration and previous negative evidence remain unchanged.

No new native or C3 replay, 336-event service trace, correctness benchmark,
sanitizer/stress, timing, throughput or production admission occurs. Verification
of structure and frozen bytes is not evidence of speedup or query-path quality.

Preparation failures are recorded in a private note, not verbatim tool logs:
local selection initially requested non-existent PRE/C3 `BOUNDARY.json` payloads
from the small bundle. The first successful CPU analysis is retained. No old
evidence was changed. A subsequent audit renamed a zero-valued tie ordinal-position
metric to avoid implying a pairwise inversion count, and added explicit
input-manifest revalidation and descriptive L4 grouping; primary counts and gates
were unchanged.
