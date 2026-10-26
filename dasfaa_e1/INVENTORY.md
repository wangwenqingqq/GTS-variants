# Larger real-data inventory — partial, not admitted

The inventory stopped after an SSH client exit 255. No reconnect was attempted.
All paths below are relative to the configured data root. Full local raw receipts
are retained outside the publish set; curated hashes are in
[evidence/continuation_20261026/PARTIAL_INVENTORY.json](evidence/continuation_20261026/PARTIAL_INVENTORY.json).
No larger dataset substitution is authorized or performed.

## SureChEMBL

Root: `TIDE/active/tide_surechembl_gate6_20260828/data/prepared/snapshots/`.
Seven snapshots make six adjacent release transitions, not six snapshots.
Each snapshot has headerless `fp_u64x4.bin` (32 bytes/row, 256 bits), `id_i64.bin`
and `popcnt_u16.bin`. The counts below are derived from consistent file sizes,
not a fresh semantic parse or ID-delta audit.

| Snapshot date | Rows from fingerprint file size | Fingerprint SHA-256 status |
|---|---:|---|
| 2026-06-01 | 37,849,270 | `1ceb7dc33ed10b1fce2dc3e43bd8dbb557b0a2420f9164eb085312f7372d9c4e` |
| 2026-06-15 | 37,871,160 | `543d940a7ceb3868585bd4d39944c56bde74c9460dfb0559e2831374dae0be25` |
| 2026-07-01 | 40,939,438 | `8388089cb8861e18b3877d74c9402edc25510b4b059c9d2d8af42377fbc72fe7` |
| 2026-07-17 | 40,946,511 | `c74a94df0d0d607d1dd2f4a2368c519b7a62e2c399adbe09fb8b505e77708c15` |
| 2026-08-04 | 41,089,185 | Not received |
| 2026-08-18 | 41,106,048 | Not received |
| 2026-08-25 | 41,126,808 | Not received |

For the first four snapshots, full hashes of IDs/popcounts were also received
and retained in the linked JSON. Snapshot directory dates are observed; official
release metadata and chronological ID/payload changes were not re-audited here.
All complete snapshots exceed the mandatory 10M tree cap and are forbidden as
full G/P inputs. A bounded real-ID subset could be considered only after explicit
user approval and a fresh frozen split/delta manifest. Do not expand 256-bit
fingerprints to 2048 bits and call them the original ChEMBL metric corpus.

## ChEMBL 37

Observed file: `TIDE/active/tide_surechembl_gate6_20260828/data/official/chembl_37/chembl_37.fps.gz`
(176,228,008 bytes). An HDF5 file also exists, but earlier HDF5/FPS discrepancy
means it is not an interchangeable source. Prefer the official FPS source.
Prior archived preparation reports 2,897,819 rows, 2048-bit fingerprints and
source SHA-256 `c33bfac42abfea96840279ec35eeb3364c1063aa3e35c02369618beaf6389529`.
Those are **historical expected values, not freshly verified hashes/counts** in
this interrupted inventory.

Prior release-pair evidence reports 43,874 new IDs, 870 removals and 15 changed
same-ID fingerprints between releases 36 and 37. Changed IDs are not fresh-ID
arrivals. This provides a meaningful versioned workload but 43,874 additions
alone cannot support an 80,000-insert trace. Do not recycle or copy payloads.

Recommendation pending user decision: a frozen <=1M genuine-row subset of the
2048-bit FPS corpus can support 100K mixed workloads after approved query
isolation and a 90/10 split. It changes the dataset contract and is not the full
release-delta workload. Preserve these two evaluations as distinct scopes.

## Protein 200K

Observed file: `wxr_pro6000-1/GTS/Datasets/dna_barcode/protein_200k.txt`.
Header: `200000 300 6`. The observed data rows are space-separated integer
character codes (for example 77,80,84), not literal sequence strings.
200K is the declared header count; a fresh complete line count, maximum sequence
length and SHA-256 were **not received**. Release date/accession mapping remains
unestablished. Do not call it a DNA barcode benchmark or a chronological stream.

The current adapter supports <=108-byte NUL-terminated strings, whereas the
file declares width 300. It requires audited decoding and width support before
admission. Even a 200K corpus gives only about 20K arrivals under 90/10: it still
cannot support 100K 4:4:2 or 8:1:1. It is not a complete capacity solution.

## Addressing and scale constraints

The cap is the minimum of the mandatory N<=10M ceiling, workspace feasibility
and actual implementation indexing limits. Several archival expressions form
`row*dim` in signed int32. With the external query row included, the conservative
adapter check is `(N+1)*dim <= INT32_MAX` (non-text payloads).

| Expanded payload | Conservative maximum N by int32 indexing | Other cap |
|---|---:|---|
| 2048-bit binary floats | 1,048,574 | N<=10M; tree workspace |
| 256-bit binary floats | 8,388,606 | N<=10M; tree workspace |
| 960D L2 floats | 2,236,961 | N<=10M; tree workspace |

A packed implementation could have different addressing, but is not the current
G/P interface and cannot silently relax this check. The pending inventory must
be finished only after explicit campaign resumption, with independent guard logs.


## 2026-10-26 04:57 UTC — resumed inventory killed by guard

A new streaming, read-only inventory was started under the authoritative guard
(RSS1GiB, minimum available48GiB, timeout900s). It returned98 after17s because
cgroup headroom fell to23.8GiB below the guard's24GiB floor; observed peak task
RSS0.04GiB. Full output was redirected to the E1-only remote resume directory,
but not downloaded after mandatory stop. It is not a newly verified complete
inventory. The existing four earlier snapshot hashes remain the only curated
snapshot evidence. ChEMBL37 count/hash, remaining SureChEMBL hashes and
protein200k full parse/hash still require completion after explicit resumption.
No larger corpus replacement, capacity relaxation or query reduction occurred.
