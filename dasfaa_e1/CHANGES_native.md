# Native adapter review and diagnostic provenance

## Changes

- Preserve the documented archival range-update adapter. Its kNN radius comes
  from k live objects, not from the oracle; all candidate return, CPU distance
  recomputation and host selection remain inside operation time. The retained
  executable is diagnostic-only, not decision-grade native-kNN timing.
- Derive static `search_v2.cuh` copies from exact pinned P/G originals and the
  mandated correctness patches. Exact source, patch and resulting hashes are
  retained; zero fuzzy patching is allowed. This source is **not executed** by
  the range-update adapter. A provenance patch is not a range correctness gate.
- Retain the archival G allocator-heavy range update versus P persistent
  workspace and single-query collection. No new P-only optimization was added.
- Add full native tree-range candidate IDs, radius and consolidation boundary
  to diagnostic query JSONL, for a separate independent full-output range audit.
- Write the actual binary PID to `<output-prefix>.pid`, enforce the 10M cap,
  and reject native int32 row/dimension indexing overflow before allocation.
- Build manifests record original/derived/adapter source and binary hashes,
  executed API and non-execution of the retained static kNN source.

## Source review

Deletion in range leaves now maps compacted physical IDs through the stable-ID
map before reading the authoritative bitmap. Rebuild compacts live rows and
keeps the same external IDs. Insert never modifies native metadata. The safe
radius includes live delta objects if they are among the k seed objects; this
is valid because any k live objects bound global kth distance from above.
Tanimoto is an explicit interface extension for the original G arm.

Native splits create nine floor(N/10) children and a residual final child.
The worst-child height recurrence is a structural safety adaptation: it prevents
native leaf sizes from exceeding the `MAX_SIZE` query row stride. The wrapper
additionally audits every built leaf. The original ideal log10 height can fail
at residual boundaries (for example N=19,999 at maximum height 4).

## Validation

Local static smoke tests cover exact patches, mutated-context rejection,
deterministic derivation, archive byte preservation, stable bitmap addressing,
all-metric branch coverage, residual-child height bounds, PID and resource
preflight guards. These do **not** establish CUDA compilation, sanitizer success,
full native range correctness, or timing validity.

Run locally:

```sh
python3 dasfaa_e1/prepare_native.py
python3 -m unittest discover -s dasfaa_e1/tests -v
python3 dasfaa_e1/check_no_direct_insert.py
bash -n dasfaa_e1/build.sh
```

The campaign owner must run GPU build/sanitizer/smoke only through its guarded,
locked runner on one admitted device. Example binary child command (wrapped by
that runner; never launch this directly):

```sh
CUDA_VISIBLE_DEVICES=<admitted-UUID> bin/P <case.bin> P 300 <output-prefix> 30
```

## Remaining limits

- Native static kNN is not exercised by the range adapter. A direct kNN adapter
  needs proper stable-ID output and deletion-aware pivot upper bounds; merely
  filtering returned dead IDs is not sufficient.
- Full range candidate audit is distinct from top-k output audit, and final
  query-before-insert range semantics/calibration remain separate work.
- SIFT-50K historic stop is not proven by a hypothetical compacted-ID probe.
  Existing archived trace audit and expected-failure probe are causal leads,
  not a literal replay or final attribution.
