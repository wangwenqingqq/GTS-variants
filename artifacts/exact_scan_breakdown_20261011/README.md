# Exact scan roofline / breakdown — diagnostic campaign

**Decision: MEMORY_BOUND, not near roofline. No new optimization or paper claim.**
See [DECISION](DECISION.md), [numeric results](RESULTS.md),
[claim–evidence ledger](CLAIM_EVIDENCE.md), and [figure captions](figures/CAPTIONS.md).
The plan is dated 2026-10-11; GPU measurement/closure occurred 2026-10-12.

## Coverage

GIST 1M/D960 FP32 L2 B1, 32 original range queries; six fresh native-keeper runs,
six forward/reverse rounds of four controls, D128/256/512/960, N100K/250K/500K/1M,
three frozen radii, native D2D streaming calibration, fixed336-event E_ADAPT
workflow, independent NSYS/NCU, and one ordered-FP64 matched reference. 106 starts:
105 valid processes plus one retained pre-CUDA launch failure; budget 110.
The L2 supplement's two-bucket interpretation was rejected and corrected offline,
without replacing its valid raw capture. No prior successful sample is rerun.

## Safety and semantics

- One authorized idle single device and matching NUMA binding, frozen privately
  for the campaign. Observe clocks/power only. Reuse the two-sided-starttime guard;
  no foreign process signal or GPU setting mutation.
- cuVS 26.8.1 L2Unexpanded, FP32 stored/squared values, complete IDs/FP32 Euclidean
  fields and charged FP64 cast observer. Exact complete membership against full
  ordered-FP64 scores on tested inputs; native field scale tolerance 5e-5.
- READ_ONLY is a diagnostic float4 checksum/reduction, not a production scan.
  Unprofiled FULL_OUTPUT calls unchanged Scan::range. Original six-process keeper
  remains a separate denominator. All setup/context/warmup/teardown scopes retained.
- Calibration is uniform 8 holdouts, seed 2026101112, disjoint from original 32.
  Intended output targets are not attained and never retuned after timing.
- Profiler duration and executed FLOPs are diagnostic only. CUDA-event D2D bytes
  count both read and write. Logical payload, DRAM traffic and L2 requests differ.
- No new compression, Tensor Core, tree, certificate or persistent prototype;
  no 100k/1B inference, external comparator refresh or manuscript upload.

## Reproduce analysis without a GPU

With Python3 and NumPy already available:

```bash
python3 report.py --artifact .
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 audit.py --artifact .
```

Plotting uses an existing matplotlib environment and the user's installed
paper-figures helper, not copied managed skill code:

```bash
AGENTS_SKILLS_HOME="$HOME/.agents/skills" python3 report.py --artifact . --figures
```

The delivery rendered all 5 charts to PDF/SVG/PNG, inspected print-size and
high-resolution previews, and audited PDF font types. The paper itself was not
compiled or edited.

## Reproduce a new measurement campaign

This is a pinned campaign recipe, **not a standalone self-contained AE package**.
Use the existing qualified original native static/E builds, original input and
full ordered-FP64 reference manifests from the adjacent external_closure and
unified_target_workflow recipes. Large vectors, complete-ID/field payloads,
full score arrays, profilers and vendor code stay outside Git with hashes;
regenerate or locate them before admission. Paths and device identities are
runtime parameters; do not copy another host's credentials/configuration.

1. Run `prepare.py --help` and provide a fresh external work directory plus
   qualified input/reference/CPU-library/native-build directories. Exact baseline
   build/library/input pins are intentional, not portable auto-discovery.
   A **fresh active-contract** preparation writes PREPARED and READY directly.
2. `calibrate.py --original-contract ...` is only for archival R0→R1 repair.
   It needs the exact private raw R0 contract, not this curated CONTRACT_R0.
   Do not run it after fresh active-contract preparation or modify old records.
3. Use `campaign.py --stage qualification|keeper|primary|scaling|dynamic` with
   explicit GPU, NUMA, work, READY, trace and dynamic-reference parameters.
   Use `profile.py --stage nsys_static|ncu|nsys_dynamic` for independent captures.
   Order: qualification → keeper → static NSYS/NCU → primary → scaling → frozen
   STATIC_DECISION → dynamic → dynamic NSYS. First runtime/isolation/quality/
   provenance failure stops; no automatic retry or favorable-sample replacement.
4. `build_matched.py` generates the unchanged parent prefix into private support
   before building matched.cu. `run_matched.py` preserves the historical failed
   attempt and requires registered recovery; it sets BUILD_MAPPING=TILED plus
   original PAR_STRONG/FULL/non-observer environment. It is not an automatic
   recovery mechanism. The historical numeric reference is one process only.
5. The independently authorized L2 capture is in `l2_supplement.py`. Its retained
   original two-bucket assumption can fail on Other sectors; after runtime/output
   qualification, `l2_finalize.py` performs the explicit offline three-bucket
   interpretation. Never rerun the GPU just to change an analysis assumption.
6. `analyze_stats.py`, `analyze_dynamic.py`, `timeline.py`, `forensic.py` and
   `curate.py` transform external raw evidence. Curate only whitelisted scalars,
   receipts and hashes; keep raw sources and failed attempts immutable/private.

## Publication boundary

Public CONTRACT files parameterize only placement prose; they are **not the raw
executed registration bytes**. PROVENANCE records raw R0/R1 and curated hashes.
CUDA diagnostic bodies are unchanged from measured source; Python archival
calibration gains an explicit raw-contract argument; the delivered L2 helper gains
a required NUMA parameter. The curator generates the contract/hash bridge. Raw before/after device
identity, active-user observations, absolute deployment paths, original commands,
full vendor SASS/reports and data arrays are not published. This public existing
repository retains visibility/history; it is not an anonymous submission artifact.
