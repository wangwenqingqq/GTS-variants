# Baseline identity

Upstream source: `ZJU-DAILY/GTS` at commit
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639` (see source pins for exact origin).
The eight file hashes in `SOURCE_MANIFEST.json` are verified against the live
local upstream copy before generation. Actual include chain:
`bench.cu -> tree.cuh -> config.cuh`, then `navigation.cuh -> search_v2.cuh`.
The entry is **searchIndexKnnV2**. Runtime evidence remains a separate gate.

G0–G3 are one fresh binary with independent mode bits: 0=neither, 1=memo,
2=distinct cross-layer candidates, 3=both. Numeric/common-output repairs are
shared. Generated `common.patch` and source hashes are retained privately;
no upstream source or data is republished here.

Compiler: CUDA 13.1, `nvcc -O3 -std=c++17 --fmad=false -lineinfo
-gencode arch=compute_120a,code=sm_120a -rdc=true -I adapted/include
bench.cu -lcudadevrt -o bench`. The toolkit's full nvcc path is used so relocated
symlinks do not lose header lookup. Build/binary receipts accompany results.

Tree: height 6, branch 10, allocated 111111 nodes, leaf capacity 20 with actual
10 objects per leaf in this snapshot. 1M distinct logical instances; complete
unique leaf ownership, source/tree hashes in `evidence/TREE_AUDIT.json`.
Queried pivot families: levels 3–5, 11100 slots, 11099 unique rows if all visited.

Native upper-bound chain: current-level `getDisPQ -> Thrust sort -> updateDisK`
with first two levels skipped. No original persistent distinct cross-layer
candidate set and no original pivot-to-leaf distance memo. The common repair
retains the original O(1) Kth read after the level sort in G0/G1;
G2 additionally retains distinct prior-level witnesses and includes them in the
final output. G1 retains G0 decisions.

Current P routes are separate historical prototypes; none is used as G0 and
none is renamed to a G0–G3 mode. Other concurrently running G0/G1 diagnostics
use a different legacy arithmetic contract and a different GPU; their samples
are not pooled or counted in this campaign.

Status at freeze: CPU source/ownership audit passed; CUDA implementation
unvalidated; formal budget 0/24. See append-only ledger for later gate states.
