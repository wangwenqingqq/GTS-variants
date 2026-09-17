# Compile-only checks

Date: 2026-09-17. Platform: Linux; CUDA 13.1.115; CMake 3.28.3.

Each source tree was extracted with `git archive` from the exact branch commit below. Only compilation was performed. No resulting executable was launched; no GPU correctness, sanitizer, or timing result is claimed. Compiler warnings are retained in the private audit record.

| Branch | Commit | Build | Result |
|---|---|---|---|
| `variants/archive/GTS_hei_input_fixed` | `27cb21089ab6b25159204e22bde4203f77ee005e` | Existing CMake configuration, Release, two compile jobs | Compile PASS |
| `variants/archive/GTS_incremental` | `2c92590ac11c204f8e0c9d2107026d01bc7baced` | Existing CMake configuration, Release, two compile jobs | Compile PASS |
| `variants/safe_arrival/source` | `34298a67a11afbf318e678392afb5541bd9438c0` | Separate driver; nvcc C++17, O2, RDC, sm_120, include/ | Compile PASS |

All other branches remain **untested historical source snapshots**. Passing compilation does not establish historical binary reproduction, input availability, numerical correctness, update visibility, or performance. The header-only native diagnostic branch intentionally lacks a standalone entry point.
