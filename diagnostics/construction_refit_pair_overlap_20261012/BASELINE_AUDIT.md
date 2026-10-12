# Baseline and provenance audit

## Frozen target

Parent: `d315215e5186d1fbb0210fe74ed27df1fd8e6483`, current P2 = PAR_STRONG/FULL/TILED/Fixed3. Original keeper binary SHA256: `771f7cf42a23a8e2081f2d2da47d02e747799e9b06dcd4c6e9c0eba093ee0d3c`.

GIST N=1,000,000, D=960, FP32 L2; batch 1, K=8, radius=0.705625057220459; 336 events (40 insert, 40 delete, 128 range, 128 KNN). No parameter or dataset change. The exact data/trace hashes and historical GPU provenance are in `CONTRACT.json`. Historical capture GPU: RTX PRO 6000 Blackwell, SM120, GPU1, driver 590.48.01, CUDA 13.1.115. These are capture provenance, **not current host availability claims**.

## Existing captures, not a new observer replay

1. The original rebuild-change-amplification observer captured the actual POST_R1/POST_R2 base occurrence mapping, tree, order, empty flags, numeric bounds, metadata and dynamic work counts. Its ordered IDs/FP32 result fields/final occurrence set matched P2, and the trigger steps were 48 and 216. The inherited quality receipt reports 256 queries/54,614 output items/final live count 1,000,000.
2. Earlier native C0 construction replays captured all five scoring/sort/split stages. C0 dose=0 performs no forced pivot selection; the causal replay has an optional selected-pivot load, so it is **not claimed to be the unchanged keeper binary**. Native gate checks show its entire final `nodes.bin`, `order.i32`, `empty.i32` byte-identical to the corresponding original POST capture. This task rechecks those bytes, all recorded decisions, selected pivot rows, sorted key association and canonical memberships.
3. C0 standalone replays did **not** invoke refit. Refit pairs are reconstructed separately from original production POST tree/order and the pinned `numeric.cuh` loop. Original lo/hi are aggregate node extrema, not per-pair interval outputs.
4. All 132 full C0 build-capture files fetched for this task matched the earlier causal raw manifest by size and SHA256. Original POST input files matched the earlier production snapshot manifest. All 25 frozen keeper source files matched the recorded source audit. The current input manifest pins 190 files in total.

The CPU fetch read existing task-owned captures over the already configured SSH route; it did not create a process on any GPU, alter shared service state, or write old evidence. No new instrumentation was needed, so no new GPU output-equivalence gate is claimed. This task establishes evidence integrity and CPU pair reconstruction; it does not newly execute sanitizers, performance controls or the P2 service.

## Count admission

For each rebuild, source-exact enumeration uses actual split flags, node lids/sizes, recorded launch tile widths and 512-thread geometry. Counts must equal both POST metadata and earlier source-derived work: 5,000,000 scoring tasks, 11,111 active splits × 10 = 111,110 boundary tasks, 5,000,000 valid-node refit tasks. Root pid=-1 launches a block but performs no distance work. Count mismatch aborts before promotion.

Raw capture archive SHA256: `9654489014414294b4c1f6a5d93bd3c88ca100f36a70cc034b7b0f0b0d9a1fd0`. Full public manifests retain relative names only; private host paths and process commands are not part of the publish set.
