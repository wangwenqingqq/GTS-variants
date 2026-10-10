# Frozen tree-pruning diagnosis

Read [TREE_PRUNING_VALUE.md](TREE_PRUNING_VALUE.md) for the two evidence tables,
one selected research boundary, costs and counterevidence. This directory adds
no production variant or default. It reuses the qualified parent's kernels.

## Reproduction boundaries

Python3 + NumPy, the existing CUDA13.1/sm_120 environment and private benchmark
inputs are required; no new dependencies. Raw output must be outside Git.
The qualified parent and registered input/reference/audit manifests are explicit
arguments; their hashes are in the public proof. Private paths, GPU UUIDs and
vectors are deliberately not embedded in this repository.

1. Run `python3 artifacts/external_closure/pruning_value/test_pruning.py`.
2. `build.py --parent "$QUALIFIED_P_BUILD" --output "$PRIVATE_NEW_BUILD"`
   includes the exact unchanged generated parent source, preserving original
   kernels; capture additionally enables the existing observation counters.
3. `run.py --work "$PRIVATE_NEW_RUN" --inputs "$REGISTERED_INPUTS"`
   `--references "$REFERENCE_ROOT" --audits "$AUDIT_ROOT" --build "$BUILD"`
   `--guard "$STATIC_GUARD" --gpu "$ADMITTED_GPU_UUID" --numa "$ADMITTED_NUMA"`
   requires a fresh, separately authorized campaign. It is **not a resume tool**.
   It stops on failure and never retries admitted samples. The 11th build-only
   supplement requires its own prelaunch record; it is not silently dispatched.
4. `maintenance.py prepare/analyze --help` replays existing logical updates and
   binds actual tree dumps. `analyze.py` checks every ID/field, builds masks from
   actual traversal, and never uses true-hit IDs as replay candidates.
5. `final_proof.py --help` verifies this preserved campaign's precise directory
   layout and execution history, including the preferred-card pre-admission stop and the
   separately registered idle-card run. It is a historical reconciler, not an acceptance script for arbitrary new
   layouts or runs. Do not fabricate historical records for future experiments.
6. `curate.py --raw "$PRIVATE_COMPLETE_EVIDENCE" --campaign "$PRIVATE_RUN"`
   `--output "$NEW_PUBLIC_STAGING"`
   exports only explicit tables, metadata and hash manifests. Independently audit
   staging before copying its contents into `evidence/` or publishing.
7. `python3 artifacts/external_closure/pruning_value/report.py` regenerates the
   report from curated evidence. The exact public manifest must verify first.

GPU kernels, Host-ready query timing, observer intervals, offline truth and
maintenance counts are separate evidence gates. Replay and static source/SASS
identity do not establish end-to-end acceleration. No Graph, long-duration
stress, new NCU traffic measurement or deployment promotion is claimed.
