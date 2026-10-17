# Source admission and visibility authority

## Two evidence axes, not a misleading single label

A real vector dataset does not establish a real update distribution. B-grade
replay fidelity does not turn a generated benchmark into an A-grade deployment
trace. The physical storage adapter is a third, separately declared boundary.

| Input | Source/distribution evidence | Boundary evidence | Admitted use |
|---|---|---|---|
| English Wikipedia recentchanges, one frozen hour | A: actual public CMS edit/new observations, not vector-service logs | CMS revision IDs/timestamps; vector requests, ACKs and readers absent | Logical repetition and revision-chain statistics only |
| Three Big ANN Wikipedia-1M expiration runbooks | B: exact public-system operation replay; underlying expiration/replacement distribution C | Serial runner calls and interleaved search steps | Conditional packed-store structure, not deployed ANN storage/performance |
| Quake Wikipedia workload | B-style real-pattern-derived evaluation design; source audit only, no generated workload replay here | Paper/current-main append/query design; actual input files not admitted | Identify append-only counterexample, not measured 12M workload |
| SPFresh public evaluation | C update distribution despite production-derived SPACEV vectors | Per-vector foreground operations, not an atomic day-wide commit | Source classification; no epoch-as-ACK reinterpretation |
| Wikidata vector service | Real application context, but documentation describes snapshot-derived embeddings | No operation/ACK trace obtained | Reject CMS edits as an automatic substitute for vector-service updates |

## Public benchmark semantics

The pinned [Big ANN runner](https://github.com/harsha-simhadri/big-ann-benchmarks/blob/89a3abaafa63dda46b94b308bdf039e699841b3b/neurips23/streaming/run.py#L33-L64)
passes ascending ID ranges into separate insert/delete/replace calls and performs
searches at explicit steps. We preserve the whole sequence, scale and stable
logical tags. Replacement overwrites the payload at its tag; we do **not** invent
a delete-plus-insert path. No concurrent observer is added to this closed replay.

The [expiration generator](https://github.com/harsha-simhadri/big-ann-benchmarks/blob/89a3abaafa63dda46b94b308bdf039e699841b3b/neurips23/runbooks/gen_expiration_time_runbook.py#L13-L83)
uses seeded random expiration/replacement choices. Names containing “Wikipedia”
do not establish production arrival patterns. We replay the three existing 1M
YAML files exactly, not regenerate a more favorable sample.

Packed ascending-order swap-delete is **our explicit symbolic adapter**. It is
not a claim that DiskANN, SPFresh, Quake or a deployed service stores data this
way. Every allocated opaque row token, including retired rows, is preserved.
Source calls remain observer boundaries; 512-row subdivisions are internal
execution scopes and are never formed across source calls. No queueing delay,
arrival process, SLA or distributed atomicity is fabricated.

## Why other source names are insufficient

[SPFresh's evaluation](https://arxiv.org/html/2410.14452#S5.SS1) samples daily
insertions/deletions randomly. Its pinned `SPFresh.h` calls individual
`DeleteIndex`/`AddIndexSPFresh` operations. A daily update epoch therefore is not
licensed as a single atomic deletion batch. We inspect source only; no SPFresh
system or 100M/1B experiment is executed.

[Quake's paper](https://www.usenix.org/system/files/osdi25-mohoney.pdf) describes
monthly Wikipedia page additions and page-view-derived query sampling. The
[current-main generator](https://github.com/marius-team/quake/blob/0651c88c5c71343191ef06ee4ed292cb4a01e1aa/test/experiments/osdi2025/wiki_workload/wiki_workload.py#L236-L301)
contains append/query operations, not a deletion trace. The official `osdi2025`
branch was also inspected at `8d247a3bb67a081e30246ba12946e8f68470de35`; its
corresponding main-branch workload file is absent, and its artifact README marks
full reproduction as in progress. We do not claim a faithful generated replay,
complete public-data unavailability, or reconcile the paper's 103 updates with
the current-main 104-update upper bound by inventing input data.

The [Wikidata vector-service documentation](https://www.wikidata.org/w/index.php?title=Wikidata:Vector_Database&oldid=2548108356)
identifies snapshot-derived embeddings. This is not authority to interpret every
live Wikidata/Wikipedia edit as an acknowledged vector-index replacement.

## Admission for a future real-service trace

A useful structure-only record needs initial logical membership and row order,
ordered stable IDs/payload-version identities, request membership and return/ACK
boundaries, plus interleaved queries/snapshots/readers. Optional vectors are not
required for opaque-provenance counting, but actual vector outputs and complete
ACK/service costs are needed for performance admission. Unspecified boundaries
must stay UNKNOWN. Consistent opaque IDs may be used; raw business events and
identity-mapping secrets must remain outside Git.
