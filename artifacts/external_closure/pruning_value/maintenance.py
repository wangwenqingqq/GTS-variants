#!/usr/bin/env python3
"""Stable occurrence/content accounting over retained rebuild events; no online bound reuse."""
import argparse,json,struct,hashlib,time
from pathlib import Path
import numpy as np
from build import sha,save,outside_repo
if not __debug__:raise RuntimeError("Python assertions are required")
from analyze import table,NODE

def replay(n,events,states=None):
    base=np.arange(n,dtype=np.int64);occ=base.copy();alive=np.ones(n,bool);buffer=[];buffer_occ=[];next_id=n
    snapshots=[(base.copy(),occ.copy())];updates=[];rebuilds=[]
    for step,(flag,index) in enumerate(events):
        before=(len(base),len(buffer))
        if flag==0:
            original=int(base[index]);buffer.append(original);buffer_occ.append(next_id)
            updates.append(dict(step=step,action='insert',occurrence=next_id,vector_original_row=original));next_id+=1
            if len(buffer)==10:
                old=occ.copy();survivors=occ[alive];survivor_pos=np.flatnonzero(alive)
                base=np.r_[base[alive],buffer];occ=np.r_[survivors,buffer_occ];alive=np.ones(len(base),bool)
                rebuilds.append(dict(step=step,N=len(base),new_buffer_instances=len(buffer),removed_base_instances=len(old)-len(survivors),survivors=len(survivors),survivors_changed_physical_row=int(np.count_nonzero(survivor_pos!=np.arange(len(survivors)))),full_copied_vectors=len(base)))
                buffer=[];buffer_occ=[];snapshots.append((base.copy(),occ.copy()))
        elif flag==1:
            positions=np.flatnonzero(alive)
            if index<len(positions):
                p=positions[index];identifier=int(occ[p]);original=int(base[p]);alive[p]=False
            else:
                p=index-len(positions);identifier=buffer_occ.pop(p);original=buffer.pop(p)
            updates.append(dict(step=step,action='delete',occurrence=identifier,vector_original_row=original))
        else:assert flag in (2,3)
        if states:
            row=states[step];assert [int(row[k]) for k in ('step','flag','base_before','buffer_before','base_after','buffer_after')]==[step,int(flag),*before,len(base),len(buffer)]
    return snapshots,updates,rebuilds

def prepare(a):
    a.output.mkdir(exist_ok=False);records=json.loads(a.inputs.read_text())['records'];data=Path(records['initial']['data'])
    assert sha(data)==records['initial']['data_sha256'];h=np.fromfile(data,'<i4',count=3);d,n,metric=map(int,h);assert (n,d,metric)==(1000000,960,2)
    events=np.loadtxt(a.events,skiprows=1,dtype=np.int64);states=table(a.states);assert len(events)==len(states)==336
    snapshots,updates,rebuilds=replay(n,events,states);assert len(snapshots)==3 and len(rebuilds)==2
    for name,(lineage,occ) in zip(('initial','first_rebuilt','second_rebuilt'),snapshots):
        np.save(a.output/(name+'.lineage.npy'),lineage);np.save(a.output/(name+'.occurrence.npy'),occ)
        if name!='second_rebuilt':assert np.array_equal(lineage,np.load(Path(records[name]['snapshot'])/'lineage.npy'))
    x=np.memmap(data,dtype='<f4',offset=12,shape=(n,d));lineage=snapshots[2][0]
    with (a.output/'second.f32bin').open('xb') as f:
        f.write(struct.pack('<iii',d,len(lineage),2))
        for i in range(0,len(lineage),4096):f.write(x[lineage[i:i+4096]].tobytes())
    save(a.output/'PREPARED.json',dict(data_sha256=sha(data),events_sha256=sha(a.events),states_sha256=sha(a.states),second_data_sha256=sha(a.output/'second.f32bin'),updates=updates,rebuilds=rebuilds,all_operation_states_matched=True,existing_snapshot_lineages_matched=True))

