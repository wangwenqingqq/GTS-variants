# Representation decision — 2026-10-11

**`PIVOT_CERTIFICATE_KILLED`**, narrowly scoped to the fixed 64 original-pivot
pool, unchanged GIST tree, eight frozen development queries, same U*, and
level-local outward-FP32 interval/max-bound representation. No GPU candidate,
paper mechanism or speedup is promoted.

## Sequential gate record

| Stage | Predeclared test | Observation | Decision |
|---|---|---|---|
| A | Stop if pooled L3 truth residual >=50% | 0.587500%; C0 is 83.387500% | Continue B |
| B | Promote C4/C8 at L3/L4 with >=70% gap, >=10% new G0 work, <=64 aligned B | GLOBAL-8 gap 4.544082% / 6.041531%; work 3.814956% / 4.980949% | No promotion; continue C |
| B | Kill GLOBAL if max C8 new G0 work across levels <10% | Max 8.200811% at L5 | GLOBAL rejected |
| C | Same promotion test; reject pool if max REGION-8 gap across levels <50% | Max 13.526861% at L5; L3/L4 8.529589% / 9.188991% | Pool route rejected |

The final decision follows the declared estimator rather than the favorable
query 660835 (76.147094% leaf gap coverage). REGION-4 improves over GLOBAL-8,
fits 48B, and reaches the full-pool pruning result on this sample; that is real
positive evidence, not a latency win and not sufficient for promotion.

## What this does and does not establish

**Measured:** ancestor-level fixed-U* truth residual is low; the existing bounds
are weak; global pivots miss the work gate; query-oracle per-region selection
does better but misses the gap gate. REGION-8 exactly realizes the union of all
64 candidate prune masks. Every candidate bound is safe under the frozen score
contract, and both selection families are monotone.

**Inferred:** more interval dimensions from this exact pool cannot improve
pruning under the same max-of-individual-bounds contract on these eight queries.
The cause is not solely use of a shared subset: even unconstrained per-region
selection of this pool falls short. This is not a proof against other pivots,
joint geometric constraints, cross-level composition or different summaries.

**Material caveat:** perfect ancestor truth is partly a granularity effect.
With only eight threshold-retained objects/query and 1,000 objects per L3
region, at most 8,000 objects/query can lie in truth-retained L3 regions even
without an especially good partition. Low truth residual does not by itself
validate partition quality or imply a compact implementable certificate.
REGION selection overfits the same eight queries; no holdout, other dataset,
formal256, 10K or E2/E3 admission result exists here. No CPU utilization, GPU
utilization, measured metadata traffic or end-to-end latency is established.

## Negative-evidence record and reopen condition

- **Target/keeper:** unchanged repaired-original G0 tree/path bounds, same
  independent U*, same original G0 visit denominator at L3/L4/L5.
- **Rejected mechanism:** fixed64 classical pivot lo/hi summaries, shared
  farthest-first or oracle per-region greedy, 0/1/2/4/8 nested dimensions.
- **Effect:** best pooled gap coverage 13.526861%; REGION-4 leaf additional
  visited pruning 11.514593%, while L3/L4 remain 7.160963% / 7.575877%.
- **Added costs:** REGION-4 needs 48 aligned B/region and 28/45/60 unique
  pivot distances/query; REGION-8 needs 80B with identical pruning but twice
  the bound evaluations. Costs are proxies in separate units, not latency.
- **Do not revive:** do not implement this unchanged pool/interval family in
  CUDA or add its classical geometry as paper novelty. More dimensions from
  this pool, larger metadata or CUDA Graph execution do not fix its observed
  information ceiling under this contract.
- **Reopen only with:** a predeclared materially different pool/summary,
  combined geometric constraint or partition mechanism, a cheap same-contract
  falsification screen, and a nearest-prior-art kill test. Show reproducible
  improvement on development queries, then independent held-out queries;
  retain true bytes, evaluation costs, exact safety and original comparator.
  A latency campaign requires separate resource admission and complete GPU
  correctness/end-to-end gates. No next mechanism is implemented automatically.

## Claim-evidence ledger

| ID | Claim | State | Evidence / denominator | Allowed wording and counterevidence |
|---|---|---|---|---|
| CC-A | Ancestor truth has high counterfactual headroom | measured | ANCESTOR_TRUTH.json, 8M query-object pairs, same U* | Low truth residual on this tree/slice; granularity is a material caveat |
| CC-B | GLOBAL-8 is insufficient | rejected | per_level_summary.csv; same-level original G0 visits | All three levels <10% new visited work; positive pruning is not zero benefit |
| CC-C | Region-specific choice rescues the fixed pool | rejected | REGION rows; pooled oracle gap | Better than GLOBAL but max 13.526861%, below 50%; one favorable query does not replace pooled estimator |
| CC-D | Larger subsets of this pool cannot improve its prune envelope | inferred | all64 masks equal REGION8 at every region/query | Only same numerical format and max-bound family on eight queries; not arbitrary geometry |
| CC-E1 | The new interval bound is conservative under its arithmetic contract | theoretical | SAFETY.md forward-error and reverse-triangle proof | Finite FP32 [0,2], D960, ordered RN-FP64, rho=1e-4; not an unproved epsilon |
| CC-E2 | The selected implementation passes finite-set safety checks | measured | 56,832,000 candidate checks + serialized records | Zero violations on this freeze; finite checks do not replace CC-E1 or remove old G0 admission limits |
| CC-F | Metadata fits the declared byte budget | measured | CERTIFICATE_VALIDATION.json actual record lengths/hashes | GLOBAL8=64B; REGION4=48B; REGION8=80B, IDs/padding included |
| CC-G | Certificate reduces end-to-end CPU/GPU overhead or latency | unknown | no timing evidence | No claim; count leverage cannot establish latency or general GPU-tree redundancy |
| CC-H | Classical multi-pivot summary is novel | rejected | PRIOR_ART.md, AESA/LAESA/M-tree/PM-tree/G-PICS/GTS | Established baseline; a distinct mechanism would need a new novelty gate |

All experiment rows belong to `certificate_compression_20261011`, base
`1f4d4ab05c66b4cc2411b7532a86517b823d53f9`, CPU-only Linux scalar collection plus
offline analysis on 2026-10-11. Sources and large raw outputs are SHA-pinned;
the final task commit and remote verification are reported at delivery.
