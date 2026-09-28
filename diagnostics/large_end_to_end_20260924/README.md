# Large-L2 five-mode end-to-end ledger

This directory contains the fixed experiment contract, stage generator,
independent full-output verifier, offline audit and report renderer for the
GIST/Deep/Tloc `N=65536` and `N=1000000` A/B/C/D/E comparison. Mode definitions
and the exact timed boundary are in `CONTRACT.md`. The immutable plan and hashes
are in `PREREGISTRATION.json`.

The campaign reuses the byte-identical benchmark executable and immutable
fixtures from `fusion_large_l2_20260924`. Remote scratch is
`/home/data/wangxuran/tmp/gts_20260922_cpu_io/large_end_to_end_20260924_gpu0`.
The first GPU 1 batch stopped when a foreign process entered during
`timing_2_A`; its failed receipt is preserved in the sibling `_gpu1` root.
No observation from that batch is included in the fresh GPU 0 campaign.

The complete remote root is copied to ignored `local/raw/`. The audit
rechecks code, registration, fixture/oracle/gold hashes, stage order, all
receipts, GPU admission, in-process interference checks, sanitizer summaries,
full CPU distance matrices, every ordered output hash, and profiler signatures
against the previous Graph traces. It then derives `EVIDENCE.json`:

```bash
python3 analyze.py local/raw EVIDENCE.json
python3 report.py
```

The report uses process-mean completed hot-query time and exact four-round
paired log-ratio bootstrap intervals. The CUDA executable is not regenerated
or modified by this campaign; its SHA-256 is frozen in the registration.
