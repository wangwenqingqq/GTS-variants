# Active research baseline

- Publication target: `wangwenqingqq/GTS-variants`. `ZJU-DAILY/GTS` is the
  read-only baseline provenance; never push these changes to that upstream.

- Decision on 2026-09-24: use original GTS, not `archive/GTS_incremental`.
- Original source is pinned to `ZJU-DAILY/GTS` commit
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`; verify the eight GTS source
  hashes in `diagnostics/original_tree_redundancy/SOURCE_PINS.json` before use.
- Root `include/` and `src/` remain the historical incremental archive. Do not
  mistake them for the active baseline, delete them, or continue optimizing them.
- New original-GTS workflow work belongs in `diagnostics/original_workflow/`.
  Follow its README and retain prior positive and negative evidence unchanged.
- Keep a byte-identical original baseline. Any correctness/portability repair
  belongs in a separately named variant with an exact diff and independent oracle.
- Static RNN/kNN evidence does not certify mixed insert/delete/rebuild workflows.
- Updated user authorization on 2026-09-24: other idle GPUs may also be used.
  Check current idle/process state and acquire `/tmp/gtspp_gpu{index}.lock` before
  each run; record the physical GPU index/UUID. Do not touch foreign processes or
  change GPU settings. Keep comparisons on the same GPU within each experiment.
- Use standard-library tooling and existing harnesses before adding new machinery.
