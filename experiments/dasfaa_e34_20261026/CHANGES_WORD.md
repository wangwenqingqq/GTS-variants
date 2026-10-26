# Word preparation and gates

## Changes

- Preserve seed 20261026 and the fixed source-row permutation. Record exact-string query/index overlap for every requested prefix; overlapping loads are blocked rather than resampled. Keep N=611000 visible as infeasible when holding out 1000 of 611756 source rows.
- Validate packed input dimensions, payload size, and every string length against stride 109. Preparation refuses to replace prior frozen artifacts.
- The exhaustive CPU oracle uses a per-call fixed-size row instead of allocating a vector for every distance. It caps OpenMP at 32 threads and publishes only completed outputs without replacement.
- Add a complete-output tie-aware audit whose candidate distance checks use independent full-table Python DP. It validates oracle payload, ID range/distinctness, candidate distances, and optional exact expected output count.
- Keep the existing rolling-row GPU scan, Q tile 32, and CuPy top-k. Validate int32/length bounds; perform excluded correctness before excluded warmup. No native-library label is used for this custom edit scan.
- The Word P harness leaves the archived query/search kernels unchanged. It appends input queries beyond the N indexed IDs, disables unkeyed legacy cache reuse, rejects N>10M, reports tree height/build time, and does not call search at height >=8. Corrected search headers must come from the separate patched build.

## Local validation

```sh
python3 test_word.py
```

The CPU-only smoke compiles `edit_oracle.cpp`, compares exhaustive top-10 against independent full-table Python DP on deterministic varied strings, and covers length 108, empty strings, ties, invalid/duplicate IDs, truncation, exact-value overlap, fixed permutation, immutable preparation, and Q1024 output wrapping.

## Remaining gates

No real Word dataset, CUDA compilation, GPU result, sanitizer, or timing has been verified by this local smoke. Before GPU execution, freeze and inspect the actual Word manifest, reject any exact-value overlap, compile against the corrected P header, run guarded CPU oracles, and pass memcheck/synccheck plus all-output audits. Call `audit(..., expected_rows=1024)` for Q1024 and `expected_rows=1000` for Q1/Q32. The scan's logical byte field describes padded input storage, not measured DRAM traffic. The `unused_cache` CLI argument is retained for runner compatibility; no Word cache is read or written.

## Byte-preserving source-parser correction

The first guarded real-source preparation failed before writing artifacts: the source contains byte `0x8e`, so decoding the entire file as ASCII was invalid. The source hash remains unchanged. The preparation loader now reads raw bytes and matches the archived `file.cuh` loader exactly: split only on LF as `std::getline` does, preserve CR and all bytes >=128, and use the prefix before the first NUL as the indexed object, matching native `strlen`. It records counts of non-ASCII and embedded-NUL source rows. No UTF-8 error suppression, replacement, stripping, or normalization is performed; the fixed permutation is unchanged. Packed strings, the CPU oracle, the GPU recurrence, and the independent auditor all compare byte values using explicit lengths. Local smoke now includes `0x8e`, `0xff`, embedded-NUL packed content, CR preservation, and the native source-NUL prefix boundary. This fixes input parsing, not a GPU result; real-data isolation and GPU gates remain unverified by the local smoke.
