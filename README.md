# GTS source-variant archive

Private source preservation snapshot, 2026-09-17. This repository is an archive,
not a newly validated release, a performance ranking, or a new contribution claim.

## Branch layout

- `main`: source identity catalog and archive boundaries.
- `variants/<collection>/<directory>`: one branch for every source-bearing
  directory instance captured by the audit, including historical aliases.
- 47 source branches map to 30 source-only bundles and 36 source-plus-build
  payloads. Exact payload aliases share a commit. Identical source with different
  build files remains a different payload. Old binary hashes are provenance only.

The collection names are neutral snapshot labels, not live filesystem paths.
Every branch keeps the source layout at repository root. `SNAPSHOT.json` records
exact archived bytes and aliases. Sources and existing build files are not
algorithmically modified. The separate safe-arrival driver's machine-specific
default dataset path is replaced with `data/sift_base.txt`; original and published
hashes plus the adjustment are disclosed in its manifest. Scripts are stored with
executable Git mode.

## Which branch means what?

| Family | Examples | Meaning / limitation |
|---|---|---|
| Released upstream | `nested_official/GTS` | Original fixed-height source; large-data sentinel failures are not valid fast answers. |
| Local original / dtype | `GTS_ori`, `GTS_float` | Local timing/workspace or dtype variants, not necessarily pristine upstream. |
| Height/input repair | `GTS_hei`, `GTS_hei_input`, `GTS_hei_input_fixed` | Adaptive height and external top-k query support. A fixed label is not an exactness certificate. |
| Pivot/sort/arithmetic | `GTS_fft`, `GTS_sort_opt`, `GTS_hei_input_powopt`, `GTS_pivot_ablation_20260512` | Attributable optimization/ablation attempts. FFT means farthest-first traversal here. |
| Learned pruning | `GTS_lea0`, `GTS_lea1`, `GTS_hei_lea*` | MLP, tuning, or residual/scale pruning. Extra pruning can change recall. |
| Integrated updates | `GTS_hei_lea_ada_input_prune_update`, `GTS_incremental` | Historical workspace/update/direct-insertion implementation. Legacy direct insertion is not a correctness keeper. |
| Deferred updates | `GTS_async_update_0529` | Buffer/rebuild deferral and optional dynamic kNN; the name alone does not establish concurrent rebuild. |
| Metric forks | `GTS_protein`, `GTS_tanimoto` | String capacity or binary-fingerprint distance extensions. |
| Buffer-only closure | `minimal_closure/GTSPP`, `rttide_adapter/GTSPP` | Explicit buffer-only option; default remains legacy behavior. Separate semantic harness included. |
| Safe-arrival prototype | `safe_arrival/source` | Patched headers plus `artifacts/gtspp_gate1_safe_delta.cu`; bounded safety evidence is not a full dynamic guarantee. |
| Native diagnostic headers | `gate0_native/native_gts_src` | Header snapshot used by an external probe; no standalone main/CMake entry in this branch. |

## Known interpretation traps

- `hei` and `hei_random` can have identical source; build-file identity is
  checked separately. A directory name is not evidence of a mechanism.
- The named incremental Tanimoto backup is identical to its incremental parent;
  the actual Tanimoto fork is a different branch.
- Some `fixed` branches retain calibrated pruning. Nonnegative residuals alone
  do not prove sound pruning. C2-off is not an independent exactness oracle.
- Static kNN does not measure direct-insertion update benefits. Keep static,
  approximate, and true-arrival/delete/rebuild experiments separate.
- Result-only directories, old binaries, datasets, notebooks, training dumps,
  credentials, local paths, and unrelated paper/runtime files are not shipped.
- Permission-restricted and unexpanded historical areas are not silently
  represented as complete source captures; exclusions are listed in the catalog.

## Restore and build boundary

Check out the desired branch and inspect its original `CMakeLists.txt` and
`rebuild.sh`. Most branches require CUDA and a suitable C++ compiler. Historical
architecture/toolchain assumptions are intentionally preserved; do not execute
an old experiment launcher blindly. Inputs and calibration assets may need to be
provided separately. `BUILD_CHECKS.md` distinguishes compile-only observations
from untested archive branches. No benchmark or GPU correctness run is implied.

The safe-arrival driver is separate from the ordinary main program. Build it
with the branch's `include/` directory and its recorded CUDA contract, rather
than assuming that the default GTS executable exercises safe admission.

## Provenance and rights

