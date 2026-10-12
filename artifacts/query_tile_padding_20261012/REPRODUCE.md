# Reproduction boundaries

This is a pinned continuation of the exact-scan campaign at518d846, not a
portable replacement for that campaign's native library or data. No dependency,
GPU setting, heuristic or device kernel change is required or permitted.

## CPU checks and scalar reanalysis

From this artifact directory, with Python + NumPy:

```sh
python3 -m unittest test_contract test_analysis -v
python3 verify.py
```

`verify.py` checks the exact publication whitelist/hashes, all frozen measurement
sources (including original shared harness), process schedule and model verdict
against published raw scalar samples. It does not masquerade as a new GPU run.

## GPU reproduction

Required externally: the original pinned GIST binary, complete original
exact-scan work directory (CPU oracle and32 full ordered-FP64 references), native
static build registration and immutable native keeper, exact resolved libraries,
the same admitted physical device/NUMA, and an empty external work directory.
Data/keeper/oracle/library hashes are in evidence/INPUT_IDENTITY.json. No vectors,
vendor reports or private deployment details are distributed here.

Set the placement variables on the destination host; do not store them in Git:

```sh
python3 prepare.py --work "$WORK" --previous "$PREVIOUS" \
  --static-build "$STATIC_BUILD" --gpu "$GPU_UUID" --numa "$NUMA"
for stage in qualification keeper primary ncu; do
  python3 campaign.py --work "$WORK" --stage "$stage" \
    --gpu "$GPU_UUID" --numa "$NUMA" || exit 1
done
python3 analyze.py --work "$WORK" --output "$ANALYSIS"
python3 curate.py --work "$WORK" --output "$CURATED"
```

All work/analysis/curation directories must be fresh and external. Sources are
pinned before GPU execution; every prior stage is fully reverified before the
next. No automatic recovery, replacement or retry is provided. First failure
retains the evidence and requires separately authorized recovery. Initial CPU
allocation registration requires the same device identifier form as the prior
registration; the preserved preflight attempt demonstrates why UUID is used.

The NCU command uses existing passwordless administrative permission only to
collect counters; no permission/GPU settings are changed. Shared guard ownership
excludes foreign processes and protects only its own child process group.

## Reporting and figures

Copy the curated scalar receipts into evidence/, with PROCESS_SAMPLES.json under
timing/. On a reporting host with existing matplotlib/NumPy and the user-owned
paper-figures skill:

```sh
python3 report.py --analysis "$ANALYSIS" --artifact "$ARTIFACT" \
  --figure-skill "$FIGURE_SKILL"
```

Analysis/report code was written before viewing counters but is not part of the
frozen measurement source set; it cannot change measured queries, binary or
launches. JSON contains exact scalars; table/figure display rounding is separate.
PDF/SVG are vector, PNG is a300dpi preview. Inspect whole figures and high-DPI
crops, check final-size labels and embedded fonts. Publication manifest excludes
itself; raw hashes identify evidence, not an assertion that raw data is in Git.
