# E3 static baseline matrix — not yet executed

E4 precedes E3. No E3 latency, ratio, recall, or sanitizer result is claimed by
this inventory. Every required dataset/k/Q remains scheduled.

| Dataset | k | Q | G | P | S |
|---|---|---|---|---|---|
| T-loc1M | 8,10 | 1,32,full1000 | pending/native arena bound | pending | pending |
| T-loc10M | 8,10 | 1,32,full1000 | pending/native arena bound | pending | pending |
| Word | 8 | 1,32,full1000 | pending/native arena bound | pending | pending |
| Vector200K angular/cosine | 8 | 1,32,full100 | pending/native arena bound | pending | pending |
| Deep1M | 8,10 | 1,32,full10000 | pending/native arena bound | pending | pending |
| SIFT1M | 8,10 | 1,32,full10000 | pending/native arena bound | pending | pending |
| GIST1M | 8,10 | 1,32,full1000 | pending/native arena bound | pending | pending |
| Protein | 8 | 1,32,full1000 | pending/native arena bound | pending | pending |
| ChEMBL | 8 | 1,32,full1000 | pending/metric support | pending/metric support | pending |

## Live inventory, 2026-10-26 UTC

Read-only guarded source inventory found the expected archived data families.
Vector header is300 dimensions,200000 rows,metric5; Protein header100,52799,
metric6; ChEMBL50K is2048 dimensions,50000 rows,metric8. These headers are not
full-content or hash validation. Exact sources/query identity and all hashes
must be separately frozen before E3 execution.

The approved archived tree/search files have branches for metrics0/1/2/5/6 but
no metric8 branch. Static ChEMBL P/G support therefore remains unestablished;
never run an all-zero fallthrough as a real Tanimoto baseline. Do not modify the
approved P search beyond the authorized patch/WORK boundary to hide this gap.

Native metric5 computes angular distance in degrees, monotonically related to
cosine similarity for nonzero vectors. The E3 oracle/tie tolerance must use the
actual declared angular metric, not silently change its distance denominator.
Zero-vector and acos-domain behavior must be audited before launch. The E4
vector harness is L2/k8/1000query-specific and does not complete E3 automatically.

S native FAISS1.15.1 extension/interpreter hashes and CuPy14.1.0 metadata have
been collected read-only before S gates. Edit/Tanimoto use explicitly labeled
custom scans, not native-library proxies. No dependency or GPU setting was changed.

C2/P-approx are removed. Optional larger Protein/Tanimoto gradients remain
optional and uncompleted; no synthetic strings substitute for versioned protein.
