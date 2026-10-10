#!/usr/bin/env python3
"""Frozen local block ownership simulation; modeled bytes, no timing claim."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from run import HERE,sha,save,outside_repo,interval,radius_upper,rejected,stats,raw
if not __debug__:raise RuntimeError('Assertions required')

def bind_static(root,verification):
    proof=json.loads((root/'PROOF.json').read_text())
    assert verification['passed'] and verification['proof_sha256']==sha(root/'PROOF.json'),'verification belongs to another campaign'
    for name,digest in proof['raw_files'].items():assert sha(root/name)==digest,('static raw mutation',name)
    assert all(sha(root/name)==digest for name,digest in verification['result_hashes'].items())
    return proof

class Ownership:
    def __init__(self,occ,permutation,scores,p,active,max_id):
        self.occ=occ;self.perm=permutation;self.scores=scores[:p];self.p=p;self.active=active;self.n=len(occ);self.starts=np.arange(0,self.n,active);self.initial_blocks=len(self.starts)
        self.owner=np.full(max_id+1,-1,dtype=np.int32);self.slot=self.owner.copy();self.row=self.owner.copy();self.row[occ]=np.arange(self.n)
        ordered=occ[permutation];self.owner[ordered]=np.arange(self.n)//active;self.slot[ordered]=np.arange(self.n)%active
        self.count=np.zeros(self.initial_blocks+128,dtype=np.int32);self.count[:self.initial_blocks]=np.minimum(active,self.n-self.starts)
        norms=np.sqrt(self.scores);self.norms=norms
        self.sums=np.zeros((p,len(self.count)));self.sums[:,:self.initial_blocks]=np.add.reduceat(norms[:,permutation],self.starts,axis=1)
        lo,hi=interval(self.scores,960);self.lower=lo;self.upper=hi
        self.lo=np.zeros((p,len(self.count)));self.hi=self.lo.copy();self.lo[:,:self.initial_blocks]=np.minimum.reduceat(lo[:,permutation],self.starts,axis=1);self.hi[:,:self.initial_blocks]=np.maximum.reduceat(hi[:,permutation],self.starts,axis=1)
        self.nb=self.initial_blocks;self.modified={};self.changed=set();self.moved=set();self.existing_move_events=0;self.all_move_events=0;self.splits=0;self.refreshes=0;self.max_initial_occ=int(occ.max());self.event_records=[]
    def slots(self,b):
        if b not in self.modified:
            a=np.full(256,-1,dtype=np.int64)
            if b<self.initial_blocks:
                ids=self.occ[self.perm[b*self.active:min((b+1)*self.active,self.n)]];a[:len(ids)]=ids
            self.modified[b]=a
        return self.modified[b]
    def refresh(self,b):
        slots=self.slots(b);members=slots[slots>=0];rows=self.row[members];self.count[b]=len(members)
        if len(rows):
            self.sums[:,b]=self.norms[:,rows].sum(axis=1);self.lo[:,b]=self.lower[:,rows].min(axis=1);self.hi[:,b]=self.upper[:,rows].max(axis=1)
            assert np.all(self.lower[:,rows]>=self.lo[:,b,None]) and np.all(self.upper[:,rows]<=self.hi[:,b,None])
        else:self.sums[:,b]=0;self.lo[:,b]=0;self.hi[:,b]=0
        assert len(set(map(int,members)))==len(members) and np.all(self.owner[members]==b) and np.array_equal(self.slot[members],np.flatnonzero(slots>=0))
        self.changed.add(b);self.refreshes+=1
    def apply(self,e,row):
        identifier=int(e['occurrence']);action=e['action'];self.row[identifier]=row;before_move=self.existing_move_events
        if action=='delete':
            b=int(self.owner[identifier]);assert b>=0;slot=int(self.slot[identifier]);assert self.slots(b)[slot]==identifier
            self.slots(b)[slot]=-1;self.owner[identifier]=-1;self.slot[identifier]=-1;affected=[b]
        else:
            assert action=='insert' and self.owner[identifier]<0
            empty=np.flatnonzero(self.count[:self.nb]==0)
            if len(empty):b=int(empty[0])
            else:
                centroid=self.sums[:,:self.nb]/self.count[None,:self.nb];cost=np.square(centroid-self.norms[:,row,None]).sum(axis=0);b=int(np.argmin(cost))
            slots=self.slots(b);vacant=np.flatnonzero(slots<0);affected=[b]
            if len(vacant):
                j=int(vacant[0]);slots[j]=identifier;self.owner[identifier]=b;self.slot[identifier]=j
            else:
                ids=np.r_[slots,identifier];rows=self.row[ids];indices=np.lexsort((ids,self.norms[0,rows]));keep=set(map(int,ids[indices[:128]]));transfer=ids[indices[128:]]
                new=self.nb;self.nb+=1;assert self.nb<=len(self.count);newslots=self.slots(new);affected.append(new);self.splits+=1
                for j,v in enumerate(slots.copy()):
                    if int(v) not in keep:slots[j]=-1
                for j,v in enumerate(transfer):
                    newslots[j]=v;self.owner[v]=new;self.slot[v]=j
                    if v!=identifier:
                        self.all_move_events+=1
                        if v<=self.max_initial_occ:self.existing_move_events+=1;self.moved.add(int(v))
                if identifier in keep:
                    j=int(np.flatnonzero(slots<0)[0]);slots[j]=identifier;self.owner[identifier]=b;self.slot[identifier]=j
        for b in affected:self.refresh(b)
        self.event_records.append(dict(step=e['step'],action=action,occurrence=identifier,affected_blocks=affected,existing_move_events=self.existing_move_events-before_move,live_objects=int(self.count[:self.nb].sum())))
    def validate_delta(self,events,end_occ,end_line,line):
        touched=[b for b in self.changed if b<self.initial_blocks]
        old=np.concatenate([self.occ[self.perm[b*self.active:min((b+1)*self.active,self.n)]] for b in touched]) if touched else np.empty(0,dtype=np.int64)
        expected=set(map(int,old));new_ids={}
        for e in events:
            i=int(e['occurrence'])
            if e['action']=='delete':expected.remove(i)
            else:expected.add(i);new_ids[i]=int(e['vector_original_row'])
        actual=np.concatenate([self.slots(b)[self.slots(b)>=0] for b in sorted(self.changed)])
        assert len(actual)==len(set(map(int,actual))) and set(map(int,actual))==expected
        old_deleted=np.setdiff1d(self.occ,end_occ);new_alive=np.setdiff1d(end_occ,self.occ)
        delete_events={int(e['occurrence']) for e in events if e['action']=='delete'};insert_events={int(e['occurrence']) for e in events if e['action']=='insert'}
        assert set(map(int,old_deleted))==delete_events-insert_events
        assert set(map(int,new_alive))==insert_events-delete_events
        assert int(self.count[:self.nb].sum())==len(end_occ)
        sort=np.argsort(end_occ);sorted_occ=end_occ[sort];pos=np.searchsorted(sorted_occ,actual);assert np.array_equal(sorted_occ[pos],actual)
        assert np.array_equal(end_line[sort[pos]],line[self.row[actual]])
        return hashlib.sha256(np.sort(actual).tobytes()).hexdigest()
    def query(self,refs,qids,r):
        rows=[]
        qlo,qhi=interval(self.scores[:,qids],960)
        for qi,q in enumerate(qids):
            req=np.zeros(self.nb,dtype=bool)
            hits=np.flatnonzero(refs[qi]<=r*r)
            # Original occurrences, excluding actual deletes; inserts are added from exact source rows.
            live=self.owner[self.occ[hits]];req[live[live>=0]]=True
            for b in self.changed:
                ids=self.slots(b);ids=ids[ids>=0];req[b]=bool(np.any(refs[qi,self.row[ids]]<=r*r))
            keep=~np.any(rejected(self.lo[:,:self.nb],self.hi[:,:self.nb],qlo[:,qi,None],qhi[:,qi,None],radius_upper(r,960)),axis=0);keep&=self.count[:self.nb]>0
            assert np.all(keep[req]),'post-update false prune'
            rows.append(dict(query=qi,qid=q,total_blocks=self.nb,oracle_required_blocks=int(req.sum()),surviving_blocks=int(keep.sum()),surviving_block_fraction=float(keep.mean()),surviving_active_objects=int(self.count[:self.nb][keep].sum()),false_prune_blocks=int(np.count_nonzero(req&~keep))))
        return rows

def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);root=outside_repo(a.run);contract=json.loads((HERE/'D_CONTRACT.json').read_text());prepared=json.loads((a.maintenance/'PREPARED.json').read_text());assert sha(a.maintenance/'PREPARED.json')==contract['prepared_sha256']
    assert json.loads((root/'DECISION.json').read_text())['decision']=='CONDITIONAL'
    bind_static(root,json.loads(a.static_verification.read_text()))
    source={p.name:sha(p) for p in [HERE/'update.py',HERE/'D_CONTRACT.json',HERE/'run.py']};input_files=[a.maintenance/'PREPARED.json'];before_hashes={a.maintenance/'PREPARED.json':sha(a.maintenance/'PREPARED.json')}
    save(out/'REGISTERED.json',dict(contract_sha256=sha(HERE/'D_CONTRACT.json'),source_hashes=source,static_proof_sha256=sha(root/'PROOF.json'),static_verification_sha256=sha(a.static_verification),user_authorized_diagnostic_continuation=True,GPU_processes=0))
    result=[];bindings={};previous_step=-1
    for spec in contract['intervals']:
        name=spec['snapshot'];end=spec['end'];occ=np.load(a.maintenance/(name+'.occurrence.npy'));line=np.load(a.maintenance/(name+'.lineage.npy'));end_occ=np.load(a.maintenance/(end+'.occurrence.npy'));end_line=np.load(a.maintenance/(end+'.lineage.npy'))
        for label in (name,end):
            for suffix,pins in [('occurrence',contract['occurrence_sha256']),('lineage',contract['lineage_sha256'])]:
                f=a.maintenance/(label+'.'+suffix+'.npy');assert sha(f)==pins[label];input_files.append(f);before_hashes[f]=sha(f)
        events=[e for e in prepared['updates'] if previous_step<e['step']<=spec['through_step']];previous_step=spec['through_step'];ni=sum(e['action']=='insert' for e in events);nd=sum(e['action']=='delete' for e in events);assert (ni,nd)==(spec['actual_inserts'],spec['actual_deletes'])
        original_to_row=np.full(int(line.max())+1,-1,dtype=np.int32);original_to_row[line]=np.arange(len(line));event_rows=[int(original_to_row[e['vector_original_row']]) for e in events];assert min(event_rows)>=0
        binding=json.loads((root/(name+'_AB_CHECKPOINT.json')).read_text());qids=binding['queries'];refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(len(occ),)) for q in qids]);assert {str(q):sha(a.references/name/(str(q)+'.f64')) for q in qids}==binding['reference_file_hashes']
        for q in qids:
            f=a.references/name/(str(q)+'.f64');before_hashes[f]=sha(f)
        max_id=max(int(occ.max()),max(e['occurrence'] for e in events));radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0])
        for layout in contract['layouts']:
            perm=np.load(root/(name+'_'+layout+'.npy'));assert sha(root/(name+'_'+layout+'.npy'))==binding['layout_hashes'][layout]
            before_hashes[root/(name+'_'+layout+'.npy')]=sha(root/(name+'_'+layout+'.npy'))
            for strategy in contract['strategies']:
                scores=np.load(root/(name+'_'+strategy+'_scores.npy'),mmap_mode='r');assert sha(root/(name+'_'+strategy+'_scores.npy'))==json.loads((root/'PROOF.json').read_text())['raw_files'][name+'_'+strategy+'_scores.npy']
                before_hashes[root/(name+'_'+strategy+'_scores.npy')]=sha(root/(name+'_'+strategy+'_scores.npy'))
                for p in contract['pivots']:
                    for active in contract['initial_active_capacities']:
                        model=Ownership(occ,perm,scores,p,active,max_id);before=model.query(refs,qids,radius)
                        for e,row in zip(events,event_rows):model.apply(e,row)
                        delta=model.validate_delta(events,end_occ,end_line,line);after=model.query(refs,qids,radius)
                        result.append(dict(snapshot=name,ending_snapshot=end,layout=layout,strategy=strategy,pivot_count=p,slack_fraction=(256-active)/256,active_capacity=active,physical_capacity=256,actual_inserts=ni,actual_deletes=nd,net_entering_base=len(np.setdiff1d(end_occ,occ)),net_removing_base=len(np.setdiff1d(occ,end_occ)),initial_total_blocks=model.initial_blocks,final_total_blocks=model.nb,changed_blocks=len(model.changed),changed_certificates=len(model.changed),changed_certificate_intervals=p*len(model.changed),invalidated_block_fraction=len(model.changed)/model.initial_blocks,changed_block_fraction=len(model.changed)/model.initial_blocks,moved_existing_objects=len(model.moved),moved_existing_events=model.existing_move_events,all_vector_move_events=model.all_move_events,inserted_objects=ni,deleted_objects=nd,bytes_moved=(ni+model.all_move_events)*960*4,coordinate_payload_model_bytes=(ni+model.all_move_events)*960*4,certificate_refresh_calls=model.refreshes,certificate_write_model_bytes=16*p*model.refreshes,block_splits=model.splits,block_merges=0,global_repartition_events=0,movement_amplification=len(model.moved)/(ni+nd),event_movement_amplification=model.existing_move_events/(ni+nd),final_membership_delta_sha256=delta,final_live_objects=int(model.count[:model.nb].sum()),initial_query_survival_mean=float(np.mean([r['surviving_block_fraction'] for r in before])),post_update_query_survival_mean=float(np.mean([r['surviving_block_fraction'] for r in after])),initial_queries=before,post_update_queries=after,events=model.event_records))
        bindings[name]=dict(events=events,ending_snapshot=end,affected_slots_checked_after_each_update=True,all_final_occurrence_and_lineage_deltas_matched=True);print(name,'144 update simulations complete',flush=True)
    assert len(result)==288 and {p.name:sha(p) for p in [HERE/'update.py',HERE/'D_CONTRACT.json',HERE/'run.py']}==source
    assert {p:sha(p) for p in before_hashes}==before_hashes,'input mutation'
    hashes={p.name:sha(p) for p in set(input_files)}
    save(out/'UPDATE_LOCALITY.json',dict(status='completed_diagnostic_only',rows=result,bindings=bindings,scope=contract['scope'],static_decision='CONDITIONAL',all_post_update_false_prune_blocks=sum(q['false_prune_blocks'] for r in result for q in r['post_update_queries'])))
    save(out/'PROOF.json',dict(passed=True,source_hashes=source,input_hashes=hashes,registered_sha256=sha(out/'REGISTERED.json'),update_results_sha256=sha(out/'UPDATE_LOCALITY.json'),simulations=len(result),all_post_update_queries=288*32,actual_false_prune_blocks=0,GPU_processes=0,original_query_gate_not_promoted=True))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('run','maintenance','references','static-verification','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
