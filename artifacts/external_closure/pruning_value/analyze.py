#!/usr/bin/env python3
"""Exhaustive output checking, exact candidate replay and non-overlapping pruning accounting."""
import argparse,csv,json,time,math
from pathlib import Path
import numpy as np
from build import sha,save,outside_repo
if not __debug__:raise RuntimeError('Python assertions are required')
NODE=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('leaf','<i4')])

def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def write_csv(p,rows):
    with Path(p).open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def tree(root):
    nodes=np.fromfile(root/'nodes',NODE);empty=np.fromfile(root/'empty','<i4');order=np.fromfile(root/'order','<i4')
    assert np.array_equal(np.sort(order),np.arange(len(order)))
    live=(empty==0)&(nodes['size']>0);depth=np.zeros(len(nodes),np.int32)
    for i in range(1,len(nodes)):depth[i]=depth[(i-1)//10]+1
    return nodes,live,order,depth

def min_truth(nodes,live,order,ref):
    leaves=np.flatnonzero(live & (nodes['leaf']!=0));leaves=leaves[np.argsort(nodes['lid'][leaves])]
    assert nodes['lid'][leaves[0]]==0 and np.array_equal(np.cumsum(nodes['size'][leaves])[:-1],nodes['lid'][leaves[1:]])
    result=np.full(len(nodes),np.inf);result[leaves]=np.minimum.reduceat(ref[order],nodes['lid'][leaves])
    for nid in np.flatnonzero(live&(nodes['leaf']==0))[::-1]:result[nid]=np.min(result[nid*10+1:min(nid*10+11,len(nodes))])
    return result

def check_answers(root,reference,qids):
    meta=json.loads((root/'META.json').read_text());manifest=json.loads((reference/'REFERENCE.json').read_text())
    assert (meta['N'],meta['D'])==(manifest['N'],manifest['D'])
    refs={}
    for q in qids:
        p=reference/f'{q}.f64';assert p.stat().st_size==meta['N']*8;assert sha(p)==manifest['files'][str(q)];refs[q]=np.fromfile(p,'<f8');assert len(refs[q])==meta['N']
    assert (root/'ids').stat().st_size%4==0 and (root/'fields').stat().st_size%4==0,'trailing partial output item'
    ids=np.fromfile(root/'ids','<i4');fields=np.fromfile(root/'fields','<f4');rows=table(root/'queries.csv');offset=0
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);r2=radius*radius
    for row in rows:
        for key in ('host_ms','front_ms','verify_ms','output_ms'):
            if key in row:assert math.isfinite(float(row[key])) and float(row[key])>=0,(key,'invalid time')
        q=int(row['qid']);assert q==qids[int(row['query'])];count=int(row['count']);assert int(row['offset'])==offset
        actual=ids[offset:offset+count];field=fields[offset:offset+count];idx=np.argsort(actual)
        expected=np.flatnonzero(refs[q]<=r2).astype(np.int32);distance=np.sqrt(refs[q][expected]).astype(np.float32)
        assert np.array_equal(actual[idx],expected),(row,'IDs')
        assert np.array_equal(field[idx].view(np.uint32),distance.view(np.uint32)),(row,'distance fields')
        offset+=count
    assert offset==len(ids)==len(fields)
    return rows,refs,r2

def bind_tree(root,audit):
    levels=sorted(audit.glob('level*.after_split.nodes'),key=lambda p:int(p.name.split('.')[0][5:]));assert levels
    prefix=levels[-1].name.split('.')[0]
    mapping={'nodes':f'{prefix}.after_split.nodes','empty':f'{prefix}.after_split.empty','order':f'{prefix}.sorted.order','lo':'refit.lo','hi':'refit.hi'}
    result={}
    for key,old in mapping.items():
        result[key]=sha(root/key);assert result[key]==sha(audit/old),(key,'not the registered actual tree')
    return result