def load_audit(folder):
    levels=sorted(folder.glob('level*.after_split.nodes'),key=lambda p:int(p.name.split('.')[0][5:]));assert levels
    label=levels[-1].name.split('.')[0];nodes=np.fromfile(levels[-1],NODE);empty=np.fromfile(folder/(label+'.after_split.empty'),'<i4');order=np.fromfile(folder/(label+'.sorted.order'),'<i4')
    return nodes,empty,order

def pairs(folder,lineage,occ):
    result=[]
    for file in sorted(folder.glob('level*.input.nodes')):
        stem=file.name[:-len('.input.nodes')];nodes=np.fromfile(file,NODE);flags=np.fromfile(folder/(stem+'.input.split'),'<i4');order=np.fromfile(folder/(stem+'.input.order'),'<i4');pivots=np.fromfile(folder/(stem+'.distance.pids'),'<i4')
        for nid in np.flatnonzero(flags):
            pid=pivots[nid]
            if pid<0:continue
            members=order[nodes[nid]['lid']:nodes[nid]['lid']+nodes[nid]['size']]
            result.append((members,int(pid)))
    # Occurrence-key range is frozen above the small update-created IDs.
    factor=2000000
    return np.concatenate([occ[m]*factor+occ[p] for m,p in result]),np.concatenate([lineage[m]*factor+lineage[p] for m,p in result])

def compare(old,new,old_line,new_line,old_occ,new_occ):
    an,ae,ao=load_audit(old);bn,be,bo=load_audit(new);assert len(an)==len(bn)
    count=dict(nonempty_nodes=0,same_member_occurrences=0,same_pivot_occurrence=0,same_pivot_vector=0,same_members_and_pivot_occurrence=0,address_only_nodes=0,stable_ID_sufficient_bound_reuse=0,changed_member_nodes=0,pivot_vector_changed_nodes=0)
    for nid in np.flatnonzero((be==0)&(bn['size']>0)):
        count['nonempty_nodes']+=1
        if ae[nid] or an[nid]['size']<=0:continue
        a,b=an[nid],bn[nid];am=ao[a['lid']:a['lid']+a['size']];bm=bo[b['lid']:b['lid']+b['size']]
        same=np.array_equal(np.sort(old_occ[am]),np.sort(new_occ[bm]));pold=int(a['pid']);pnew=int(b['pid'])
        po=(pold<0 and pnew<0) or (pold>=0 and pnew>=0 and old_occ[pold]==new_occ[pnew])
        pv=(pold<0 and pnew<0) or (pold>=0 and pnew>=0 and old_line[pold]==new_line[pnew])
        count['same_member_occurrences']+=int(same);count['same_pivot_occurrence']+=int(po);count['same_pivot_vector']+=int(pv)
        count['same_members_and_pivot_occurrence']+=int(same and po);count['changed_member_nodes']+=int(not same);count['pivot_vector_changed_nodes']+=int(not pv)
        physical=not np.array_equal(am,bm) or pold!=pnew
        count['address_only_nodes']+=int(same and po and physical)
        # A sufficient condition only: same pivot coordinates, each new vector already covered.
        reusable=pv and pnew>=0 and np.isin(new_line[bm],old_line[am]).all()
        count['stable_ID_sufficient_bound_reuse']+=int(reusable)
    old_pairs,old_vectors=pairs(old,old_line,old_occ);new_pairs,new_vectors=pairs(new,new_line,new_occ)
    count.update(build_object_pivot_evaluations=len(new_pairs),build_evaluations_identical_occurrence_pair=int(np.isin(new_pairs,np.unique(old_pairs)).sum()),build_evaluations_identical_vector_pair=int(np.isin(new_vectors,np.unique(old_vectors)).sum()),refit_object_pivot_evaluations=int(bn['size'][(be==0)&(bn['pid']>=0)].sum()),all_prior_bounds_retired_by_current_epoch_contract=True)
    # Also search exact stable regions across node addresses, not only equal heap slots.
    signatures={}
    for nid in np.flatnonzero((ae==0)&(an['size']>0)):
        a=an[nid];members=np.sort(old_occ[ao[a['lid']:a['lid']+a['size']]])
        digest=hashlib.sha256(members.tobytes()).digest();pid=int(a['pid']);pivot=int(old_line[pid]) if pid>=0 else -1
        signatures.setdefault((digest,pivot),[]).append(int(nid))
    matches=0
    for nid in np.flatnonzero((be==0)&(bn['size']>0)):
        b=bn[nid];members=np.sort(new_occ[bo[b['lid']:b['lid']+b['size']]])
        digest=hashlib.sha256(members.tobytes()).digest();pid=int(b['pid']);pivot=int(new_line[pid]) if pid>=0 else -1
        for old_nid in signatures.get((digest,pivot),[]):
            a=an[old_nid];old_members=np.sort(old_occ[ao[a['lid']:a['lid']+a['size']]])
            assert np.array_equal(members,old_members),'membership hash collision'
            matches+=1;break
    count['exact_member_occurrences_and_pivot_content_reusable_any_node']=matches
    return count

