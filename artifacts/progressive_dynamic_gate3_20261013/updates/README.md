# Bounded update and stage checks

| Checkpoint | after128 (%) | after256 (%) | after512 (%) |
| --- | ---: | ---: | ---: |
| Initial | 65.412818750 | 14.984493750 | 0.807696875 |
| 20I/20D | 65.412843750 | 14.984478125 | 0.807681250 |
| 40I/40D | 65.412659375 | 14.984381250 | 0.807684375 |
| Final | 65.412659375 | 14.984381250 | 0.807684375 |

Means cover the same 32 fixed diagnostic queries, not the 128 A range requests. The A dry process alone adds 128 probes at exact initial/20I20D/40I40D/final points (steps -1/132/300/336). All complete probe members, fields and prefix survivors match independent CPU references. Maximum per-query survivor drift at any prefix is 0.0007 percentage points. There is no repeated-process CI or invented stability threshold for this deterministic description.

Native append/swap-delete/norm updates are unchanged. Formal total ACK ratios stay below 1.5. B and unlimited/capacity-growing updates were not run; the seed-frozen B inputs are not measurements.
