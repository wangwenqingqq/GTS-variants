# Byte and cost boundary

| Item | B0 | O1 | C1 |
|---|---:|---:|---:|
| Nominal selected exact-coordinate payload/object | 512 B | 512 B, diagnostic only | 512 B |
| Actual logical coordinates read by oracle process/object | Shared with O1's 3840 B scan | 3840 B | Not used by the probe |
| Logical coordinates read by probe/object | — | — | 512 B |
| Persistent dataset moments | 0 | 0 | 7680 B |
| Query-specific selected-index array | Fixed indices | Unpriced pair selector | 256 B/query |
| Full FP32 query | 3840 B/query | 3840 B/query | 3840 B/query |
| Dataset-statistics preprocessing | None | None | 2 passes, 7.68 GB logical input |
| Query score / priority work | None | Per-pair 960-term selection, unpriced | 960 moment scores and one stable top128 selection/query |
| Measured physical DRAM / GPU latency | NOT_RUN | NOT_RUN | NOT_RUN |

One decimal MB is 1,000,000 B. Proof yield is strict non-hit rejections divided
by **nominal selected payload**, excluding the separately listed costs. O1's
yield is an information ceiling, not an implementable bandwidth efficiency.
B1 retains the historical 480 B/object result, explicitly not remeasured here.

The unchanged database remains row-major. C1's selected coordinates are generally
noncontiguous: cache lines/sectors, prefetch, compaction, masks, output, launches,
and any GPU layout conversion may add traffic. A nominal 512 B of useful values
does **not** prove a 512 B physical transfer or less end-to-end time. Nothing in
this CPU experiment measures those costs or assumes them to be zero.

The native O1 diagnostic retains two 960-element FP64 temporary arrays per worker
(15360 B), before other local variables. Raw proof arrays are validation-only:
512 MB for B0/O1 partials and 256 MB for C1 partials. Frozen full scores remain
external validation inputs. Operational population wall times include admission,
build, qualification, hashing and evidence export; they are not search timings.
