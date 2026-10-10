#!/usr/bin/env python3
"""Audit exact sidecar records. All scheduling estimates are static simulations."""
import argparse,array,hashlib,json,math,struct
from collections import Counter
from pathlib import Path
ROW=struct.Struct('<3f7I')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pack(sizes,limit):
    bins=0;used=0;leaves=0
    for size in sizes:
        assert 0<size<=32
        if used+size>32 or leaves==limit:bins+=1;used=leaves=0
        used+=size;leaves+=1
    return bins+bool(leaves)
def analyze(index,geometry,result,oracle):
    raw=index.read_bytes();n,d,h,c=struct.unpack_from('<4i',raw)
    ids=struct.unpack_from(f'<{n}i',raw,16);offset=16+4*n
    nodes=list(struct.iter_unpack('<ifiii',raw[offset:offset+20*c]))
    flags=struct.unpack_from(f'<{c}i',raw,offset+20*c)
    owner=array.array('i',[-1])*n;leaves=set()
    for nid,node in enumerate(nodes):
        if not flags[nid] and node[4] and node[2]>0:
            leaves.add(nid)
            for obj in ids[node[3]:node[3]+node[2]]:assert owner[obj]==-1;owner[obj]=nid
    assert min(owner)>=0
    raw=result.read_bytes();rn,rd,q,k=struct.unpack_from('<4i',raw);assert (rn,rd)==(n,d)
    rid=struct.unpack_from(f'<{q*k}i',raw,16);dist=struct.unpack_from(f'<{q*k}f',raw,16+4*q*k)
    references=json.loads(oracle.read_text())['records'];assert len(references)==q
    rows=[]
    with geometry.open('rb') as f:
        assert struct.unpack('<4i',f.read(16))==(0x4c474531,n,d,c)
        for qi,ref in enumerate(references):
            qid,pivots,pivotdims=struct.unpack('<iQQ',f.read(20));assert qid==ref['qid']
            data=f.read(c*ROW.size);assert len(data)==c*ROW.size
            winners=rid[qi*k:(qi+1)*k];winner_leaves={owner[x] for x in winners}
            tie=ref['ties'][str(k)];eligible=set(tie['strictly_closer_ids']+tie['boundary_ids'])
            eligible_leaves={owner[x] for x in eligible};final=dist[(qi+1)*k-1]
            totals=Counter();sizes=Counter();active=Counter();validhist=Counter();acceptedhist=Counter();sequence={};seen=set();bounds=[];lower=[]
            for nid,r in enumerate(ROW.iter_unpack(data)):
                lb,nb,eb,tested,passed,visits,vm,cm,am,task=r
                if tested==1:
                    totals['node_bound_tests']+=1;totals['node_bound_passes']+=passed
                    if nid in leaves:
                        totals['leaf_bound_tests']+=1;totals['leaf_bound_rejections']+=not passed
                    assert passed==(lb<=nb)
                elif tested==2:totals['nodes_labelled_without_bound']+=1
                else:assert tested==0 and not passed
                if not visits:
                    assert not(vm or cm or am);continue
                assert visits==1 and nid in leaves and passed==1
                assert tested in (1,2) and (tested!=1 or lb<=nb)
                size=nodes[nid][2];objs=ids[nodes[nid][3]:nodes[nid][3]+size]
                assert vm==(1<<size)-1
                expected=sum(1<<i for i,x in enumerate(objs) if x!=qid)
                assert cm==expected and am&~vm==0
                for winner in winners:
                    if owner[winner]==nid:assert am&(1<<objs.index(winner))
                assert task not in sequence;sequence[task]=size;seen.add(nid)
                work=cm.bit_count();valid=vm.bit_count();accept=am.bit_count()
                totals['visited_leaves']+=1;totals['valid_objects']+=valid;totals['distance_objects']+=work;totals['accepted_objects']+=accept
                totals['leaf_distance_dimensions']+=work*d;totals['launched_ctas']+=1;totals['launched_warps']+=16
                totals['distance_active_warps']+=bool(work);totals['zero_distance_warps']+=16-bool(work)
                totals['distance_warps_at_most_8_lanes']+=0<work<=8
                totals['no_disk_survivor_leaves']+=accept==0
                totals['no_returned_topk_leaves']+=nid not in winner_leaves
                totals['no_legal_topk_member_leaves']+=nid not in eligible_leaves
                totals['online_existing_bound_prunable']+=tested==1 and lb>eb
                totals['node_to_leaf_bound_changes']+=tested==1 and nb!=eb
                totals['missing_leaf_bound']+=tested!=1
                totals['retrospective_lower_above_final_kth']+=tested==1 and lb>final
                sizes[size]+=1;active[work]+=1;validhist[valid]+=1;acceptedhist[accept]+=1
                bounds.append(eb);lower.append(lb)
            assert winner_leaves<=seen and len(sequence)==totals['visited_leaves']
            assert set(sequence)==set(range(len(sequence)))
            ordered=[sequence[i] for i in range(len(sequence))]
            packing={str(limit):pack(ordered,limit) for limit in (2,3,32)}
            rows.append({'qid':qid,'totals':dict(totals),'pivot_distances':pivots,'pivot_dimensions':pivotdims,
                'all_distance_dimensions':pivotdims+totals['leaf_distance_dimensions'],
                'objects_per_leaf':dict(sizes),'distance_lanes_per_object_warp':dict(active),
                'valid_lanes_per_object_warp':dict(validhist),'accepted_objects_per_leaf':dict(acceptedhist),
                'entry_bound_minmax':[min(bounds),max(bounds)],'leaf_lower_minmax':[min(lower),max(lower)],
                'final_kth_euclidean':final,'returned_topk_leaf_count':len(winner_leaves),
                'packing_structural_warps':packing})
        assert not f.read(1),'extra sidecar records'
    totals=Counter();hist={name:Counter() for name in ('objects_per_leaf','distance_lanes_per_object_warp','accepted_objects_per_leaf')}
    for row in rows:
        totals.update(row['totals'])
        for name in hist:hist[name].update(row[name])
    return {'scope':'GPU work-participation sidecars plus CPU retrospective classification; not timing or hardware occupancy',
      'index_sha256':sha(index),'geometry_sha256':sha(geometry),'result_sha256':sha(result),'oracle_sha256':sha(oracle),
      'N':n,'D':d,'Q':q,'K':k,'totals':dict(totals),
      'all_distance_dimensions':sum(x['all_distance_dimensions'] for x in rows),
      'pivot_distances':sum(x['pivot_distances'] for x in rows),'histograms':{k:dict(v) for k,v in hist.items()},
      'packing_structural_warps':{key:sum(x['packing_structural_warps'][key] for x in rows) for key in ('2','3','32')},
      'rows':rows}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('index','geometry','result','oracle','out'):p.add_argument(name,type=Path)
    a=p.parse_args();assert not a.out.exists();r=analyze(a.index,a.geometry,a.result,a.oracle)
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['totals'],indent=2))
