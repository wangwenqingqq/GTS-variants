#!/usr/bin/env python3
"""Conditionally execute GLOBAL then query-oracle REGION evaluation with frozen gates."""
import argparse,csv,json,math,sys,time
from pathlib import Path
import numpy as np
from certificates import bound,metadata_size,serialize,RHO,error_bound
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'certified_navigation_20261010'))
from audit import sha,save
COUNTS=[0,1,2,4,8]


def farthest_first(matrix,ids):
    assert ids==sorted(set(ids)) and len(ids)==64 and matrix.shape==(64,64)
    selected=[0]
    while len(selected)<8:
        nearest=matrix[:,selected].min(axis=1).copy();nearest[selected]=-np.inf
        selected.append(int(np.argmax(nearest)))
    return selected


def greedy(masks,k=8):
    regions,pivots=masks.shape
    covered=np.zeros(regions,dtype=np.uint8)
    selected=np.zeros((regions,k),dtype=np.uint8)
    used=np.zeros((regions,pivots),dtype=bool)
    pop=np.array([bin(i).count('1') for i in range(256)],dtype=np.int8)
    for j in range(k):
        gain=pop[masks & np.bitwise_not(covered[:,None])].copy();gain[used]=-1
        pick=np.argmax(gain,axis=1)
        selected[:,j]=pick;used[np.arange(regions),pick]=True
        covered |= masks[np.arange(regions),pick]
    assert np.array_equal(covered,np.bitwise_or.reduce(masks,axis=1))
    return selected


def promotion(rows):
    return any(r['level'] in (3,4) and r['pivot_count'] in (4,8) and
        r['oracle_gap_coverage']>=.70 and r['incremental_G0_pruning']>=.10 and
        r['aligned_bytes_per_region']<=64 for r in rows)


def decision(global_rows,region_rows):
    if promotion(global_rows):return 'GLOBAL_CERTIFICATE_FEASIBLE'
    if promotion(region_rows):return 'REGION_SPECIFIC_CERTIFICATE_FEASIBLE'
    if max(r['oracle_gap_coverage'] for r in region_rows if r['pivot_count']==8)<.50:
        return 'PIVOT_CERTIFICATE_KILLED'
    if any(r['level'] in (3,4) and r['oracle_gap_coverage']>=.70 and r['incremental_G0_pruning']>=.10
           and r['aligned_bytes_per_region']>64 for r in region_rows):return 'METADATA_HEAVY'
    return 'INSUFFICIENT_EVIDENCE'


