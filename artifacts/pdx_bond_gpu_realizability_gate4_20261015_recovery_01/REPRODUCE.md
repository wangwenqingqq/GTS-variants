# Reproduction boundaries

Run from the repository root. Every output directory below must be fresh.
Use Python without `-O`, set `PYTHONDONTWRITEBYTECODE=1`, and retain stdout and
the verification receipt. No command in the public verification path invokes
CUDA or reruns the 32M CPU population.

## 1. Public scalar/source verification

Python 3.9+ and NumPy are required; no new framework or installation is needed.
The measured server used NumPy 1.26.4. Cross-platform transcendental/bootstrap
reconstruction allows 1e-12 roundoff; integer identities and file hashes remain
exact. Set `REPO` to the checkout root and `OUT` outside this artifact folder:

```sh
REPO=$(pwd)
BUNDLE="$REPO/artifacts/pdx_bond_gpu_realizability_gate4_20261015_recovery_01"
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/verify.py" --repo "$REPO" --out "$OUT"
```

This checks the exact publication whitelist, unchanged 47-file CPU checkpoint,
executed source/dependency hashes, identical generated CUDA headers/fixtures,
all 384 primary per-query ACK samples, frozen statistics/gray-zone checks,
all 832 captured kernels and family/query sums, 26 quality/guard receipt
bindings, static resources, source model and final decision. It does **not**
recompute raw membership, private authority scores, isolation observations,
or SASS; those were validated by the executed private curator, not proven
independently by hash matching. Run this path from `git archive HEAD` for a
clean committed-tree check, without unrelated untracked caches.

## 2. Figure regeneration

Use an installed Matplotlib runtime and a separately installed plotting helper;
its managed source is not redistributed in this repository. `STYLE_ROOT` is
the directory containing `paper_style.py` (the helper is external and unpinned;
there is no promise of byte-identical PDF metadata across runtimes). The
included `figures/*.csv` and underlying JSON are the portable numeric contract.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/plot.py" \
  --data "$BUNDLE" --out "$FIGURE_OUT" --style-root "$STYLE_ROOT"
```

Outputs are 3.5-inch PDF/SVG/400-DPI PNG plus CSV. Latency is median with p10–p90
of six process means and individual means; it is not a 95% CI. DRAM is one
NCU-process mean/mode with no repeated-process uncertainty invented. The first
two planned logical/source figures are retained in the prior immutable CPU
checkpoint; its `plot.py` reproduces them. The source/model and measured-DRAM
figures must not be conflated.

## 3. Private raw revalidation (no GPU execution)

The private archive's hash/size and every relative member identity are in
`evidence/CUSTODY.json` and `evidence/RAW_MANIFEST.json`. After safe extraction
to a fresh directory, verify the archive SHA256, then each `work_r1/<relative>`
member against the manifest (1,707 files). No data vectors are in that archive.
The full private curator also needs the frozen source snapshot, original
GIST1M input, original ordered-FP64 references, CPU crossing arrays and prior
keeper registration. Those private paths must be bound explicitly. The data,
mean, reference, binary, generated source and dependency hashes are published
in `INPUT_IDENTITY.json`/`GPU_CONTRACT.json`; hashes alone cannot restore files.

With those preserved parent locations available, the original executed flow is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$BUNDLE/curate.py" \
  --work "$PRIVATE_GPU_WORK" --out "$PRIVATE_CURATED_OUT"
```

It does not execute CUDA. It asserts original absolute registrations and every
raw output/field/checkpoint/guard/source identity. The run-specific absolute
source references must still exist; rebasing them produces a new registration
and is **not** represented as byte-identical historical revalidation. This
is not a self-contained redistributable GPU benchmark or an anonymous bundle.

## 4. Fresh GPU campaign (not launched by verification)

Do not blindly replay the completed work directories. A fresh run requires a
new frozen registration/plan, verified same-model idle card and libraries,
all private parent inputs, source identity, quality gates and budget. The
source preparation entry point takes `--repo`, `--parent` (preserved Gate2
work), `--cpu` (Gate4 CPU work), `--work` (new path), and `--gpu` (admitted card).

Preserved controller sequence was `static`, `qualification`, `primary`,
`ncu`, `breakdown`; only `ncu` uses **gpu_campaign_ncu.py**. The original
`gpu_campaign.py` is retained byte-identically and has an obsolete NCU route;
do not use it for NCU. The dedicated NCU-only executor uses absolute
`/usr/bin/sudo`, forwards the frozen mean file, preserves the 26-start budget,
and binds its executor hash. The scope is documented in NCU_ROUTE_PREFLIGHT.
Both binaries/generated headers were unchanged by that frontend repair.

The original 6×2 primary order was K/B, B/K, K/B, B/K, K/B, B/K. Each process
executes 8 warmups then 32 measured queries. The executed CPU admission,
failed preflight and final recovery remain separate immutable checkpoints;
there is no automatic retry, baseline substitution or cherry-picking.
