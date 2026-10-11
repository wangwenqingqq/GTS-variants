# Measurement identity versus public replay view

The exact executed CONTRACT.json and recipe remain immutable in the private raw
archive. The public contract is explicitly a UUID-redacted view, bound to that
original by SHA256. All workload, arithmetic, shape, ordering, timer, process
budget and acceptance fields are unchanged. The public runner compares the
injected UUID's SHA256 against the frozen binding; it also accepts the private
raw UUID binding for original-recipe reproduction. This is a disclosure-only
change, not a different GPU admission or new measurement.

The public generator additionally tightens its future replay parser to match
the exact selected-function ptxas property block and assert spill stores/loads.
RESOURCE_GATE.json independently verifies every actual measured build's selected
block: all nine have zero stack, spill stores, spill loads and local memory,
3840 user shared bytes, and the inherited 4864 cuobjdump bytes. No CUDA kernel,
binary, collection order, or sample was recompiled/replaced for this parser fix.
The measurement-side source hashes and release-side hashes are kept distinct.

AMENDMENT_2.md also documents the separate measured continuation after the
mutable-log bookkeeping failure. The public fresh runner now whitelists only
real inputs, excluding outer captures. This release-side repair does not
replace the archived first controller or any sample; the separately archived
continuation collected only the original remaining budget after offline gates.
