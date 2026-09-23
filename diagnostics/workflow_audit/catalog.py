#!/usr/bin/env python3
"""Exhaustive pinned-source kernel inventory; manual per-family access review."""
import csv,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
# Values: access pattern, candidate, mandatory constraint.
FAMILIES={
 'distance':('A lane owns a point/query and loops coordinates; AoS rows gather/stride across lanes, coordinate loads contiguous only within each lane; output is often already coalesced.','Test warp-per-distance or query/pivot tiling; retain coalesced output via ownership handoff, not lane0 scattered stores.','Keep metric, accumulation, pruning boundary and every tail; small grids may lose to launch/metadata costs.'),
 'node_split':('Only up to TREE_ORDER lanes do two serial endpoint distances; strided/gathered coordinates and 20-byte TN AoS stores.','Cooperate within warp on endpoints; consider reusing exact unencoded distances from build, not lossy encoded-key decoding.','Preserve conservative min/max bounds, FP rounding, partition and empty-child semantics; price sidecar traffic.'),
 'linear':('Grid-stride scalar arrays are contiguous across lanes; no obvious coalescing defect.','Keep layout; consider eliminating redundant initialization/pass or reusing workspace only if consumer requires same bytes.','Prove every read is initialized; launch fusion is distinct from memory coalescing.'),
 'flag':('Adjacent flags contiguous; parent flags may broadcast, node fields are AoS or gathers.','Retain SoA flag writes; consider compact node-field views only if amortized across consumers.','Do not add packing per query without end-to-end benefit; preserve parent/child ownership.'),
 'transpose':('Reads node-major/query-minor flags contiguously but writes query-major/node-minor, strided between lanes.','Shared-memory tiled transpose or choose one layout consistently through count/scan/compaction.','Both sides of transpose and prefix/query boundaries must remain correct; partial tiles and padding explicit.'),
 'scatter':('Input stream mostly contiguous; prefix/gather destinations may not be adjacent across lanes.','Choose traversal matching prefix order; warp/block packing can make output contiguous.','Preserve per-query grouping, ID mapping, prefix offsets and any stable-order requirement.'),
 'reduction':('One query thread invokes device Thrust reduction over a long segment; across query lanes the segments are far apart.','One warp/CTA per segment with cooperative contiguous loads and hierarchical reduction.','Preserve empty segments, exact count, nonpower tails; static RNN proof does not cover update API fallback.'),
 'kth':('One sparse kth gather per query; contiguous small output.','Usually leave alone; fuse into producer only after output readiness proof.','O(1) per query, not the RNN full reduction; preserve sort/key and kth ties.'),
 'topk_copy':('One query thread loops k; lanes read different query segments and write with stride k.','One warp/query or flatten query-rank output to contiguous lanes.','Preserve full IDs/distances/tie contract; measured final copy is only a small fraction of large-query cost.'),
 'atomic_compact':('Input is contiguous; each passing lane atomically reserves one output slot; inter-warp ordering arbitrary.','Warp ballot/popcount, one reservation per warp, adjacent lane stores; compare native/CUB select.','Preserve unordered output contract or add ordering explicitly; empty masks and total capacity required.'),
 'data_pack':('One lane copies a full point with serial coordinate loop; read and write across lanes stride D elements.','Flatten destination coordinates or warp-per-point copy; rows gather but lanes within each row contiguous.','Preserve alive order, original-vs-current source identity, deleted prefixes, true-arrival bytes and buffer capacity.'),
 'merge_linear':('Two contiguous input segments and contiguous output stores; only deletion-prefix remapping uses a rid-indexed gather.','Keep output ownership; consider avoiding repeated logical-ID remapping or retaining mapping on device.','Preserve base/buffer/incremental identity spaces; packing is not needed for already contiguous output.'),
 'debug':('Debug-only printing/checks; no production optimization target.','Leave outside active dispatch; inventory retained so absence is explicit.','Do not count an uncalled debug definition as workload cost.'),
 'string':('Each lane owns one edit-distance DP and an irregular string; large per-thread table, divergent lengths.','Separate length-bucket/wavefront DP design rather than blindly reuse L2 warp code.','Exact edit distance, table bounds, zero-length strings, stack/local traffic; unmeasured here.'),
 'legacy_scan':('Contiguous arrays but repeated stride-doubling passes.','Use native scan if this dormant implementation is revived; current buffer path instead scans on CPU.','Do not credit removal of uncalled kernels as a live improvement.'),
 'gather_topk':('One CTA/query, lanes already write adjacent top-k slots; input permutation gathers.','Keep output mapping; profile gather locality or fuse selection only with exact contract.','Legacy API is not the native V2 entry; preserve selected IDs and sort order.'),
}
MAP={
 'tree.cuh':{'getPivotDis':'distance','nodeSplit':'node_split','initIndexData':'linear','showRes':'debug'},
 'search_v2.cuh':{'nodeProcessRnn':'distance','nodeProcessKnn':'flag','initPList':'linear','initPListKnn':'linear','getQCount':'transpose','getQCountKnn':'transpose','mergeLNode':'scatter','mergeLNodeKnn':'scatter','dataProcessRnn':'distance','dataProcessKnn':'distance','dataProcessKnnVec':'distance','mergeResRnn':'reduction','mergeResKnn':'kth','mergeResKnnIds':'topk_copy','initResV2':'linear','initDisK':'linear','labelCNode':'flag','getDisPQ':'distance','getDisPQVec':'distance','updateDisK':'kth'},
 'search.cuh':{'findNextRnn':'distance','findNextKnn':'flag','updatePnodeFlag':'flag','updateCnodeFlag':'flag','getQpDis':'distance','updateDisk':'kth','leafProcessRnn':'distance','leafProcessKnn':'distance','getQnodeCount':'reduction','getQresultCount':'reduction','mergeLeafNode':'scatter','mergeResultRnn':'scatter','mergeResultKnn':'scatter','getKnnResult':'gather_topk','initQnode':'linear','initDisk':'linear','initRes':'linear','checkRes':'debug'},
 'search_naive.cuh':{'searchD':'distance','searchS':'string','check':'linear','getAccu':'legacy_scan','updateUpp':'legacy_scan','getRnn':'scatter'},
 'update.cuh':{'mergeTotalResult':'merge_linear','findIdx':'linear','mergeInResult':'scatter','getNewData':'data_pack','leafProcessRnnUpdate':'distance','collectLeafNodesSingleQuery':'atomic_compact','compactResultSingleQuery':'atomic_compact'},
}
for f in ['update_optimized.cuh','update_user_modified.cuh']:
 MAP[f]=dict(MAP['update.cuh'])
