#!/usr/bin/env python3
"""Exact occurrence-canonical CPU analysis of complete rebuild snapshots."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import numpy as np
NODE=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('is_leaf','<i4')])
FIELDS=('regions','leaf_slot','slot_pid','leaves','owners','parents','skeleton','level_offsets','skeleton_offsets')
def ratio(a,b):return a/b if b else None
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def sig(ids):return hashlib.sha256(np.sort(ids).astype('<i4',copy=False).tobytes()).digest()
class Snapshot:
    def __init__(self,path):
        self.path=Path(path);self.meta=json.loads((self.path/'meta.json').read_text())
        def arr(name,dtype='<i4'):return np.fromfile(self.path/name,dtype=dtype)
        self.base=arr('base.i32');self.deleted=arr('deleted.i32');self.buffer=arr('buffer.i32');self.buffer_positions=arr('buffer_positions.i32');self.live=arr('live.i32')
        self.nodes=arr('nodes.bin',NODE);self.empty=arr('empty.i32');self.order=arr('order.i32')
        self.lo=arr('lo.f64','<u8');self.hi=arr('hi.f64','<u8');self.plan={f:arr('plan_'+f+'.i32') for f in FIELDS}
        self.packed=np.memmap(self.path/'packed.f32',dtype='<u4',mode='r',shape=(len(self.base)//32,self.meta['d'],32))
        n=len(self.base);nn=len(self.nodes)
        assert NODE.itemsize==20 and n==self.meta['n'] and nn==self.meta['nn']
        assert len(self.lo)==len(self.hi)==nn and len(self.deleted)==n
        assert np.array_equal(np.sort(self.order),np.arange(n))
        assert len(np.unique(self.base))==n
        assert np.array_equal(np.sort(np.r_[self.base[self.deleted==0],self.buffer]),self.live)
        assert self.packed.size==n*self.meta['d']
        self.occorder=self.base[self.order];self.valid=np.flatnonzero((self.empty==0)&(self.nodes['size']>0))
        self.level=np.zeros(nn,dtype=np.int32)
        for i in self.valid[1:]:self.level[i]=self.level[(i-1)//10]+1
        self.keys={};self.livekeys={};self.members={};self.topo={};self.num={}
        cover=np.zeros(n,dtype=np.uint8);self.leaf_index=np.full(int(max(self.live.max(),self.base.max()))+1,-1,dtype=np.int32)
        for i in self.valid:
            v=self.nodes[i];at=int(v['lid']);size=int(v['size']);assert at>=0 and at+size<=n
            ids=self.occorder[at:at+size];self.keys[i]=(int(self.level[i]),sig(ids))
            alive_ids=ids[self.deleted[self.order[at:at+size]]==0]
            self.livekeys[i]=(int(self.level[i]),sig(alive_ids));self.members[i]=ids
            if v['is_leaf']:
                cover[at:at+size]+=1;self.leaf_index[ids]=i
        assert np.all(cover==1) and len(set(self.keys.values()))==len(self.keys)
        for i in self.valid:
            v=self.nodes[i];pivot=int(self.base[v['pid']]) if v['pid']>=0 else -1
            children=tuple((self.keys[c],int(self.base[self.nodes[c]['pid']]) if self.nodes[c]['pid']>=0 else -1) for c in range(i*10+1,min(i*10+11,nn)) if c in self.keys)
            self.topo[self.keys[i]]=(pivot,children,int(v['is_leaf']))
            self.num[self.keys[i]]=(int(v['min_dis'].view('<u4')),int(self.lo[i]),int(self.hi[i]))
        self.inverse={k:i for i,k in self.keys.items()}
    def coords(self,rows):return self.packed[rows//32,:,rows%32]

def leaves(a,b,live=False):
    ka=a.livekeys if live else a.keys;kb=b.livekeys if live else b.keys
    ia=[int(i) for i in a.valid if a.nodes[i]['is_leaf']];ib=[int(i) for i in b.valid if b.nodes[i]['is_leaf']]
    ma={ka[i]:i for i in ia};mb={kb[i]:i for i in ib};exact=set(ma)&set(mb)
    ua=set(ia)-{ma[k] for k in exact};ub=set(ib)-{mb[k] for k in exact}
    common=np.intersect1d(a.base[a.deleted==0],b.base[b.deleted==0]);pa=a.leaf_index[common];pb=b.leaf_index[common]
    same=sum(ka[int(x)]==kb[int(y)] for x,y in zip(pa,pb))
    pair,counts=np.unique(pa.astype(np.int64)*len(b.nodes)+pb,return_counts=True)
    edges=[]
    for code,c in zip(pair,counts):
        x,y=divmod(int(code),len(b.nodes))
        if x in ua and y in ub:edges.append((-int(c),ka[x],kb[y],x,y))
    modified=0
    for _,_,_,x,y in sorted(edges):
        if x in ua and y in ub:ua.remove(x);ub.remove(y);modified+=1
    return {'total_pre':len(ia),'total_post':len(ib),'unchanged_membership':len(exact),
            'modified_descriptive':modified,'new_descriptive':len(ub),'removed_descriptive':len(ua),
            'unmatched_new_canonical':len(mb)-len(exact),'unmatched_removed_canonical':len(ma)-len(exact),
            'changed_fraction_post':ratio(len(mb)-len(exact),len(mb)),
            'common_live_objects':len(common),'objects_same_membership':same,'objects_changed_membership':len(common)-same,
            'object_change_fraction':ratio(len(common)-same,len(common))}

def plan_content(s):
    p=s.plan;n=s.nodes;out={};regions=p['regions'].reshape(-1,6)
    roots=[s.keys[int(row[0])] for row in regions]
    leafslot=p['leaf_slot'];slotpid=p['slot_pid'];key=s.keys
    for i,v in enumerate(leafslot):
        if i in key:out[('leaf_slot',key[i])]=key[i] if v>=0 else -1
        else:out[('leaf_slot_empty',i)]=int(v)
    for i in p['leaves']:
        i=int(i);out[('leaves',key[i])]=key[i];start=int(leafslot[i]);size=int(n[i]['size'])
        assert np.array_equal(slotpid[start:start+size],s.order[int(n[i]['lid']):int(n[i]['lid'])+size])
        for local,row in enumerate(slotpid[start:start+size]):
            oid=int(s.base[row]);out[('slot_pid',oid)]=(key[i],local)
    for pos,rid in enumerate(p['owners']):out[('owners',int(s.occorder[pos]))]=roots[int(rid)]
    for label in ('parents','skeleton'):
        for i in p[label]:out[(label,key[int(i)])]=int(s.level[i])
    for row,root in zip(regions,roots):
        for field,value in enumerate(row):out[('regions',root,field)]=root if field in (0,4) else int(value)
    for label in ('level_offsets','skeleton_offsets'):
        for i,v in enumerate(p[label]):out[(label,i)]=int(v)
    assert len(out)==sum(v.size for v in p.values())==s.meta['plan_entries']
    return out

def diff(a,b):
    assert np.array_equal(a.live,b.live) and a.meta['step']==b.meta['step']
    ins=a.meta['insert_ids'];dele=a.meta['delete_ids'];touched=set(ins)|set(dele)
    netnew=np.setdiff1d(b.base,a.base);netdel=np.setdiff1d(a.base,b.base)
    common,pa,pb=np.intersect1d(a.base,b.base,return_indices=True)
    assert np.array_equal(a.base[pa],b.base[pb]) and np.all(a.deleted[pa]==0)
    moved=int(np.count_nonzero(pa!=pb));same=len(common)-moved
    pre_positions=np.empty(len(a.live),dtype=np.int64);post_positions=np.searchsorted(b.base,a.live) if np.all(b.base[:-1]<=b.base[1:]) else np.argsort(b.base)[np.searchsorted(np.sort(b.base),a.live)]
    base_inverse={int(oid):i for i,oid in enumerate(a.base)};pending_inverse=dict(zip(map(int,a.buffer),map(int,a.buffer_positions)))
    for j,oid in enumerate(a.live):pre_positions[j]=base_inverse.get(int(oid),pending_inverse.get(int(oid),-1))
    assert np.all(pre_positions>=0) and np.array_equal(b.base[post_positions],a.live)
    all_live_moved=int(np.count_nonzero(pre_positions!=post_positions))
    leaf=leaves(a,b);leaflive=leaves(a,b,True)
    full=top=number=0;piv=0;matched_pivot=0;bound_identical=0;bound_changed=0;semantic_struct_entries=0
    categories=collections.Counter();perlevel=collections.defaultdict(collections.Counter)
    for k,j in b.inverse.items():
        i=a.inverse.get(k);unchanged_top=i is not None and a.topo[k]==b.topo[k]
        if i is not None:
            matched_pivot+=1;piv+=a.topo[k][0]!=b.topo[k][0]
        if not unchanged_top:top+=1;semantic_struct_entries+=2;state='topology'
        else:
            eq=[a.num[k][z]==b.num[k][z] for z in (1,2)]
            bound_identical+=sum(eq);bound_changed+=2-sum(eq)
            if a.num[k]==b.num[k]:full+=1;state='identical'
            else:number+=1;state='numeric_only'
        affected=any(int(x) in touched for x in b.members[j]) or b.topo[k][0] in touched
        if i is not None:affected|=any(int(x) in touched for x in a.members[i]) or a.topo[k][0] in touched
        category='C_identical' if state=='identical' else 'A_observed_direct_dependency' if affected else 'B_changed_matched_no_direct_dependency' if i is not None else 'U_changed_unmatched_dependency_unknown'
        categories[category]+=1
        perlevel[k[0]][state]+=1
    assert full+top+number==len(b.valid)
    rawbounds=int(np.count_nonzero(a.lo!=b.lo)+np.count_nonzero(a.hi!=b.hi))
    rawpack=0;flat_a=a.packed.reshape(-1);flat_b=b.packed.reshape(-1)
    assert len(flat_a)==len(flat_b)
    for at in range(0,len(flat_a),4<<20):rawpack+=int(np.count_nonzero(flat_a[at:at+(4<<20)]!=flat_b[at:at+(4<<20)]))
    aligned_changed=0;changed_objects=0
    for at in range(0,len(pa),4096):
        neq=a.coords(pa[at:at+4096])!=b.coords(pb[at:at+4096]);aligned_changed+=int(np.count_nonzero(neq));changed_objects+=int(np.count_nonzero(np.any(neq,axis=1)))
    packtotal=int(b.packed.size);packchanged=len(netnew)*b.meta['d']+aligned_changed
    ap=plan_content(a);bp=plan_content(b);planidentical=sum(k in ap and ap[k]==v for k,v in bp.items())
    planby={}
    for f in FIELDS:
        # leaf_slot_empty shares the leaf_slot denominator.
        entries=[(k,v) for k,v in bp.items() if k[0]==f or f=='leaf_slot' and k[0]=='leaf_slot_empty']
        samef=sum(k in ap and ap[k]==v for k,v in entries);av=a.plan[f];bv=b.plan[f]
        assert len(av)==len(bv)
        planby[f]={'total':len(entries),'canonical_changed':len(entries)-samef,'canonical_identical':samef,'raw_changed':int(np.count_nonzero(av!=bv))}
    rawplan=sum(x['raw_changed'] for x in planby.values());planentries=len(bp);planchanged=planentries-planidentical
    n=b.meta['n'];nn=b.meta['nn'];build=b.meta['build_distance_tasks'];changednodes=top+number
    compact_pre=len(a.base)+len(a.buffer);refit_entries=2*nn
    work={'objects_compaction_candidates':compact_pre,'objects_compacted':n,'compaction_coordinate_writes':n*b.meta['d'],
          'temporary_D2D_copy_bytes':(a.meta['n']+11)*a.meta['d']*4,
          'construction_unique_objects':n,'construction_pivot_scoring_tasks':build,'construction_split_boundary_distance_tasks':b.meta['build_created_children'],'construction_total_distance_tasks':build+b.meta['build_created_children'],'construction_sort_API_input_slots':b.meta['sort_api_input_slots'],
          'active_split_nodes':b.meta['build_active_split_nodes'],'nodes_constructed':b.meta['build_created_children']+1,
          'leaves_constructed':b.meta['leaves'],'nodes_refitted':nn,'refit_distance_tasks':b.meta['refit_distance_tasks'],
          'refit_scalar_entries_written':refit_entries,'knn_pack_entries_regenerated':packtotal,'par_plan_scalar_entries_regenerated':planentries,
          'classification':'source-exact task counts and regenerated final-payload cardinalities from captured runtime inputs; hidden library/store instruction count unknown'}
    numericstatechanged=semantic_struct_entries+bound_changed
    return {'rebuild':a.meta['rebuild'],'trigger_step_zero_based':a.meta['step'],
      'logical':{'insert_count':len(ins),'delete_count':len(dele),'update_count':len(ins)+len(dele),'insert_ids':ins,'delete_ids':dele,
                 'unique_touched_count':len(touched),'unique_touched_fraction':len(touched)/n,'net_set_changed':len(netnew)+len(netdel),
                 'net_set_fraction':(len(netnew)+len(netdel))/n,'previous_published_base_count':len(a.base),'live_pre':len(a.live),'live_post':len(b.live)},
      'positions':{'same_position':same,'moved':moved,'new_base_admissions':len(netnew),'removed_tombstones':len(netdel),'common_live_base':len(common),
                   'moved_fraction_common':ratio(moved,len(common)),'relocation_per_unique_touched':ratio(moved,len(touched)),
                   'all_live_including_pending':{'total':len(a.live),'same_position':len(a.live)-all_live_moved,'moved':all_live_moved,'moved_fraction':ratio(all_live_moved,len(a.live)),'new_logical_occurrences_across_rebuild':0,'deleted_logical_occurrences_across_rebuild':0,'relocation_per_unique_touched':ratio(all_live_moved,len(touched))}},
      'leaf':leaf,'leaf_live_filtered':leaflive,
      'nodes':{'total':len(b.valid),'matched_subtree_memberships':matched_pivot,'fully_unchanged':full,'topology_changed':top,'numeric_only_changed':number,
               'changed_fraction':ratio(changednodes,len(b.valid)),'canonical_pivot_changed_among_matched':piv,'unmatched_pivot_ownership':len(b.valid)-matched_pivot,
               'pivot_references_post':len(b.valid)-1,'pivot_ownership_state_changed':sum(int(b.nodes[j]['pid'])>=0 and (k not in a.inverse or a.topo[k][0]!=b.topo[k][0]) for k,j in b.inverse.items()),
               'root_split_pivot_pre':int(a.base[a.nodes[1]['pid']]),'root_split_pivot_post':int(b.base[b.nodes[1]['pid']]),
               'unique_pivot_occurrences_pre':len({t[0] for t in a.topo.values() if t[0]>=0}),'unique_pivot_occurrences_post':len({t[0] for t in b.topo.values() if t[0]>=0}),'unique_pivot_occurrences_retained':len({t[0] for t in a.topo.values() if t[0]>=0}&{t[0] for t in b.topo.values() if t[0]>=0}),
               'categories':dict(categories),'by_level':{str(k):dict(v) for k,v in sorted(perlevel.items())}},
      'numeric':{'total_refit_entries':refit_entries,'canonical_identical_same_topology':bound_identical,'canonical_numeric_changed_same_topology':bound_changed,
                 'structurally_unmatched_entries':semantic_struct_entries,'canonical_state_changed':numericstatechanged,'canonical_state_changed_fraction':ratio(numericstatechanged,refit_entries),
                 'raw_positional_bit_changed':rawbounds,'raw_positional_bit_identical':refit_entries-rawbounds},
      'pack':{'total':packtotal,'physical_bit_changed':rawpack,'physical_bit_identical':packtotal-rawpack,'physical_change_fraction':ratio(rawpack,packtotal),
              'survivor_coordinate_changed':aligned_changed,'survivor_objects_changed':changed_objects,'new_coordinate_entries':len(netnew)*b.meta['d'],
              'removed_coordinate_entries':len(netdel)*a.meta['d'],'canonical_changed_post':packchanged,'canonical_identical':packtotal-packchanged,
              'canonical_changed_fraction':ratio(packchanged,packtotal)},
      'plan':{'total':planentries,'canonical_changed':planchanged,'canonical_identical':planidentical,'canonical_changed_fraction':ratio(planchanged,planentries),
              'raw_changed':rawplan,'raw_identical':planentries-rawplan,'by_field':planby},
      'work':work,
      'amplification':{'construction_unique_per_unique_mutation':ratio(n,len(touched)),'construction_pivot_scoring_per_unique_mutation':ratio(build,len(touched)),'construction_total_distance_tasks_per_unique_mutation':ratio(build+b.meta['build_created_children'],len(touched)),
         'construction_unique_per_membership_changed_object':ratio(n,leaf['objects_changed_membership']),
         'leaf_reconstruction_per_changed_leaf':ratio(b.meta['leaves'],leaf['total_post']-leaf['unchanged_membership']),
         'refit_nodes_per_changed_node':ratio(nn,changednodes),'refit_scalars_per_changed_canonical_state':ratio(refit_entries,numericstatechanged),
         'refit_scalars_per_numeric_only_changes':ratio(refit_entries,bound_changed),
         'pack_per_physical_changed':ratio(packtotal,rawpack),'pack_per_canonical_changed':ratio(packtotal,packchanged),'plan_per_canonical_changed':ratio(planentries,planchanged)},
      'gate':{'no_go_local':leaf['changed_fraction_post']>=.7 or ratio(changednodes,len(b.valid))>=.7,
              'go_maintenance':leaf['changed_fraction_post']<=.2 and ratio(changednodes,len(b.valid))<=.2 and ratio(full,len(b.valid))>=.7,
              'strong_go':len(touched)/n<.0001 and leaf['changed_fraction_post']<.1 and ratio(changednodes,len(b.valid))<.1 and ratio(full,len(b.valid))>=.7}}

def main():
    p=argparse.ArgumentParser();p.add_argument('snapshots',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=True)
    results=[]
    for r in (1,2):
        print('Analyzing R'+str(r),flush=True);pre=Snapshot(a.snapshots/f'PRE_R{r}');post=Snapshot(a.snapshots/f'POST_R{r}');results.append(diff(pre,post))
    decision='NO_GO_LOCAL_MAINTENANCE' if all(r['gate']['no_go_local'] for r in results) else 'STRONG_GO' if all(r['gate']['strong_go'] for r in results) else 'GO_MAINTENANCE' if all(r['gate']['go_maintenance'] for r in results) else 'INCONCLUSIVE'
    result={'schema':1,'scope':'one diagnostic replay, two actual rebuilds; no latency result','decision':decision,'rebuilds':results}
    (a.output/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    manifest=[]
    for f in sorted(a.snapshots.rglob('*')):
        if f.is_file():manifest.append({'file':str(f.relative_to(a.snapshots)),'bytes':f.stat().st_size,'sha256':sha(f)})
    (a.output/'SNAPSHOT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');print(decision,flush=True)
if __name__=='__main__':main()
