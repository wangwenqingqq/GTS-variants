#!/usr/bin/env python3
"""Runnable CPU regression: address/index churn is not semantic churn."""
import tempfile,json
from pathlib import Path
import numpy as np
from analyze import Snapshot,diff,NODE,FIELDS

def fixture(root,reverse):
    root.mkdir();n=32;d=3;groups=list(range(4))[::(-1 if reverse else 1)]
    base=np.arange(n,dtype=np.int32)[::(-1 if reverse else 1)].copy()
    inverse=np.argsort(base);occ=np.concatenate([np.arange(g*8,(g+1)*8) for g in groups]);order=inverse[occ].astype('<i4')
    nodes=np.zeros(5,dtype=NODE);nodes[0]=(-1,0,n,0,0)
    for i,g in enumerate(groups,1):nodes[i]=(inverse[0],np.float32(g+1),8,(i-1)*8,1)
    plan={'regions':np.array([[i,8,1,1,i-1,0] for i in range(1,5)],dtype='<i4').reshape(-1),
          'leaf_slot':np.array([-1,0,8,16,24],dtype='<i4'),'slot_pid':order,'leaves':np.arange(1,5,dtype='<i4'),
          'owners':np.repeat(np.arange(4,dtype='<i4'),8),'parents':np.array([0],dtype='<i4'),'skeleton':np.array([0],dtype='<i4'),
          'level_offsets':np.array([0,1],dtype='<i4'),'skeleton_offsets':np.array([0,1],dtype='<i4')}
    data=(np.arange(n*d,dtype=np.float32).reshape(n,d)+1)[base];pack=data.reshape(1,32,d).transpose(0,2,1).copy()
    lo=np.array([0]+[g+1 for g in groups],dtype='<f8');hi=np.array([np.inf]+[g+2 for g in groups],dtype='<f8')
    payload={'base.i32':base,'deleted.i32':np.zeros(n,dtype='<i4'),'buffer.i32':np.empty(0,dtype='<i4'),
             'buffer_positions.i32':np.empty(0,dtype='<i4'),'live.i32':np.arange(n,dtype='<i4'),'nodes.bin':nodes,'empty.i32':np.zeros(5,dtype='<i4'),'order.i32':order,
             'lo.f64':lo,'hi.f64':hi,'packed.f32':pack,**{'plan_'+k+'.i32':v for k,v in plan.items()}}
    for name,v in payload.items():v.tofile(root/name)
    meta={'schema':1,'pre':not reverse,'rebuild':1,'step':4,'n':n,'d':d,'nn':5,'buffer':0,'live':n,'leaves':4,
          'insert_ids':[],'delete_ids':[],'plan_entries':sum(x.size for x in plan.values()),'build_distance_tasks':32,
          'sort_api_input_slots':32,'build_active_split_nodes':1,'build_created_children':4,'refit_distance_tasks':32}
    (root/'meta.json').write_text(json.dumps(meta))
def main():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp);fixture(p/'a',False);fixture(p/'b',True);a=Snapshot(p/'a');b=Snapshot(p/'b');r=diff(a,b)
        assert r['positions']['moved']==32 and r['leaf']['unchanged_membership']==4
        assert r['leaf']['objects_changed_membership']==0
        assert r['nodes']['fully_unchanged']==4 and r['nodes']['topology_changed']==1 and r['nodes']['numeric_only_changed']==0
        assert r['numeric']['canonical_identical_same_topology']==8 and r['numeric']['raw_positional_bit_changed']==8
        assert r['pack']['physical_bit_changed']==96 and r['pack']['survivor_coordinate_changed']==0
        assert r['plan']['canonical_changed']==0 and r['plan']['raw_changed']>0
        assert r==diff(a,b)
    print('PASS: exact identities, numeric bits, physical/semantic pack/plan separation, deterministic diff')
if __name__=='__main__':main()