MAP['update_optimized.cuh']['collectLeafNodesAndInitRes']=MAP['update_optimized.cuh'].pop('collectLeafNodesSingleQuery')
def strip(t):
 # Preserve offsets/newlines, including comment-like text inside strings.
 return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/',lambda m: ''.join('\n' if c=='\n' else ' ' for c in m[0]) if m[0].startswith(('/',)) else m[0],t)
def reach(file,name):
 if file.startswith('update_'):return 'alternative header; not included by native main'
 if name in ['showRes','checkRes','initResV2','findIdx','getAccu','updateUpp']:return 'definition only; no active native launch'
 if file=='tree.cuh':return 'initial build and capacity-triggered rebuild'
 if file=='search_v2.cuh':
  if name in ['dataProcessKnnVec','getDisPQVec','mergeResKnnIds']:return 'V2 vector/full-ID overload or calibration; ID main uses kth-only'
  return 'V2 static RNN/kNN; NOT update query'
 if file=='search.cuh':
  if name in ['findNextRnn','updatePnodeFlag','initQnode','initRes']:return 'native update query and legacy API'
  if name in ['getQnodeCount','getQresultCount','mergeLeafNode','mergeResultRnn']:return 'update qnum>1 fallback / legacy API; native main fixes qnum=1'
  return 'legacy query API; no native main call'
 if file=='search_naive.cuh':return 'overflow-buffer query; searchS only string metric'
 return 'native update conditional path'
def build():
 pins=json.loads((HERE.parent/'cpu_io/SOURCE_PINS.json').read_text());texts={}
 for f,h in pins['sha256'].items():
  b=(ROOT/f).read_bytes();assert hashlib.sha256(b).hexdigest()==h,f
  if f.endswith(('.cuh','.cu')):texts[f]=strip(b.decode())
 rows=[];sites=[]
 for f,t in texts.items():
  names=[]
  for m in re.finditer(r'__global__\s+void\s+(\w+)\s*\(',t):
   n=m[1];names.append(n);family=MAP[Path(f).name][n];access,candidate,gate=FAMILIES[family]
   if n=='leafProcessRnnUpdate':gate+=' P0: node.size can exceed MAX_SIZE while result stride stays MAX_SIZE.'
   if n=='leafProcessRnnUpdate' and Path(f).name=='update.cuh':gate+=' Native all-include self/sentinel differs.'
   if n=='nodeProcessKnn':candidate+=' C3 ballot mask is unused; warp label alone is not coalesced distance work.'
   if n in ['dataProcessKnn','dataProcessKnnVec']:gate+=' Prior D64 is bounded integer L2 only; Q32 full-query gates failed.'
   if Path(f).name=='update_optimized.cuh' and n=='collectLeafNodesAndInitRes':access+=' Despite its name, qresult_idx is not written here and the caller still launches initRes; fusion is NOT implemented.'
   rows.append(dict(file=f,line=t.count('\n',0,m.start())+1,kernel=n,reachability=reach(Path(f).name,n),family=family,access=access,candidate=candidate,correctness_gate=gate,evidence='source-confirmed access pattern; measured coverage in runtime exports; no new speedup claim'))
  assert set(names)==set(MAP.get(Path(f).name,{})),f
  patterns=[('launch',r'\b(\w+)\s*<<<'),('thrust',r'\b(thrust::\w+)\s*\('),('cuda_boundary',r'\b(cuda\w+)\s*\(')]
  for kind,pattern in patterns:
   for m in re.finditer(pattern,t):sites.append(dict(file=f,line=t.count('\n',0,m.start())+1,kind=kind,operation=m[1],scope='alternative unselected' if Path(f).name.startswith('update_') else 'pinned native/conditional/legacy; not proof of runtime execution'))
 assert len(rows)==69
 for name,data in [('kernels.csv',rows),('sites.csv',sites)]:
  with (HERE/name).open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
 (HERE/'COVERAGE.json').write_text(json.dumps({'source_pins':pins,'kernel_definitions':len(rows),'selected_header_definitions':sum(not r['file'].split('/')[-1].startswith('update_') for r in rows),'unselected_alternative_definitions':14,'sites':len(sites),'scope':'static source inventory; separate runtime intersection, not every branch dynamically tested'},indent=2)+'\n')
 print('PASS69 definitions,',len(sites),'launch/library/runtime boundary sites')
if __name__=='__main__':build()
