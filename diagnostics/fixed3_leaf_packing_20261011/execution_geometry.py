#!/usr/bin/env python3
"""Derive fixed32 distance-lane geometry from recorded masks, not scheduler counters."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
ROW=struct.Struct('<3f7I')
def analyze(path):
    totals={m:collections.Counter() for m in ('G0','G1','G2')}
    hist={m:collections.Counter() for m in totals};groups=collections.Counter();rows=[]
    with path.open('rb') as f:
        magic,n,d,nodes=struct.unpack('<4i',f.read(16));assert (magic,n,d)==(0x4c474531,1000000,960)
        for _ in range(32):
            qid,pivots,pivotdims=struct.unpack('<iQQ',f.read(20));tasks={}
            for row in ROW.iter_unpack(f.read(nodes*ROW.size)):
                if not row[5]:continue
                assert row[5]==1 and row[6]==1023 and not(row[7]&~1023)
                task=row[9];assert task not in tasks;tasks[task]=row[7]
            assert set(tasks)==set(range(len(tasks)))
            masks=[tasks[i] for i in range(len(tasks))];packed=[]
            for offset in range(0,len(masks),3):
                part=masks[offset:offset+3];groups[len(part)]+=1
                packed.append(sum(mask<<(10*i) for i,mask in enumerate(part)))
            assert sum(x.bit_count() for x in masks)==sum(x.bit_count() for x in packed)
            rows.append({'qid':qid,'leaves':len(masks),'packed_ctas':len(packed),'tail_leaves':len(masks)%3})
            for mode,mapped,warps in [('G0',masks,16),('G1',masks,1),('G2',packed,1)]:
                active=[x.bit_count() for x in mapped];hist[mode].update(active)
                totals[mode].update({'leaf_launches':1,'ctas':len(mapped),'configured_warp_slots':len(mapped)*warps,
                    'distance_participating_warps':sum(x>0 for x in active),'distance_threads':sum(active),
                    'zero_distance_warp_slots':len(mapped)*warps-sum(x>0 for x in active)})
        assert not f.read(1)
    modes={}
    for mode,t in totals.items():
        modes[mode]={**t,'distance_lanes_per_structural_object_warp':dict(hist[mode]),
            'distance_lane_fill_object_warps':t['distance_threads']/(32*t['ctas']),
            'distance_lane_fill_all_configured_slots':t['distance_threads']/(32*t['configured_warp_slots'])}
    return {'scope':'Recorded distance masks plus fixed source mapping; join CTA counts to NSYS. Not hardware occupancy or issued-instruction participation.',
        'geometry_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'modes':modes,
        'fixed3_groups_by_leaf_count':dict(groups),'rows':rows}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('geometry',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    with a.out.open('x') as f:json.dump(analyze(a.geometry),f,indent=2);f.write('\n')
