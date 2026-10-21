"""Independent complete output-byte and structural counter consistency checks."""
if not __debug__:raise SystemExit('Assertions required')
import csv,json,struct
from pathlib import Path

def verify_target(root,inputs,name,mode,seed):
 selection=json.loads((inputs/(name+'.selection.json')).read_text());rows=list(csv.DictReader((root/'COUNTERS.csv').open()));builds=list(csv.DictReader((root/'BUILDS.csv').open()))
 assert len(rows)==(12 if mode=='static' else 6)
 # TLoc has2 radii x6 algorithms;string datasets3 radii x4 algorithms.
 radii_expected=[.01,.05] if name=='TLoc' else [1,2,3] if name=='Words' else [2,4,8]
 methods_expected=['GTS_LITERAL_CPU','GTS_PARENT_CACHE_CPU','SHARED_ANNULUS_CPU','QUICKJOIN_FAMILY_CPU']+(['GRID_2D_CPU','SPATIAL_DUAL_AABB_CPU'] if name=='TLoc' else [])
 expected={(0,float(r),m) for r in radii_expected for m in methods_expected} if mode=='static' else {(s,float(radii_expected[len(radii_expected)//2]),m) for s in range(3) for m in ['GTS_PARENT_CACHE_CPU','SHARED_ANNULUS_CPU']}
 assert {(int(z['state']),float(z['radius']),z['method']) for z in rows}==expected

 assert [int(z['state']) for z in builds]==([0] if mode=='static' else [0,1,2])
 seen=set();checked=0;outputs=0
 for z in rows:
  state=int(z['state']);radius=float(z['radius']);method=z['method'];key=(state,radius,method);assert key not in seen;seen.add(key)
  assert int(z['Q'])==256 and int(z['N'])==65536-(32 if state==1 else 0)
  assert int(z['candidate_pairs'])==int(z['verify_calls'])
  assert int(z['distance_calls'])==sum(int(z[k]) for k in ['bound_calls','verify_calls','partition_calls','query_plan_calls'])
  radii=[.01,.05] if name=='TLoc' else [1,2,3] if name=='Words' else [2,4,8]
  ri=radii.index(radius) if mode=='static' else 0
  reference=root/f'S{state}_R{ri}_REFERENCE.bin';actual=root/f'S{state}_R{ri}_{method}.bin'
  b=reference.read_bytes();a=actual.read_bytes();assert a==b and len(a)%20==0
  assert len(a)//20==int(z['output_count']);old=None
  source_ids=selection['source_rows'];queries=selection['queries'][str(seed)];live=set(source_ids[:65536]);deleted={source_ids[i] for i in selection['deleted']}
  if state>0:live-=deleted
  if state==2:live|=set(source_ids[65536:])
  for qi,idx,score in struct.iter_unpack('<IQd',a):
   assert 0<=qi<256 and idx in live and score>=0 and score<=(radius if name!='TLoc' else radius*radius)
   now=(qi,idx);assert old is None or old<now;old=now
  if method=='GTS_PARENT_CACHE_CPU':
   raw=next((q for q in rows if int(q['state'])==state and float(q['radius'])==radius and q['method']=='GTS_LITERAL_CPU'),None)
   if raw:
    assert z['candidate_pairs']==raw['candidate_pairs'] and z['max_frontier_alloc_bytes']==raw['max_frontier_alloc_bytes']
  checked+=1;outputs+=len(a)//20
 assert checked==len(rows)
 return dict(passed=True,full_output_streams_checked=checked,output_records_checked=outputs,states=[int(z['state']) for z in builds],GPU_starts=0,scope='Full byte equality to all-pair reference and record membership;reference metric kernel shared,independent DP checked in qualification')
