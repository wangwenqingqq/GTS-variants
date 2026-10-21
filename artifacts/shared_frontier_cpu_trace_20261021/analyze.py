"""Frozen integer10x admission checks; no queries or oracle outcomes are generated."""
if not __debug__:raise SystemExit('Assertions required')
import csv,json
from pathlib import Path
from audit_run import audit
HERE=Path(__file__).resolve().parent
INTS=['state','N','Q','node_pair_visits','bound_calls','verify_calls','partition_calls','query_plan_calls','distance_calls','candidate_pairs','max_frontier_records','max_frontier_alloc_bytes','max_logical_query_node_frontier','query_tree_bytes','output_count','index_build_calls','index_nodes','index_bytes']

def analyze(root,inputs):
 validity=audit(root,inputs)
 rows,builds=collect(root)
 return summarize(rows,builds,validity)

def collect(root):
 c=json.loads((HERE/'CONTRACT.json').read_text());rows=[];builds=[]
 for name in c['data']:
  for mode,seed in [('static',s) for s in c['sample']['query_seeds']]+[('updates',c['sample']['query_seeds'][0])]:
   key=f'{name}_{mode}_{seed}';target=root/key
   rs=list(csv.DictReader((target/'COUNTERS.csv').open()))
   for z in rs:
    z.update({k:int(z[k]) for k in INTS});z['radius']=float(z['radius']);z.update(mode=mode,seed=seed)
    assert z['distance_calls']==sum(z[k] for k in ['bound_calls','verify_calls','partition_calls','query_plan_calls'])
   rows.extend(rs)
   for z in csv.DictReader((target/'BUILDS.csv').open()):builds.append(dict(dataset=name,mode=mode,seed=seed,**z))
 return rows,builds

def summarize(rows,builds,validity):
 c=json.loads((HERE/'CONTRACT.json').read_text());cells=[]
 for name in c['data']:
  for seed in c['sample']['query_seeds']:
   for radius in c['data'][name]['radii']:
    rs=[z for z in rows if z['dataset']==name and z['mode']=='static' and z['seed']==seed and z['radius']==radius];by={z['method']:z for z in rs}
    assert len(rs)==(6 if name=='TLoc' else 4)
    raw,cache,shared,qj=[by[n] for n in ['GTS_LITERAL_CPU','GTS_PARENT_CACHE_CPU','SHARED_ANNULUS_CPU','QUICKJOIN_FAMILY_CPU']]
    assert len({z['output_count'] for z in rs})==1
    assert raw['candidate_pairs']==cache['candidate_pairs'] and raw['max_frontier_alloc_bytes']==cache['max_frontier_alloc_bytes']
    comparators=[cache,qj]+([by['GRID_2D_CPU'],by['SPATIAL_DUAL_AABB_CPU']] if name=='TLoc' else [])
    strong=min(z['distance_calls'] for z in comparators);charged=shared['max_frontier_alloc_bytes']+shared['query_tree_bytes']
    distance_pass=10*shared['distance_calls']<=strong
    frontier_pass=10*charged<=cache['max_frontier_alloc_bytes'] and 10*shared['max_logical_query_node_frontier']<=cache['max_logical_query_node_frontier']
    cells.append(dict(dataset=name,seed=seed,radius=radius,output_count=shared['output_count'],
      literal_calls=raw['distance_calls'],cached_calls=cache['distance_calls'],shared_calls=shared['distance_calls'],quickjoin_calls=qj['distance_calls'],
      strongest_control_calls=strong,distance_reduction_factor=strong/shared['distance_calls'],literal_vs_shared_factor=raw['distance_calls']/shared['distance_calls'],
      cache_vs_shared_factor=cache['distance_calls']/shared['distance_calls'],quickjoin_vs_shared_factor=qj['distance_calls']/shared['distance_calls'],
      cached_frontier_bytes=cache['max_frontier_alloc_bytes'],shared_frontier_plus_querytree_bytes=charged,
      frontier_byte_reduction_factor=cache['max_frontier_alloc_bytes']/charged,
      logical_frontier_reduction_factor=cache['max_logical_query_node_frontier']/shared['max_logical_query_node_frontier'],
      distance_10x=distance_pass,frontier_10x=frontier_pass,any_10x=distance_pass or frontier_pass,
      cached_candidate_pairs=cache['candidate_pairs'],shared_candidate_pairs=shared['candidate_pairs'],quickjoin_candidate_pairs=qj['candidate_pairs']))
 primary=[z for z in cells if z['dataset']!='TLoc'];assert len(primary)==12
 passed=sum(z['any_10x'] for z in primary)
 label='GO_OPPORTUNITY_ONLY' if passed==12 else 'NO_GO' if passed==0 else 'MIXED_STOP'
 return dict(experiment=c['experiment'],campaign_validity=validity,decision=label,primary_cells=12,primary_cells_reaching10x=passed,
             cells=cells,all_counters=rows,all_builds=builds,GPU_starts=0,protected_GIST_heldout_accesses=0,
             native_GTS_GPU=False,native_JZ_executed=False,novelty_admitted=False,
             timing_scope='CPU resource observations,not paired speedup or end-to-end service',
             denominator='Query-plan plus search metric calls vs strongest cached-GTS/Quickjoin (plus measured grid/spatial for TLoc);frontier requires both ownership-aware bytes and logical query-node reduction')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);a=p.parse_args()
 result=analyze(a.run,a.inputs)
 with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