def capture(a):
    qids=list(map(int,a.qids.read_text().split()));assert len(qids)==32
    rows,refs,r2=check_answers(a.root,a.reference,qids);assert [(int(r['pass']),int(r['mode']),int(r['query'])) for r in rows]==[(0,0,q) for q in range(32)]
    binding=bind_tree(a.root,a.audit)
    nodes,live,order,depth=tree(a.root);n=len(order);nn=len(nodes);layers=[];bins=[];query=[];masks=[];lists=[]
    cpu_ms=0;raw_bytes=0
    for qi,qid in enumerate(qids):
        p=a.root/f'q{qi}';tested=np.fromfile(p/'nodes','<u8');pivots=np.fromfile(p/'pivots','<u8');objects=np.fromfile(p/'objects','<u8');active=np.fromfile(p/'active','<i4');ll=np.fromfile(p/'leaf_list','<i4');times=np.fromfile(p/'levels_ms','<f4')
        assert len(tested)==len(pivots)==len(active)==nn and len(objects)==n
        assert max(tested.max(),pivots.max(),objects.max())<=1
        assert np.all(tested[~live]==0) and np.all(pivots<=tested)
        start=time.perf_counter();mask=objects.astype(np.uint8);candidate=np.zeros(n,np.uint8)
        for leaf in ll[ll>=0]:candidate[order[nodes['lid'][leaf]:nodes['lid'][leaf]+nodes['size'][leaf]]]+=1
        assert np.array_equal(mask,candidate);cpu_ms+=(time.perf_counter()-start)*1000
        raw_bytes+=tested.nbytes+pivots.nbytes+objects.nbytes+active.nbytes+ll.nbytes
        masks.append(mask);lists.append(ll);ids=np.flatnonzero(mask);hits=int(np.count_nonzero(refs[qid]<=r2))
        assert np.all(mask[refs[qid]<=r2])
        truth=min_truth(nodes,live,order,refs[qid]);unresolved=n
        query.append(dict(query=qi,qid=qid,N=n,candidates=int(mask.sum()),true_hits=hits,physical_blocks32=len(np.unique(ids//32)),physical_blocks256=len(np.unique(ids//256)),total_blocks32=(n+31)//32,total_blocks256=(n+255)//256,pivot_evaluations=int(pivots.sum()),unique_query_pivot_pairs=len(np.unique(nodes['pid'][pivots>0]))))
        for level in range(1,int(depth[live].max())+1):
            t=(tested>0)&(depth==level);kept=t&(active!=0);pruned=t&(active==0);lost=int(nodes['size'][pruned].sum());unresolved-=lost
            nohit=truth>r2;must=kept&~nohit;missed=kept&nohit;pv=(pivots>0)&(depth==level)
            row=dict(query=qi,qid=qid,level=level,tested_nodes=int(t.sum()),pivot_evaluations=int(pivots[pv].sum()),unique_query_pivot_pairs=len(np.unique(nodes['pid'][pv])),newly_excluded_live_objects=lost,unresolved_live_objects=unresolved,kept_nodes_with_true_hit=int(must.sum()),kept_nodes_no_hit=int(missed.sum()),kept_no_hit_objects_at_this_level=int(nodes['size'][missed].sum()),candidate_objects=int(mask.sum()),true_hits=hits,physical_blocks32=query[-1]['physical_blocks32'],physical_blocks256=query[-1]['physical_blocks256'],observer_level_ms=float(times[level-1]))
            layers.append(row)
            for low,high in [(1,20),(21,256),(257,4096),(4097,100000),(100001,n)]:
                b=t&(nodes['size']>=low)&(nodes['size']<=high)
                if b.any():bins.append(dict(query=qi,qid=qid,level=level,size_min=low,size_max=high,tested=int(b.sum()),kept_with_hit=int((b&must).sum()),kept_without_hit=int((b&missed).sum()),pruned=int((b&pruned).sum())))
        assert unresolved==int(mask.sum()),'ancestor overlap or early-leaf loss'
    a.output.mkdir(exist_ok=False)
    np.stack(masks).tofile(a.output/'masks');np.stack(lists).tofile(a.output/'leaf_lists')
    write_csv(a.output/'layers.csv',layers);write_csv(a.output/'subtree_sizes.csv',bins);write_csv(a.output/'queries.csv',query)
    save(a.output/'CAPTURE.json',dict(passed=True,tree_binding=binding,reference_sha256=sha(a.reference/'REFERENCE.json'),exact_outputs=len(rows),cache_mask_bytes=32*n,cache_leaf_bytes=sum(x.nbytes for x in lists),cache_CPU_construct_ms=cpu_ms,observer_D2H_bytes=raw_bytes,cache_hashes={k:sha(a.output/k) for k in ('masks','leaf_lists')},CPU_scope='Host expansion/check of copied actual leaf lists and observed object counters; NOT an optimized online GPU task builder; excludes disk and observer D2H time'))

def timing(a):
    qids=list(map(int,a.qids.read_text().split()));rows,_,_=check_answers(a.root,a.reference,qids);binding=bind_tree(a.root,a.audit)
    expected=[(-1,m,q) for m in range(4) for q in range(8)]+[(p,m,q) for p in range(4) for m in (range(4) if p%2==0 else range(3,-1,-1)) for q in range(32)]
    assert [(int(r['pass']),int(r['mode']),int(r['query'])) for r in rows]==expected
    observations=[]
    for p in range(4):
        for m in range(4):
            group=[r for r in rows if int(r['pass'])==p and int(r['mode'])==m]
            observations.append(dict(pass_id=p,mode=m,**{k:sum(float(r[k]) for r in group) for k in ('host_ms','front_ms','verify_ms','output_ms')}))
    a.output.mkdir(exist_ok=False);write_csv(a.output/'passes.csv',observations)
    save(a.output/'TIMING.json',dict(passed=True,tree_binding=binding,reference_sha256=sha(a.reference/'REFERENCE.json'),exact_outputs=len(rows),scope='fixed-query diagnosis, no CI/promotion; replay excludes candidate generation',medians={m:{k:float(np.median([r[k] for r in observations if r['mode']==m])) for k in ('host_ms','front_ms','verify_ms','output_ms')} for m in range(4)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['capture','timing'])
    for k in ('root','reference','qids','audit','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=outside_repo(a.output);globals()[a.stage](a)
