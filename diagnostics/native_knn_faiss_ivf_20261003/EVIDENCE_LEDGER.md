# Evidence ledger

| ID | Claim | Scope | State | Evidence / boundary |
|---|---|---|---|---|
| B-IO | Original GTS V2 can be observed as a full-ID kNN comparator | Separate pinned-source adapter, K8/32 | unvalidated | prepare_gts.py, gts_bench.cu, DESIGN_CARD.md; production qualification pending |
| B-IVF | Native GPU IVF meets a registered kNN quality anchor | GIST/Deep 1M, new self-inclusive queries | unknown | No evidence until parameter freeze and independent final qualification |
| B-E2E | One comparator has lower Host-ready latency at matched quality | Same dataset/K/B/anchor, six fresh-process rounds | unknown | No evidence; no range-truncation or old benchmark number may substitute |

## Preserved preparation failures

- The PATH alias `/usr/local/bin/nvcc` loses nvcc's toolkit-relative include
  resolution. The first build failed before GPU execution. The actual compiler
  `/usr/local/cuda/bin/nvcc` compiled the diagnostic without arithmetic changes.
- Canonical and legacy GPU lock aliases have identical device/inode identities
  on this host. Opening both caused self-contention before a child was started.
  The runner deduplicates inode identities; no occupied external lock is bypassed.
- The installed CuPy lexsort entry point did not accept a tuple of arrays. The
  first oracle attempt failed, without an oracle result. Selected oracle
  candidates are now deterministically ordered by NumPy lexsort; the full-table
  RN FP64 scan and CPU spot-check contract are unchanged. Failed logs are kept.

Raw receipts, rejected attempts and their runtime status are append-only under
runs/. No result is admitted solely because a process compiled or exited zero.

## Final decisions (append-only; registration states above are historical)

| ID | Exact admissible claim | Scope / denominator | State | Evidence | Material exception / next action |
|---|---|---|---|---|---|
| B-IO-final | The pinned original V2 adapter delivers independently checked full neighbor IDs/distance fields | GIST/Deep1M, K8/32, B1/32, final256×six rounds | measured | SOURCE_HASHES_formal.json, per-shape quality/receipts, POST_VALIDATION.json | Capacity/workspace/output adapter, not an untouched published binary; no updates/Graphs |
| B-IVF-frozen | Development-selected100% IVF points miss final100% on all eight shapes | Frozen final256, six native processes | rejected | FROZEN_CONFIG.json, all formal IVF quality records, SUMMARY.json | Keep failed anchors; no test tuning.99% targets all pass,99.9% only Deep passes |
| B-IVF-control | Fixed native all-list1024/1024 reaches100% tie-aware recall on all eight shapes | Same frozen final256, later six processes | measured | EXHAUSTIVE_CONTROL.json, control_r1–r6 JSON/receipts | GIST deterministic-ID recall is below100% solely because valid exact-boundary alternatives differ |
| B-E2E-primary | At admitted minimum-quality targets, native IVF has shorter Host-ready passes than this original GTS adapter |99% targets on both datasets;99.9% targets on Deep, six direction-balanced rounds | measured | SUMMARY.json paired log-ratio CIs/order splits/process wins/raw timings | Minimum targets are not equal achieved recall; no100% primary ratio is admitted |
| B-E2E-control | Later exhaustive IVF median256-query passes are63.6–140.2× shorter at equal achieved tie-aware100% quality | Eight shapes, original six GTS processes versus six later IVF processes | partial | SUMMARY.json exhaustive_supplement, RESULTS.md | Non-paired temporal separation; independent CI cannot remove order/time confounding; no optimization promotion |
| B-CPU-range | On the GIST32-query/K8/B32 diagnostic, leaf-distance processing occupies99.087% of the NVTX interval and CUDA-device-sync intervals overlap that execution | Query-only NSYS range, original binary | partial | TRACE_SUMMARY.json, kernel/API CSV, raw report hashes | Inclusive API duration is not CPU arithmetic or transfer duration; no CPU instruction sampling |
| B-coalescing | Coalescing changes causally reduce this end-to-end gap | No experiment in this delivery | unknown | no evidence | Needs same-arithmetic layout-only control, sector/request counters and Host-ready timing |
| B-GTSPP | Current production GTS++ beats native IVF under this contract | No GTS++ run in this delivery | unknown | no evidence | Add the current optimized keeper; do not infer from original GTS |
| B-updates | Insert/delete or all GPU trees share the observed cost profile | Static original queries only | unknown | no evidence | Run separate update/mixed contracts; no universal tree claim |

Implementation status: diagnostic/reproduction paths are delivered; production
search sources are unchanged. Mechanism status: dominant GPU leaf work is located,
but arithmetic/layout/candidate-count causes are not separated. Thesis impact:
native IVF is a required external comparator; no novelty or universal redundancy
claim follows from this comparison.

## Additional preserved failures and delivery checks

- First low-probe native development run returned legal `-1` padding when a
  selected bucket population supplied fewer thanK candidates. The initial checker
  rejected it. Retry scores padding as missed slots; anchors are not relaxed.
  The failed dev_ivf_GIST receipt/log and v2 raw grid both remain.
- The first raw-string NVTX capture exited zero but generated **no report**;
  export therefore failed. Runtime-valid is not trace-valid. The v2 capture
  explicitly enables raw-string matching with the documented NSYS environment
  option. All four v2 complete query ranges pass trace inventory checks.
- The initial public runner draft self-contended on a freshly created canonical
  lock when its legacy root equaled `/tmp`. This was caught by the publication
  review before collection with that runner. Descriptor-inode deduplication and
  a fresh-lock/foreign-owner CPU regression fix it without bypassing external locks.
- Original collection quality gates lack explicit signed/ordered fields and
  pure-relative/zero-distance diagnostics. Offline retained GTS checks and
  separate fixed-configuration native replays supply the additional evidence;
  they are not silently retrofitted into the original timing checker.
- Public adapter rebuilds and intended-GPU synthetic smoke checks pass. Rebuilt
  container hashes differ from the measured original binary. Compile commands,
  all hashes and scopes are retained; no smoke timing replaces formal timing.
- Initial-build, Faiss/oracle sanitizer, CUDA Graph, external-query and mixed
  update gates are not covered. This delivery is not a production admission.

Raw private collection is preserved unchanged on the experiment host. Public
text copies have explicit collection/curated hash mappings. The six-round source,
measured binary, data and caches were checked unchanged after collection; selected
GPU was clear, and the pre-existing GPU0 service remained alive.
