#!/usr/bin/env python3
"""Exact occurrence membership gates and descriptive rank/boundary diagnostics."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
NODE=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('is_leaf','<i4')])
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def sig(ids):return hashlib.sha256(np.sort(ids).astype('<i4',copy=False).tobytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def correspondence(old_labels,new_labels,slots):
    pairs=np.bincount(new_labels.astype(np.int64)*slots+old_labels,minlength=slots*slots).reshape(slots,slots)
    newbest=np.argmax(pairs,axis=1);oldbest=np.argmax(pairs,axis=0)
    newmax=pairs.max(axis=1);oldmax=pairs.max(axis=0)
    nt=(pairs==newmax[:,None]).sum(axis=1);ot=(pairs==oldmax[None,:]).sum(axis=0)
    matches={i:int(j) for i,j in enumerate(newbest) if newmax[i]>0 and nt[i]==1 and ot[j]==1 and oldbest[j]==i}
    return matches,pairs
def sparse_correspondence(old_labels,new_labels,slots):
    codes,counts=np.unique(new_labels.astype(np.int64)*slots+old_labels,return_counts=True)
    new=codes//slots;old=codes%slots
    nm=np.zeros(slots,dtype=np.int64);om=nm.copy()
    np.maximum.at(nm,new,counts);np.maximum.at(om,old,counts)
    nt=np.bincount(new[counts==nm[new]],minlength=slots);ot=np.bincount(old[counts==om[old]],minlength=slots)
    keep=(counts==nm[new])&(counts==om[old])&(nt[new]==1)&(ot[old]==1)
    return ({int(i):int(j) for i,j in zip(new[keep],old[keep])},
            {int(i):int(c) for i,c in zip(new[keep],counts[keep])})
class Tree:
    def __init__(self,snapshot,replay=None):
        self.snapshot=Path(snapshot);self.replay=Path(replay) if replay else None;src=self.replay or self.snapshot
        self.base=np.fromfile(self.snapshot/'base.i32',dtype='<i4');self.order=np.fromfile(src/'order.i32',dtype='<i4')
        self.nodes=np.fromfile(src/'nodes.bin',dtype=NODE);self.empty=np.fromfile(src/'empty.i32',dtype='<i4')
        self.live=np.fromfile(self.snapshot/'live.i32',dtype='<i4');self.occs=self.base[self.order];n=len(self.base)
        assert n==1000000 and len(self.nodes)==111111 and not np.any(self.empty)
        assert np.array_equal(np.sort(self.order),np.arange(n)) and len(np.unique(self.base))==n
        self.level={};self.members={};self.keys={};self.labels={};self.pivots={};self.topology={}
        cover=np.zeros(n,dtype=np.int32);self.oidmax=int(max(self.base.max(),self.live.max()))+1
        self.leaf_label=np.full(self.oidmax,-1,dtype=np.int32)
        for level in range(6):
            first=(10**level-1)//9;slots=10**level;inds=list(range(first,first+slots));self.level[level]=inds
            labels=np.full(self.oidmax,-1,dtype=np.int32)
            cursor=0
            for slot,i in enumerate(inds):
                node=self.nodes[i];at=int(node['lid']);size=int(node['size']);assert at==cursor and size==n//slots;cursor+=size
                ids=self.occs[at:at+size];self.members[i]=ids;self.keys[i]=sig(ids);labels[ids]=slot
                assert int(node['is_leaf'])==(level==5)
                if level==5:cover[at:at+size]+=1;self.leaf_label[ids]=i;assert 1<=size<=20
                else:
                    children=self.nodes[i*10+1:i*10+11];assert len(children)==10
                    assert np.all(children['pid']==children['pid'][0]);pid=int(children[0]['pid']);assert 0<=pid<n
                    assert self.base[pid] in ids;self.pivots[i]=int(self.base[pid])
                    assert np.array_equal(children['lid'],at+np.arange(10)*(size//10)) and np.all(children['size']==size//10)
            assert cursor==n;self.labels[level]=labels
        assert np.all(cover==1)
        for i in range(len(self.nodes)):
            children=tuple(self.keys[c] for c in range(i*10+1,min(i*10+11,len(self.nodes)))) if not self.nodes[i]['is_leaf'] else ()
            inherited=int(self.base[self.nodes[i]['pid']]) if self.nodes[i]['pid']>=0 else -1
            self.topology[i]=(inherited,self.pivots.get(i,-1),children,int(self.nodes[i]['is_leaf']))
        self.index={level:{self.keys[i]:i for i in inds} for level,inds in self.level.items()}
        if self.replay:self.audit_gate()
    def audit(self,level,suffix,dtype):return np.fromfile(self.replay/f'audit/build0/level{level}.{suffix}',dtype=dtype)
    def audit_gate(self):
        with (self.replay/'DECISIONS.csv').open() as f:decisions=list(csv.DictReader(f))
        assert len(decisions)==11111;self.decisions=decisions;tie=[]
        for level in range(5):
            ids=self.audit(level,'input.order','<i4');keys=self.audit(level,'distance.keys','<f8');ordered=self.audit(level,'sorted.order','<i4');sortedkeys=self.audit(level,'sorted.keys','<f8')
            assert len(ids)==len(keys)==len(ordered)==len(sortedkeys)==1000000
            assert np.isfinite(keys).all() and np.array_equal(np.sort(ids),np.arange(1000000))
            assert np.all(sortedkeys[:-1]<=sortedkeys[1:]);byrow=np.empty(1000000,dtype='<u8');byrow[ids]=keys.view('<u8')
            assert np.array_equal(byrow[ordered],sortedkeys.view('<u8'))
            inputrank=np.empty(1000000,dtype=np.int32);inputrank[ids]=np.arange(1000000)
            equal=sortedkeys[:-1]==sortedkeys[1:];groups=int(np.count_nonzero(equal & np.r_[True,~equal[:-1]]));participating=int(equal.sum())+groups
            reversals=int(np.count_nonzero(equal & (inputrank[ordered][:-1]>inputrank[ordered][1:])))
            tie.append({'level':level,'exact_encoded_key_tied_adjacent_pairs':int(equal.sum()),'tie_groups':groups,'tie_participating_occurrences':participating,'adjacent_input_rank_descents_within_exact_encoded_key_ties':reversals,'secondary_key':'none supplied; input rank observed, not added to sort'})
            pids=self.audit(level,'distance.pids','<i4');first=(10**level-1)//9
            for i in self.level[level]:
                assert int(self.base[pids[i]])==self.pivots[i]
                at=int(self.nodes[i]['lid']);size=int(self.nodes[i]['size'])
                assert np.array_equal(np.sort(ids[at:at+size]),np.sort(ordered[at:at+size]))
                assert sig(self.base[ids[at:at+size]])==self.keys[i]

            for row in [x for x in decisions if int(x['level'])==level]:assert int(row['chosen_pivot_oid'])==self.pivots[int(row['storage_node'])]
        assert np.array_equal(self.audit(4,'sorted.order','<i4'),self.order)
        self.ties=tie
    def export(self):
        # Canonical signatures retain complete memberships through order + base.
        with (self.replay/'CANONICAL.csv').open('w') as f:
            writer=csv.writer(f);writer.writerow(['storage_node','level','membership_sha256','inherited_pivot_oid','selected_split_pivot_oid','ordered_children_membership_sha256'])
            for level,inds in self.level.items():
                for i in inds:writer.writerow([i,level,self.keys[i],self.topology[i][0],self.pivots.get(i,-1),'|'.join(self.topology[i][2])])
        dump(self.replay/'VALIDITY.json',{'passed':True,'complete_permutation':True,'leaf_coverage':True,'valid_arity':True,'pivot_in_parent':True,'keys_sorted_and_permutation_preserved':True,'numeric_node_ids_not_correspondence':True,'tie_diagnostics':self.ties})
def compare(a,b):
    common=np.intersect1d(a.base,b.base);common=np.intersect1d(common,np.intersect1d(a.live,b.live));la=a.level[5];lb=b.level[5]
    exact=len(set(a.index[5])&set(b.index[5]));same=sum(a.keys[int(i)]==b.keys[int(j)] for i,j in zip(a.leaf_label[common],b.leaf_label[common]))
    ka=a.leaf_label[common]-a.level[5][0];kb=b.leaf_label[common]-b.level[5][0]
    pairs,counts=np.unique(ka.astype(np.int64)*100000+kb,return_counts=True);best=np.zeros(100000,dtype=np.int32);bestold=np.full(100000,-1,dtype=np.int32)
    for code,c in zip(pairs,counts):
        old,new=divmod(int(code),100000)
        if c>best[new] or c==best[new] and old<bestold[new]:best[new]=c;bestold[new]=old
    result={'leaf':{'post_total':len(lb),'pre_total':len(la),'exact_unchanged':exact,'changed':len(lb)-exact,'changed_fraction':1-exact/len(lb)},
      'common_live_objects':{'total':len(common),'same_exact_leaf_membership':same,'changed_exact_leaf_membership':len(common)-same,'changed_fraction':1-same/len(common)},
      'descriptive_only':{'best_overlap_mean_intersection':float(best.mean()),'best_overlap_mean_jaccard':float(np.mean(best/(20-best))),'best_overlap_retained_membership_fraction':float(best.sum()/len(common)),'not_gate':'best-overlap does not relax canonical exact identity'},'levels':[]}
    for level in range(6):
        ai=a.level[level];bi=b.level[level];slots=len(bi);samekeys=set(a.index[level])&set(b.index[level]);matches,overlaps=sparse_correspondence(a.labels[level][common],b.labels[level][common],slots)
        sa=set(a.pivots[i] for i in ai if i in a.pivots);sb=set(b.pivots[i] for i in bi if i in b.pivots)
        samepivot=sum(a.pivots.get(a.index[level][k],-1)==b.pivots.get(b.index[level][k],-1) for k in samekeys) if level<5 else None
        exactobjects=sum(len(b.members[b.index[level][k]]) for k in samekeys)
        row={'level':level,'partitions':slots,'exact_same_partitions':len(samekeys),'partition_divergence_fraction':1-len(samekeys)/slots,'common_objects_same_exact_parent_membership':exactobjects,
             'common_objects_changed_exact_parent_fraction':1-exactobjects/len(common),'pre_unique_selected_pivots':len(sa),'pivot_surviving':len(sa&sb),'pivot_survival_fraction':len(sa&sb)/len(sa) if sa else None,'exact_membership_matched_same_pivot':samepivot,
             'matched_correspondence':len(matches),'same_pivot_under_correspondence':sum(a.pivots[ai[j]]==b.pivots[bi[i]] for i,j in matches.items()) if level<5 else None}
        retained=int(sum(overlaps.values()))
        row['common_objects_retained_under_correspondence']=retained
        row['common_objects_unmatched_or_parent_moved']=len(common)-retained
        row['common_objects_unmatched_or_parent_moved_fraction']=1-retained/len(common)
        row['full_membership_caveat']='Exact PRE partition membership includes removed occurrences; identity divergence is not object movement. Root remains one corresponding parent.'
        result['levels'].append(row)
    matched=sum(len(set(a.index[l])&set(b.index[l])) for l in range(6))
    identical=sum(a.topology[a.index[l][k]]==b.topology[b.index[l][k]] for l in range(6) for k in set(a.index[l])&set(b.index[l]))
    result['canonical_topology']={'post_nodes':len(b.nodes),'matched_membership':matched,'fully_identical':identical,'changed':len(b.nodes)-identical,'includes':'inherited pivot, selected split pivot, ordered child membership, leaf flag'}
    return result

def rank_boundaries(a,b,level):
    """Distances/ties are diagnostic; exact leaf identity remains the gate."""
    slots=10**level;common=np.intersect1d(a.base,b.base);common=np.intersect1d(common,np.intersect1d(a.live,b.live))
    ol=a.labels[level][common];nl=b.labels[level][common]
    matches,overlaps=sparse_correspondence(ol,nl,slots)
    codes=nl.astype(np.int64)*slots+ol;permutation=np.argsort(codes);ordered_codes=codes[permutation]
    oldmass=np.bincount(ol,minlength=slots);newmass=np.bincount(nl,minlength=slots)
    oldids=a.base[a.audit(level,'sorted.order','<i4')];newids=b.base[b.audit(level,'sorted.order','<i4')]
    oldkeys=a.audit(level,'sorted.keys','<u8');newkeys=b.audit(level,'sorted.keys','<u8')
    ranka=np.full(max(a.oidmax,b.oidmax),-1,dtype=np.int32);rankb=ranka.copy();ranka[oldids]=np.arange(1000000);rankb[newids]=np.arange(1000000)
    details=[];total=0;changedseg=0;crossings=np.zeros(9,dtype=np.int64);drifts=[]
    for i,j in sorted(matches.items()):
        pre=a.level[level][j];post=b.level[level][i];sizea=int(a.nodes[pre]['size']);sizeb=int(b.nodes[post]['size']);starta=int(a.nodes[pre]['lid']);startb=int(b.nodes[post]['lid'])
        code=i*slots+j;lo=np.searchsorted(ordered_codes,code);hi=np.searchsorted(ordered_codes,code,side='right')
        ids=common[permutation[lo:hi]];ra=ranka[ids]-starta;rb=rankb[ids]-startb
        crossed=np.array([np.count_nonzero((ra<k*(sizea//10))!=(rb<k*(sizeb//10))) for k in range(1,10)])
        seg=np.count_nonzero(ra//(sizea//10)!=rb//(sizeb//10));drift=rb.astype(np.int64)-ra;drifts.append(np.abs(drift))
        identical_pivot=a.pivots[pre]==b.pivots[post];ties_persisted=ties_changed=0
        # Compare common equal-key groups only when the selected pivot is identical.
        if identical_pivot:
            present=np.zeros(len(ranka),dtype=bool);present[ids]=True
            pkeys=oldkeys[starta:starta+sizea];cuts=np.r_[0,np.flatnonzero(pkeys[1:]!=pkeys[:-1])+1,sizea]
            for lo,hi in zip(cuts[:-1],cuts[1:]):
                if hi-lo<2:continue
                group=oldids[starta+lo:starta+hi];group=group[present[group]];
                if len(group)<2:continue
                qkeys=newkeys[rankb[group]]
                for key in np.unique(qkeys):
                    g=group[qkeys==key]
                    if len(g)>1:ties_persisted+=1;ties_changed+=int(np.any(np.diff(rankb[g])<0))
        total+=len(ids);changedseg+=int(seg);crossings+=crossed
        details.append({'pre_membership_sha256':a.keys[pre],'post_membership_sha256':b.keys[post],'pre_selected_pivot':a.pivots[pre],'post_selected_pivot':b.pivots[post],'same_pivot':identical_pivot,'common_retained_in_matched_parent':len(ids),'imports_exports_common':int(oldmass[j]+newmass[i]-2*overlaps[i]),'decile_boundary_pre_positions':[k*(sizea//10) for k in range(1,10)],'decile_boundary_post_positions':[k*(sizeb//10) for k in range(1,10)],'crossing_counts':crossed.tolist(),'changed_segment_count':int(seg),'rank_absolute_mean':float(np.mean(np.abs(drift))),'rank_absolute_max':int(np.max(np.abs(drift))), 'persisted_tie_subgroups':ties_persisted,'tie_subgroups_relative_order_changed':ties_changed if identical_pivot else None})
    d=np.concatenate(drifts) if drifts else np.array([])
    return {'level':level,'correspondence':'unique mutual maximum common occurrence overlap; numeric IDs never matched','matched_partitions':len(matches),'common_total':len(common),'matched_parent_retained_common':total,'unmatched_or_parent_moved_common':len(common)-total,'crossing_per_decile_boundary':crossings.tolist(),'changed_segment_objects':changedseg,'total_crossing_fraction':changedseg/total if total else None,'sum_crossings_not_unique':int(crossings.sum()),'absolute_rank_drift_p50_p90_p99_max':np.percentile(d,[50,90,99,100]).tolist() if len(d) else None,'partitions':details}

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
    results=[]
    for r in (1,2):
        pre=Tree(a.prior/f'snapshots/PRE_R{r}',a.root/f'runs/R{r}_PRE');pre.export()
        c0=Tree(a.prior/f'snapshots/POST_R{r}',a.root/f'runs/R{r}_C0');c0.export()
        modes=[]
        for name in ('C0','C1','C2','C3'):
            folder=a.root/f'runs/R{r}_{name}'
            if not (folder/'REPLAY.json').exists():continue
            tree=c0 if name=='C0' else Tree(a.prior/f'snapshots/POST_R{r}',folder);tree.export()
            comp=compare(pre,tree);native=compare(c0,tree);boundary=[rank_boundaries(pre,tree,l) for l in range(5)]
            dump(folder/'BOUNDARY.json',boundary)
            requested=[d for d in tree.decisions if d['requested']=='1'];admitted=[d for d in requested if d['admitted']=='1']
            fallback=[d for d in requested if d['admitted']!='1']
            row={'mode':name,'frozen_levels':int(name[1:]),'vs_pre':comp,'vs_native':native,'freezes':{'requested':len(requested),'admitted':len(admitted),'fallback':len(fallback),'fallback_reasons':{reason:sum(d['reason']==reason for d in fallback) for reason in {d['reason'] for d in fallback}}},'boundary':[{k:v for k,v in b.items() if k!='partitions'} for b in boundary],'boundary_details_sha256':sha(folder/'BOUNDARY.json'),'ties':tree.ties,'validity':True}
            modes.append(row)
        results.append({'rebuild':r,'modes':modes})
    dump(a.output/'RESULT.json',{'experiment':'early_pivot_causal','scope':'structural only; no production/performance claim','rebuilds':results})
    print(json.dumps([{'r':x['rebuild'],'modes':[{'mode':m['mode'],'churn':m['vs_pre']['leaf']['changed_fraction'],'freezes':m['freezes']} for m in x['modes']]} for x in results]),flush=True)
if __name__=='__main__':main()
