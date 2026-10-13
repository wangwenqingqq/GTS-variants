# M1 cheap kill — CPU-only sector model

Use the installed keeper source and frozen Gate2 integer survivor counts. Enumerate
the32 lane addresses for every loop position in all four stages, for every
possible row residue modulo the sector period. Count unique32B sectors; compare
with useful FP32 bytes. The cudaMalloc database begins aligned; the12B input file
header is not part of the device allocation. Original row IDs can be arbitrary
after stable compaction or swap-delete without changing their alignment.

Primary kill: modeled **coordinate transaction** saving <20% -> KILL_M1.
Also give a generous accounting sensitivity: pretend all state/ID/padding/flag
payload and ordered rereads disappear; divide this saving by the full modeled
payload. Use old all-kernel NCU only as a separate historical consistency check,
not a newly measured candidate and not a universal compulsory-DRAM lower bound.

No CUDA launch, alternative layout binary, latency measurement or new NCU capture.
Do not report the address-model result as measured DRAM or an E2E speedup.
