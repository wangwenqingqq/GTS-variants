# Native kNN / IVF comparison

- Use pinned original GTS, not the root historical incremental implementation.
- Select an idle single GPU after live process checks and advisory-lock admission;
  GPU0 is not mandatory. Do not touch foreign jobs or alter GPU settings.
- Keep the original source unchanged. Only the separate documented observation
  adapter may expose full neighbor IDs and configure sufficient tree capacity.
- Freeze data, query sets, K, batch size, ID quality, output/timing scope and IVF
  parameters before final measurement. No final-query parameter tuning.
- Compare native GPU IVF kNN with kNN. A custom full-scan range executor is not a
  native IVF range baseline; range output truncation is not kNN Recall@K.
- Preserve failed runs, source/receipt hashes, raw order and unmet quality anchors.
- Do not publish same-quality ratios if either method misses that final anchor.