The released GTS source originates from [ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS),
commit `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Preserve the upstream authors'
attribution and rights. No new license is imposed on upstream or derived source.
The inspected upstream snapshot did not include a license file. This private
archive is not a grant of permission to publicly redistribute or relicense it.

## Complete branch catalog

See `VARIANTS.json` for full payload/source/binary identities and exclusions.

| Branch | Source SHA-256 (prefix) | Source/build payload (prefix) |
|---|---|---|
| `variants/archive/GTS_async_update_0529` | `38bd1ff922eb` | `0b81b892e078` |
| `variants/archive/GTS_fft` | `5b495a327e44` | `c319e033c61c` |
| `variants/archive/GTS_float` | `6643cd1768f2` | `7c9de95b2b1e` |
| `variants/archive/GTS_hei_input` | `1a8cccda9497` | `a8ea004ec9a5` |
| `variants/archive/GTS_hei_input_fixed` | `a0bf8f773277` | `bdcfcde04786` |
| `variants/archive/GTS_hei_input_instrument` | `a3618826961f` | `1fa5e05a6c2c` |
| `variants/archive/GTS_hei_input_powopt` | `b1e1e3cdada5` | `34cadf05006a` |
| `variants/archive/GTS_hei_lea_ada` | `e012ca14d7a3` | `e2f7fa3b22cc` |
| `variants/archive/GTS_hei_lea_ada_input_prune` | `7e67cf493119` | `d0b843fd1e52` |
| `variants/archive/GTS_hei_lea_ada_input_prune_fixed` | `b0f545e21f1b` | `0616584f1c12` |
| `variants/archive/GTS_hei_lea_ada_input_prune_update` | `6bd9ce9c9628` | `36690867122c` |
| `variants/archive/GTS_hei_random` | `96a976fc3c59` | `055c4d84c2e8` |
| `variants/archive/GTS_incremental` | `931349ec587e` | `a14bcd2ea2a1` |
| `variants/archive/GTS_incremental.bak_tanimoto_20260601_114814` | `931349ec587e` | `a14bcd2ea2a1` |
| `variants/archive/GTS_lea0` | `5ceb7bd4ee3c` | `038ad4609d9c` |
| `variants/archive/GTS_lea1` | `d943cd23e4c7` | `af0eee9b62a7` |
| `variants/archive/GTS_ori` | `d2bbc99c8e47` | `033633681f42` |
| `variants/archive/GTS_pivot_ablation_20260512` | `e09c8a41be5c` | `19fce7c463a5` |
| `variants/archive/GTS_protein` | `78b2e71b8a0d` | `147ebbf9eca3` |
| `variants/archive/GTS_sort_opt` | `34aad5e44c8b` | `65fee84726ee` |
| `variants/archive/GTS_tanimoto` | `0c84e40d6a24` | `45116eb91d86` |
| `variants/backup4080_data/GTS` | `e481e1d3689f` | `b82bb5331834` |
| `variants/backup4080_data/GTS_hei_input` | `1a8cccda9497` | `aab533ca3171` |
| `variants/backup4080_data/GTS_plus_plus` | `270a97d075d6` | `683d3a125b4e` |
| `variants/backup4080_home/GTS_hei_lea_ada_input_prune_update` | `af59de0cdca6` | `487cfad1c8e6` |
| `variants/backup4080_home/GTS_incremental` | `83c5d412b216` | `43beda61aeb0` |
| `variants/backup4080_home/GTS_ori` | `d2bbc99c8e47` | `de8db4929b2f` |
| `variants/backup4080_second_source/GTS` | `12e9c17af25a` | `9f388e5854d9` |
| `variants/gate0_native/native_gts_src` | `676ae6287be0` | `1f3d33cf22da` |
| `variants/minimal_closure/GTSPP` | `a8c7e05ff9ff` | `20ed522952b6` |
| `variants/nested_official/GTS` | `12e9c17af25a` | `9f388e5854d9` |
| `variants/project/GTS_fft` | `5b495a327e44` | `c319e033c61c` |
| `variants/project/GTS_float` | `6643cd1768f2` | `7c9de95b2b1e` |
| `variants/project/GTS_hei` | `96a976fc3c59` | `5856c32edc89` |
| `variants/project/GTS_hei_input` | `1a8cccda9497` | `d96e05dba76d` |
| `variants/project/GTS_hei_lea` | `2de914557fb5` | `58e2b6525cac` |
| `variants/project/GTS_hei_lea_ada` | `e012ca14d7a3` | `e2f7fa3b22cc` |
| `variants/project/GTS_hei_lea_ada_input` | `7e4429045072` | `1cd8e0324212` |
| `variants/project/GTS_hei_lea_ada_input_prune` | `7e67cf493119` | `e2b60971a875` |
| `variants/project/GTS_hei_random` | `96a976fc3c59` | `055c4d84c2e8` |
| `variants/project/GTS_lea0` | `5ceb7bd4ee3c` | `038ad4609d9c` |
| `variants/project/GTS_lea1` | `d943cd23e4c7` | `af0eee9b62a7` |
| `variants/project/GTS_ori` | `d2bbc99c8e47` | `c58145c7c522` |
| `variants/project/GTS_sort_opt` | `34aad5e44c8b` | `65fee84726ee` |
| `variants/rttide_adapter/GTSPP` | `a8c7e05ff9ff` | `20ed522952b6` |
| `variants/safe_arrival/source` | `8fba88b35f03` | `62a09e10c1ad` |
| `variants/tensorjoin_external/GTS` | `12e9c17af25a` | `9f388e5854d9` |
