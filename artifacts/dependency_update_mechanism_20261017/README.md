# Dependency-aware GPU update attribution

**B — ENGINEERING_STRONG, not an independent Tail algorithm contribution.**
All 368 registered GPU targets pass. Generic propagation and Tail produce the
same final assignments; the tested Tail planner is slower than generic DSE on
all four fixed mixed-service traces. Strong standard-library execution retains
the engineering benefit without requiring the custom executor.

- [REPORT.md](REPORT.md): full conclusion, six baselines, structure, complete
  ACK/service, physical attribution, figures and limitations.
- [DECISION.md](DECISION.md): separate implementation/mechanism/thesis decisions,
  negative evidence and one remaining research question.
- [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md): exact allowed wording and counterevidence.
- [CONTRACT.json](CONTRACT.json), [GPU_CONTRACT.json](GPU_CONTRACT.json): original
  CPU gate and privacy-curated pre-target GPU contract.
- [DESIGN.md](DESIGN.md), [SEMANTICS.md](SEMANTICS.md), [PRIOR_ART.md](PRIOR_ART.md):
  actual mechanisms,strict allocated-state semantics and concrete novelty test.
- `results/`: all 252 fixed process records,70 contrasts and20 profile captures.
- `tables/`:168 operator rows,42 service/resource cells,420 paired metric rows,
  physical activities,counters and raw-bound replacement p50.
- `evidence/`:quality,census,source/binary/input identities,two closures and custody.
- `figures/`:three PDF/SVG/400DPI PNG figures plus exact numeric CSVs.
- [REPRODUCE.md](REPRODUCE.md), [ATTRIBUTION.md](ATTRIBUTION.md):checks and limits.

GIST1M = 1,000,000 x 960 FP32 coordinates (3.84GB). Each main process has 500k
replacement pairs,1M point updates and160 formal B1 exact-range queries.
Families model logical-age/cancellation stress,not measured application traffic.
This is not a10k-query,ANN/kNN,Faiss/CAGRA,original GTS-tree,1B,concurrent-reader
or production-admission result. Large inputs/raw archives remain outside Git;
public manifests prove identity,not public raw availability. Confidential paper
sources and existing production paths are not changed.
