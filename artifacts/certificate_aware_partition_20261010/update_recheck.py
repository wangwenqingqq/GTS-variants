#!/usr/bin/env python3
"""Two bounded, independently initialized update intervals; no timing claims."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from partition import (HERE, BASE, sha, save, outside_repo, raw, make_partition,
                       bind_inputs, source_hashes, decide, interval, radius_upper)
from update import Ownership
from verify_partition import independent_partition


class VariableOwnership(Ownership):
    """Reuse the prior update rules, retaining the actual variable block boundaries."""
    def __init__(self,occ,perm,starts,scores,max_id):
        super().__init__(occ,perm,scores,4,240,max_id)
        assert len(starts)==self.initial_blocks and starts[0]==0
        self.starts=starts.copy();ends=np.r_[starts[1:],self.n];sizes=ends-starts
        assert np.all((sizes>0)&(sizes<=240))
        ordered=occ[perm]
        self.owner[ordered]=np.repeat(np.arange(len(starts)),sizes)
        self.slot[ordered]=np.arange(self.n)-np.repeat(starts,sizes)
        self.count[:self.initial_blocks]=sizes
        self.sums[:,:self.initial_blocks]=np.add.reduceat(self.norms[:,perm],starts,axis=1)
        self.lo[:,:self.initial_blocks]=np.minimum.reduceat(self.lower[:,perm],starts,axis=1)
        self.hi[:,:self.initial_blocks]=np.maximum.reduceat(self.upper[:,perm],starts,axis=1)

    def slots(self,b):
        if b not in self.modified:
            a=np.full(256,-1,dtype=np.int64)
            if b<self.initial_blocks:
                start=self.starts[b];end=self.starts[b+1] if b+1<self.initial_blocks else self.n
                ids=self.occ[self.perm[start:end]];a[:len(ids)]=ids
            self.modified[b]=a
        return self.modified[b]

    def check_full(self,end_occ,end_line,line,refs,qids,radius,observed):
        """Reconcile every live occurrence/slot and independently reconstruct oracle blocks."""
        live=[];row_ids=[];owners=[]
        for b in range(self.nb):
            slots=self.slots(b);ids=slots[slots>=0];rows=self.row[ids]
            assert self.count[b]==len(ids) and np.all(self.owner[ids]==b)
            assert np.array_equal(self.slot[ids],np.flatnonzero(slots>=0))
            if len(ids):
                assert np.array_equal(self.lo[:,b],self.lower[:,rows].min(axis=1))
                assert np.array_equal(self.hi[:,b],self.upper[:,rows].max(axis=1))
            live.extend(ids);row_ids.extend(rows);owners.extend([b]*len(ids))
        live=np.array(live,dtype=np.int64);row_ids=np.array(row_ids);owners=np.array(owners)
        order=np.argsort(live);target=np.argsort(end_occ)
        assert len(live)==len(np.unique(live))==len(end_occ)
        assert np.array_equal(live[order],end_occ[target])
        assert np.array_equal(line[row_ids[order]],end_line[target])
        assert np.array_equal(np.flatnonzero(self.owner>=0),np.sort(end_occ))
        qlo,qhi=interval(self.scores[:,qids],960);rup=radius_upper(radius,960)
        for qi,row in enumerate(observed):
            req=np.zeros(self.nb,dtype=bool);req[np.unique(owners[refs[qi,row_ids]<=radius*radius])]=True
            rej=(qlo[:,qi,None]>np.nextafter(self.hi[:,:self.nb]+rup,np.inf)) | (self.lo[:,:self.nb]>np.nextafter(qhi[:,qi,None]+rup,np.inf))
            keep=~rej.any(axis=0);keep &= self.count[:self.nb]>0
            assert not np.any(req & ~keep)
            assert row==dict(query=qi,qid=qids[qi],total_blocks=self.nb,oracle_required_blocks=int(req.sum()),
                             surviving_blocks=int(keep.sum()),surviving_block_fraction=float(keep.mean()),
                             surviving_active_objects=int(self.count[:self.nb][keep].sum()),false_prune_blocks=0)
        return hashlib.sha256(np.c_[live[order],line[row_ids[order]]].astype('<i8').tobytes()).hexdigest()


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    c,prior,files=bind_inputs(a.prior,a.verification,a.maintenance,a.references)
    static=json.loads((a.run/'PROOF.json').read_text());verified=json.loads(a.static_verification.read_text())
    assert static['passed'] and static['source_hashes']==source_hashes()
    assert verified['passed'] and verified['static_proof_sha256']==sha(a.run/'PROOF.json')
    assert {p.name:sha(p) for p in a.run.iterdir() if p.is_file() and p.name!='PROOF.json'}==static['raw_files']
    summary=json.loads((a.run/'BLOCK_SELECTIVITY.json').read_text())['summary'];decision=decide(summary)
    assert decision==json.loads((a.run/'DECISION.json').read_text())
    strategy,kind=decision['top_one']
    sources={p.name:sha(p) for p in (HERE/'update_recheck.py',HERE/'verify_partition.py',HERE/'test_update_recheck.py',BASE/'update.py')}
    save(out/'REGISTERED.json',dict(source_hashes=sources,static_source_hashes=source_hashes(),
                                  static_proof_sha256=sha(a.run/'PROOF.json'),static_verification_sha256=sha(a.static_verification),
                                  contract_sha256=sha(HERE/'CONTRACT.json'),selected=[strategy,kind],
                                  capacity_aware_initialization_authorized=True,GPU_processes=0))
    prepared=json.loads((a.maintenance/'PREPARED.json').read_text());previous=-1;results=[]
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0])
    for spec in c['updates']['intervals']:
        name,end=spec['snapshot'],spec['end']
        occ=np.load(a.maintenance/(name+'.occurrence.npy'));line=np.load(a.maintenance/(name+'.lineage.npy'))
        end_occ=np.load(a.maintenance/(end+'.occurrence.npy'));end_line=np.load(a.maintenance/(end+'.lineage.npy'))
        events=[e for e in prepared['updates'] if previous<e['step']<=spec['through_step']];previous=spec['through_step']
        ni=sum(e['action']=='insert' for e in events);nd=sum(e['action']=='delete' for e in events)
        assert (ni,nd)==(spec['actual_inserts'],spec['actual_deletes'])
        mapping=np.full(int(line.max())+1,-1,dtype=np.int64);mapping[line]=np.arange(len(line))
        event_rows=[int(mapping[e['vector_original_row']]) for e in events];assert min(event_rows)>=0
        scores=np.load(a.prior/(name+'_'+strategy+'_scores.npy'))[:4];tree=np.load(a.prior/(name+'_L3.npy'))
        perm,starts=make_partition(np.sqrt(scores),occ,tree,kind,240,True)
        check=independent_partition(np.sqrt(scores),occ,tree,kind,240,True)
        for x,y in zip((perm,starts),check):np.testing.assert_array_equal(x,y)
        np.savez(out/(name+'_initialization.npz'),permutation=perm,starts=starts)
        qids=prior['bindings'][name]['queries'];refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(len(occ),)) for q in qids])
        max_id=max(int(occ.max()),max(e['occurrence'] for e in events))
        model=VariableOwnership(occ,perm,starts,scores,max_id)
        before=model.query(refs,qids,radius);initial_state=model.check_full(occ,line,line,refs,qids,radius,before)
        sizes=model.count[:model.nb].copy()
        for event,row in zip(events,event_rows):model.apply(event,row)
        after=model.query(refs,qids,radius);final_state=model.check_full(end_occ,end_line,line,refs,qids,radius,after)
        changed=len(model.changed)/model.initial_blocks;moved=len(model.moved)/len(occ)
        results.append(dict(snapshot=name,ending_snapshot=end,strategy=strategy,partition=kind,pivot_count=4,
                            physical_capacity=256,active_capacity=240,nominal_slack_fraction=.0625,
                            actual_initial_empty_slot_fraction=1-len(occ)/(256*model.initial_blocks),
                            min_initial_block_size=int(sizes.min()),max_initial_block_size=int(sizes.max()),
                            initial_total_blocks=model.initial_blocks,final_total_blocks=model.nb,
                            global_initialization_passes=1,initialization_objects=len(occ),
                            actual_inserts=ni,actual_deletes=nd,changed_blocks=len(model.changed),changed_block_fraction=changed,
                            moved_existing_objects=len(model.moved),moved_existing_fraction=moved,
                            moved_existing_events=model.existing_move_events,all_vector_move_events=model.all_move_events,
                            splits=model.splits,certificate_refreshes=model.refreshes,global_repartition=0,
                            placement_blocks_examined=sum(e['action']=='insert' for e in events)*model.initial_blocks if not model.splits else None,
                            initial_query_survival_mean=float(np.mean([q['surviving_block_fraction'] for q in before])),
                            post_update_query_survival_mean=float(np.mean([q['surviving_block_fraction'] for q in after])),
                            locality_gate_passed=changed<=.05 and moved<=.05,
                            initial_state_sha256=initial_state,final_state_sha256=final_state,
                            full_final_occurrence_lineage_and_bounds_verified=True,initial_queries=before,post_update_queries=after,
                            events=model.event_records))
        print(name,'update recheck',changed,len(model.moved),model.splits,'query before/after',
              results[-1]['initial_query_survival_mean'],results[-1]['post_update_query_survival_mean'],flush=True)
    for path,digest in files.items():assert sha(path)==digest
    assert sources=={p.name:sha(p) for p in (HERE/'update_recheck.py',HERE/'verify_partition.py',HERE/'test_update_recheck.py',BASE/'update.py')}
    save(out/'UPDATE_RECHECK.json',dict(rows=results,selection=decision['top_one'],static_decision=decision,
                                       independent_initialization_per_interval=True,sustained_ownership_demonstrated=False,
                                       false_prune_blocks=0,query_rows=128,GPU_processes=0,
                                       CPU_locality_claim=False,reason='Insertion scans all block centroids; locality concerns writes/moves, not total work or latency'))
    save(out/'PROOF.json',dict(passed=True,registered_sha256=sha(out/'REGISTERED.json'),source_hashes=sources,
                             raw_files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                             actual_intervals=2,false_prune_blocks=0,all_membership_and_lineage_verified=True,GPU_processes=0))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('prior','verification','maintenance','references','run','static-verification','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