def contents(a):
    records=json.loads(a.inputs.read_text())['records'];data=Path(records['initial']['data'])
    assert sha(data)==records['initial']['data_sha256']
    h=np.fromfile(data,'<i4',count=3);d,n,_=map(int,h);x=np.memmap(data,dtype='<f4',offset=12,shape=(n,d))
    start=time.perf_counter();digests=np.empty(n,dtype='V32')
    for i in range(n):digests[i]=hashlib.sha256(x[i].tobytes()).digest()
    _,first,inverse,counts=np.unique(digests,return_index=True,return_inverse=True,return_counts=True)
    identity=first[inverse].astype(np.int64)
    for i in np.flatnonzero(identity!=np.arange(n)):
        assert x[i].tobytes()==x[identity[i]].tobytes(),'content digest collision'
    np.save(a.output/'content_ids.npy',identity)
    save(a.output/'CONTENT_IDENTITY.json',dict(data_sha256=sha(data),rows=n,unique_bitwise_FP32_vectors=len(first),duplicate_original_rows=n-len(first),hash_algorithm='SHA256 per complete FP32 row; every repeated digest checked against full coordinate bytes',content_ids_sha256=sha(a.output/'content_ids.npy'),CPU_seconds=time.perf_counter()-start))
    return identity

def analyze(a):
    prepared=json.loads((a.output/'PREPARED.json').read_text());names=['initial','first_rebuilt','second_rebuilt'];audits=[a.audits/'million_prefix_B1/build2',a.audits/'million_prefix_B1/build3',a.second_audit/'build0'];result=[]
    content=contents(a)
    for i in (1,2):
        old,new=names[i-1:i+1];v=compare(audits[i-1],audits[i],content[np.load(a.output/(old+'.lineage.npy'))],content[np.load(a.output/(new+'.lineage.npy'))],np.load(a.output/(old+'.occurrence.npy')),np.load(a.output/(new+'.occurrence.npy')))
        v.update(prepared['rebuilds'][i-1]);v['full_copy_payload_bytes']=v['N']*960*4;v['packed_republication_vectors']=v['N'];result.append(v)
    save(a.output/'MAINTENANCE_V2.json',dict(passed=True,rows=result,prepared_sha256=sha(a.output/'PREPARED.json'),caveat='Heap-node statistics plus exact stable-region matching across all old node addresses. Coordinate content identities include byte-verified duplicate original rows. Stable-ID subset criterion is sufficient, not exhaustive. Other bounds are not proved mathematically unsafe; all are invalidated by current pointer/epoch contract. No old bound was reused.',audit_hashes=[{p.name:sha(p) for p in folder.iterdir() if p.is_file()} for folder in audits]))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','analyze']);p.add_argument('--output',type=Path,required=True)
    for k in ('inputs','events','states','audits','second-audit'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();a.output=outside_repo(a.output);globals()[a.stage](a)