def main():
    p=argparse.ArgumentParser()
    for key in ['stage','pool_run','out']:p.add_argument('--'+key.replace('_','-'),dest=key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    pm=json.loads((a.stage/'PIVOT_MANIFEST.json').read_text())
    assert sha(a.stage/'ancestors.npz')==pm['ancestors_sha256']
    assert sha(a.stage/'pivot_pool64.ids')==pm['pool_sha256']
    assert sha(HERE/'CONTRACT.yaml')==pm['contract_sha256']
    om=json.loads((a.pool_run/'OUTPUT_MANIFEST.json').read_text())
    for name in ['intervals.npz','SCAN_RECEIPT.json','VALIDATION.json']:
        assert sha(a.pool_run/name)==om[name]['sha256']
    assert json.loads((a.pool_run/'VALIDATION.json').read_text())['status']=='PASS'
    receipt=json.loads((a.pool_run/'SCAN_RECEIPT.json').read_text())
    assert not receipt['GPU_used'] and receipt['exit_code']==0
    assert receipt['pool_sha256']==pm['pool_sha256']
    assert receipt['source_sha256']==json.loads((HERE/'evidence/SOURCE.json').read_text())['generated_sha256']
    z=np.load(a.stage/'ancestors.npz');v=np.load(a.pool_run/'intervals.npz')
    ancestor=json.loads((a.stage/'ANCESTOR_TRUTH.json').read_text());assert ancestor['decision']=='CONTINUE_STAGE_B'
    queries=json.loads((a.stage/'INPUT_IDENTITY.json').read_text())['queries']
    u=np.sqrt(z['U_star_squared']);dq=np.sqrt(z['query_pivot_scores'])
    selected_global=farthest_first(v['pool_pair_scores'],pm['pool'])
    save(a.out/'GLOBAL_PIVOTS.json',dict(pool_indices=selected_global,
        rows=[pm['pool'][i] for i in selected_global],nested_counts=COUNTS,
        selection='farthest-first ordered squared distance, seed=min row ID, ties=min row ID',
        query_dependent=False))
    results=[];perquery=[];validation=[];masks_by_level={};serialized={}

    def evaluate(level,mode,selected):
        size={3:1000,4:100,5:10}[level];r=10**level
        native=z[f'native_lb_{level}'];truthsq=z[f'truth_sq_{level}'];truth=np.sqrt(truthsq)
        active=z[f'visited_{level}'];base=native<=u[:,None]
        retained_truth=truthsq<=z['U_star_squared'][:,None]
        low=v[f'low_{level}'];high=v[f'high_{level}']
        previous=native.copy();previous_pruned=~base
        for k in COUNTS:
            chosen=selected[:,:k];current=native.copy()
            for j in range(k):
                pi=chosen[:,j]
                for q in range(8):
                    lb=bound(low[np.arange(r),pi],high[np.arange(r),pi],dq[q,pi])
                    assert np.all(lb<=truth[q]),'selected certificate unsafe'
                    current[q]=np.maximum(current[q],lb)
            pruned=current>u[:,None]
            assert np.all(current>=previous) and not np.any(previous_pruned & ~pruned),'nonmonotone bound'
            assert not np.any(pruned & retained_truth),'false top-K prune'
            newly=pruned & base;assert not np.any(newly & ~active)
            unique=len(np.unique(chosen)) if k else 0
            logical,aligned=metadata_size(k,mode=='REGION_ORACLE')
            data=serialize(low,high,chosen,mode=='REGION_ORACLE')
            assert len(data)==r*aligned
            name=f'{mode}_L{level}_C{k}.bin';(a.out/name).write_bytes(data)
            serialized[name]=dict(bytes=len(data),sha256=sha(a.out/name))
            visited=int(active.sum())*size;old=int(base.sum())*size
            floor=int(retained_truth.sum())*size;remaining=int((~pruned).sum())*size
            new=int(newly.sum())*size;pairs=int(base.sum())*k
            row=dict(selection_mode=mode,level=level,pivot_count=k,regions=r,
                safe_pruned_regions=int(pruned.sum()),safe_pruned_objects=8*1000000-remaining,
                remaining_objects=remaining,residual_object_fraction=remaining/8000000,
                newly_pruned_G0_visited_objects=new,G0_visited_objects=visited,
                incremental_G0_pruning=new/visited,oracle_gap_coverage=(old-remaining)/(old-floor),
                logical_bytes_per_region=logical,aligned_bytes_per_region=aligned,
                unique_query_pivot_distances_per_query=unique,query_pivot_distances_total=8*unique,
                bound_evaluations=pairs,object_distance_coordinate_updates=remaining*960,
                object_distance_coordinate_updates_avoided=new*960,
                pivot_distance_coordinate_updates=8*unique*960,
                metadata_bytes_read=int(base.sum())*aligned,
                scalar_bound_ops=pairs*8+8*unique*5,outward_nextafter_ops=pairs*3,
                shared_row_ID_table_bytes=256 if mode=='REGION_ORACLE' and k else 4*unique,
                shared_pivot_vectors_bytes=unique*960*4,
                query_distance_cache_bytes_per_query=unique*8,
                certificate_efficiency=(old-remaining)/(old-floor)/aligned if aligned else 0.)
            results.append(row)
            for q,qid in enumerate(queries):
                oldq=int(base[q].sum())*size;floorq=int(retained_truth[q].sum())*size
                remainq=int((~pruned[q]).sum())*size;newq=int(newly[q].sum())*size
                perquery.append(dict(query_id=qid,selection_mode=mode,level=level,pivot_count=k,
                    remaining_objects=remainq,residual_object_fraction=remainq/1000000,
                    newly_pruned_objects=newq,G0_visited_objects=int(active[q].sum())*size,
                    incremental_G0_pruning=newq/(int(active[q].sum())*size),
                    oracle_gap_coverage=(oldq-remainq)/(oldq-floorq)))
            previous=current;previous_pruned=pruned
            if mode=='REGION_ORACLE' and k==8:
                mask=masks_by_level[level]
                for q in range(8):
                    expected=base[q] & np.any((mask & (1<<q))!=0,axis=1)
                    assert np.array_equal(newly[q],expected),'REGION8 is not the full-pool envelope'

    # Safety screen covers every candidate in the pool, including rejected pivots.
    for level in [3,4,5]:
        r=10**level;low=v[f'low_{level}'];high=v[f'high_{level}'];truth=np.sqrt(z[f'truth_sq_{level}'])
        native=z[f'native_lb_{level}'];base=native<=u[:,None]
        mask=np.zeros((r,64),dtype=np.uint8)
        for q in range(8):
            lb=bound(low,high,dq[q])
            assert np.all(lb<=truth[q,:,None]),'full-pool safety violation'
            extra=(lb>u[q]) & base[q,:,None]
            mask |= extra.astype(np.uint8)*(1<<q)
        masks_by_level[level]=mask
        validation.append(dict(level=level,pool_candidate_bounds_checked=8*r*64,safety_violations=0))
        chosen=np.tile(np.array(selected_global,dtype=np.uint8),(r,1))
        evaluate(level,'GLOBAL',chosen)
    global_rows=[r for r in results if r['selection_mode']=='GLOBAL']
    global_killed=max(r['incremental_G0_pruning'] for r in global_rows if r['pivot_count']==8)<.10
    if not promotion(global_rows):
        for level in [3,4,5]:
            chosen=greedy(masks_by_level[level])
            np.save(a.out/f'REGION_L{level}_selected.npy',chosen)
            evaluate(level,'REGION_ORACLE',chosen)
    region_rows=[r for r in results if r['selection_mode']=='REGION_ORACLE']
    verdict=decision(global_rows,region_rows)
    for name,rows in [('per_level_summary.csv',results),('per_query_summary.csv',perquery)]:
        with (a.out/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    save(a.out/'aggregate_summary.json',dict(base_commit='1f4d4ab05c66b4cc2411b7532a86517b823d53f9',
        query_count=8,levels=[3,4,5],leaf_alias=5,pivot_counts=COUNTS,ancestor_truth=ancestor,
        global_results=global_rows,region_results=region_rows,decision=verdict,
        GLOBAL_PIVOT_CERTIFICATE_KILLED=global_killed,region_stage_run=bool(region_rows),
        scope='fixed-pool stratified-query offline counts, no latency or out-of-sample claim',
        stage_C_selection_overfits_queries=True,metadata_alignment_bytes=16))
    save(a.out/'VALIDATION.json',dict(status='PASS',full_pool_checks=validation,
        total_candidate_bounds_checked=sum(x['pool_candidate_bounds_checked'] for x in validation),
        GLOBAL_monotone=True,REGION_monotone=True if region_rows else None,
        REGION8_equals_full64_pool_envelope=True if region_rows else None,
        C0_truth_bridges=True,false_topK_prunes=0,RHO=RHO,proven_distance_error_bound=error_bound(),
        serialized_metadata=serialized,elapsed_seconds=time.monotonic()-start,
        source_sha256=sha(Path(__file__)),helper_sha256=sha(HERE/'certificates.py'),
        pool_intervals_sha256=sha(a.pool_run/'intervals.npz')))
    print('Decision',verdict,flush=True)
    for row in results:
        if row['pivot_count'] in (0,8):print(row['selection_mode'],row['level'],row['pivot_count'],
            'residual',row['residual_object_fraction'],'gap',row['oracle_gap_coverage'],
            'new work',row['incremental_G0_pruning'],'bytes',row['aligned_bytes_per_region'],flush=True)

if __name__=='__main__':main()
