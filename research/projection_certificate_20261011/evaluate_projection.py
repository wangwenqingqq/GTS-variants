#!/usr/bin/env python3
"""Stage B full frozen matrix after Stage A; no timing or GPU admission."""
import argparse,csv,json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'certified_navigation_20261010'))
from audit import sha,save
from projection_math import prefix_bounds,serialize,decision,COUNTS,exact_gram_bound

def read_csv(p):
    with p.open() as f:return list(csv.DictReader(f))

def write_csv(p,rows):
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser()
    for key in ['freeze','run','ancestors','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    im=json.loads((a.freeze/'INPUT_MANIFEST.json').read_text());om=json.loads((a.run/'OUTPUT_MANIFEST.json').read_text())
    assert sha(a.ancestors)==im['ancestors_sha256'] and sha(HERE/'CONTRACT.json')==im['contract_sha256']
    assert sha(a.freeze/'BRIDGE_PAIRS.json')==im['pairs_sha256']
    for name,entry in om.items():assert sha(a.run/name)==entry['sha256']
    stage=json.loads((a.run/'STAGE_A.json').read_text());receipt=json.loads((a.run/'BUILD_RECEIPT.json').read_text())
    assert stage['status']=='PASS' and stage['inputs']==im and receipt['GPU_used']==False and receipt['exit_code']==0
    for name,key in [('project_rows.cpp','source_sha256'),('build_projection.py','worker_sha256'),('projection_math.py','math_sha256')]:
        assert sha(HERE/name)==receipt[key],'source drift '+name
    basis=json.loads((a.run/'BASIS.json').read_text())
    for family,rows in basis['families'].items():
        matrix=np.array([[float.fromhex(v) for v in row] for row in rows]);upper,_=exact_gram_bound(matrix)
        assert upper<=1 and str(upper)==basis['certificates'][family]['exact_gram_infinity_bound']
    z=np.load(a.ancestors);v=np.load(a.run/'intervals.npz');u=np.sqrt(z['U_star_squared'])
    pivpath=HERE.parent/'certificate_compression_20261011/evidence/per_level_summary.csv'
    assert sha(pivpath)==im['pivot_summary_sha256'];pivots=read_csv(pivpath)
    results=[];perquery=[];validations=[];records={};truth_rows=[]
    for level,size in [(3,1000),(4,100),(5,10)]:
        r=10**level;native=z[f'native_lb_{level}'];truthsq=z[f'truth_sq_{level}'];truth=np.sqrt(truthsq)
        retained=truthsq<=z['U_star_squared'][:,None];visited=z[f'visited_{level}'];base=native<=u[:,None]
        assert np.array_equal(retained,truth<=u[:,None]);assert np.all(native<=truth)
        assert not np.any(base&~visited)
        old=int(base.sum())*size;floor=int(retained.sum())*size;g0=int(visited.sum())*size
        expected=next(x for x in pivots if int(x['level'])==level and int(x['pivot_count'])==0)
        assert old==int(expected['remaining_objects']) and g0==int(expected['G0_visited_objects'])
        truth_rows.append(dict(level=level,remaining_objects=floor,residual_fraction=floor/8000000))
        def record(family,k,pruned):
            new=pruned&base;assert not np.any(new&~visited) and not np.any(pruned&retained)
            remaining=int((~pruned).sum())*size;added=int(new.sum())*size
            logical=8*k;aligned=((logical+15)//16)*16
            evaluations=int(base.sum()) if k else 0
            row=dict(family=family,level=level,k=k,regions=r,objects_per_region=size,
                safe_pruned_regions=int(pruned.sum()),safe_pruned_objects=8000000-remaining,
                remaining_objects=remaining,residual_fraction=remaining/8000000,
                additional_G0_visited_pruned=added,G0_visited_objects=g0,
                incremental_G0_pruning=added/g0,oracle_gap_coverage=(old-remaining)/(old-floor),
                logical_bytes_per_region=logical,aligned_bytes_per_region=aligned,
                query_projection_coordinate_updates=8*k*960,
                bound_evaluations=evaluations,bound_scalar_ops=(8*k+3)*evaluations+2*8*k,
                outward_nextafter_ops=(4*k+2)*evaluations+2*8*k,
                metadata_bytes_read=evaluations*aligned,
                avoided_original_coordinate_updates=added*960,
                remaining_original_coordinate_updates=remaining*960,
                shared_basis_bytes=k*960*8,query_projection_cache_bytes_per_query=k*8,
                certificate_efficiency=(old-remaining)/(old-floor)/aligned if aligned else 0.)
            results.append(row)
            for qi,qid in enumerate(im['queries']):
                oldq=int(base[qi].sum())*size;floorq=int(retained[qi].sum())*size
                remain=int((~pruned[qi]).sum())*size;newq=int(new[qi].sum())*size;g0q=int(visited[qi].sum())*size
                perquery.append(dict(query_id=qid,family=family,level=level,k=k,remaining_objects=remain,
                    residual_fraction=remain/1000000,additional_G0_visited_pruned=newq,
                    G0_visited_objects=g0q,incremental_G0_pruning=newq/g0q,
                    oracle_gap_coverage=(oldq-remain)/(oldq-floorq)))
        record('C0',0,~base)
        for fi,family in enumerate(['RANDOM_ORTHO','PCA']):
            sl=slice(fi*8,(fi+1)*8);low=v[f'low_{level}'][:,sl];high=v[f'high_{level}'][:,sl]
            previous=native.copy();previous_pruned=~base;bs={k:np.empty_like(native) for k in COUNTS}
            for qi in range(8):
                for k,lb in prefix_bounds(low,high,v['query_projection'][qi,sl]).items():bs[k][qi]=lb
            for k in COUNTS:
                assert np.all(bs[k]<=truth),'projection above truth'
                candidate=np.maximum(native,bs[k]);pruned=candidate>u[:,None]
                assert np.all(candidate>=previous) and not np.any(previous_pruned&~pruned)
                record(family,k,pruned);previous=candidate;previous_pruned=pruned
                data=serialize(low,high,k);name=f'{family}_L{level}_K{k}.bin'
                (a.out/name).write_bytes(data);assert len(data)==r*((8*k+15)//16)*16
                packed=np.frombuffer(data,dtype=np.uint8).reshape(r,(8*k+15)//16*16)
                restored=packed[:,:8*k].copy().view('<f4').reshape(r,k,2)
                assert np.array_equal(restored[:,:,0],low[:,:k]) and np.array_equal(restored[:,:,1],high[:,:k])
                assert not packed[:,8*k:].any(),'nonzero metadata padding'
                records[name]=dict(bytes=len(data),sha256=sha(a.out/name),endpoint_roundtrip=True,zero_padding=True)
            validations.append(dict(family=family,level=level,bounds_checked=8*r*len(COUNTS),
                false_topK_prunes=0,bound_above_truth=0,nested=True))
    comparators=[]
    for row in results:
        if row['family']!='PCA' or row['k'] not in (2,4,8):continue
        pool=[x for x in pivots if int(x['level'])==row['level'] and int(x['pivot_count'])>0]
        feasible=[x for x in pool if int(x['aligned_bytes_per_region'])<=row['aligned_bytes_per_region']]
        best=max(feasible,key=lambda x:(float(x['oracle_gap_coverage']),-int(x['aligned_bytes_per_region'])))
        unlimited=max(pool,key=lambda x:(float(x['oracle_gap_coverage']),-int(x['aligned_bytes_per_region'])))
        comparators.append(dict(level=row['level'],PCA_k=row['k'],budget_bytes=row['aligned_bytes_per_region'],
            PCA_gap=row['oracle_gap_coverage'],pivot_mode=best['selection_mode'],pivot_count=int(best['pivot_count']),
            pivot_aligned_bytes=int(best['aligned_bytes_per_region']),pivot_gap=float(best['oracle_gap_coverage']),
            joint_gain=row['oracle_gap_coverage']-float(best['oracle_gap_coverage']),
            unlimited_pivot_mode=unlimited['selection_mode'],unlimited_pivot_count=int(unlimited['pivot_count']),
            unlimited_pivot_bytes=int(unlimited['aligned_bytes_per_region']),unlimited_pivot_gap=float(unlimited['oracle_gap_coverage']),
            gain_vs_unlimited=row['oracle_gap_coverage']-float(unlimited['oracle_gap_coverage'])))
    verdict=decision(results);last=[x for x in results if x['k']==8]
    by={(x['family'],x['level']):x for x in last}
    k3=all(abs(by[('PCA',l)]['oracle_gap_coverage']-by[('RANDOM_ORTHO',l)]['oracle_gap_coverage'])<.05 and
        max(by[('PCA',l)]['oracle_gap_coverage'],by[('RANDOM_ORTHO',l)]['oracle_gap_coverage'])<.3 for l in [3,4,5])
    for name,rows in [('per_level_summary.csv',results),('per_query_summary.csv',perquery),('pivot_comparison.csv',comparators)]:
        write_csv(a.out/name,rows)
    save(a.out/'SUMMARY.json',dict(base_commit=im['projection_base_commit'],decision=verdict,distinct_cells=len(results),
        queries=im['queries'],N=1000000,D=960,K=8,B=1,levels=[3,4,5],leaf_alias=5,
        results=results,truth=truth_rows,pivot_comparators=comparators,kill_K3_all_levels=k3,
        stage_C_required=verdict=='INTERMEDIATE_NEEDS_DIRECTION_TEST',
        scope='exact-safe CPU offline counts on original tree, eight frozen stratified queries; no latency or population inference',
        intervals_sha256=sha(a.run/'intervals.npz'),ancestors_sha256=sha(a.ancestors),contract_sha256=sha(HERE/'CONTRACT.json')))
    save(a.out/'VALIDATION.json',dict(status='PASS',stage_A='PASS',validations=validations,
        candidate_bounds_checked=sum(x['bounds_checked'] for x in validations),
        false_topK_prunes=0,bound_above_truth=0,C0_bridge=True,original_ownership_unchanged=True,
        native_full_path_retained=True,new_certificate_level_local=True,serialized_metadata=records,
        basis_contraction_independently_rechecked=True,GPU_used=False,
        source_sha256=sha(Path(__file__)),math_sha256=sha(HERE/'projection_math.py'),
        elapsed_resource_seconds=time.monotonic()-started))
    print('Decision',verdict)
    for x in last:print(x['family'],x['level'],'gap',x['oracle_gap_coverage'],'G0 incremental',x['incremental_G0_pruning'])
if __name__=='__main__':main()
