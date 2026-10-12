#!/usr/bin/env python3
"""Full same-P2 safety, complementary masks, and exact integer decision gates."""
import argparse, csv, gzip, io, json, os, resource, struct, sys, time
from pathlib import Path
from fractions import Fraction
import numpy as np
from views import HERE, sha, save, bounds, scalar_bound, configurations, exact_gram_bound, endpoints, decision, ETA, RHO
sys.path.insert(0,str(HERE.parent/'projection_certificate_20261011'))
from build_projection import ordered

def csv_write(path, rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser()
    for k in ['data','old-projected','scores','prior-run','build','out']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())
    assert sha(HERE/'CONTRACT.json')==im['contract_sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and len(os.sched_getaffinity(0))==1
    assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']) and os.getpriority(os.PRIO_PROCESS,0)>=10
    assert sha(a.data)==im['data_sha256'] and sha(a.old_projected)==im['projected_sha256'] and sha(a.scores)==im['scores_sha256']
    assert struct.unpack('<4i',a.scores.open('rb').read(16))==(1000000,960,8,8)
    assert sha(a.prior_run/'PCA_BALANCED.i32')==im['P2_permutation_sha256']
    assert sha(a.prior_run/'PCA_BALANCED.npz')==im['old_P2_metadata_sha256']
    manifest=json.loads((a.build/'VIEW_MANIFEST.json').read_text());receipt=json.loads((a.build/'BUILD_RECEIPT.json').read_text())
    assert sha(a.build/'projected.f64')==receipt['projected_sha256']
    basis=json.loads((HERE.parent/'projection_certificate_20261011/evidence/BASIS.json').read_text())
    oldp=np.array([[float.fromhex(t) for t in row] for row in basis['families']['PCA']])
    newp=np.array([[float.fromhex(t) for t in row] for row in manifest['projected_direction_hex']]);matrices=np.concatenate([oldp,newp])
    cfg,aliases=configurations();assert cfg==manifest['physical_configs'] and aliases==manifest['aliases']
    for c in cfg:
        for g in c['groups']:assert exact_gram_bound(matrices[g])[0]<=1
    z=np.concatenate([np.memmap(a.old_projected,dtype='<f8',mode='r',shape=(1000000,16))[:,8:16],np.memmap(a.build/'projected.f64',dtype='<f8',mode='r',shape=(1000000,32))],axis=1)
    assert np.isfinite(z).all()
    scores=np.memmap(a.scores,dtype='<f8',offset=16,mode='r',shape=(8,1000000));assert np.isfinite(scores).all() and (scores>=0).all()
    perm=np.fromfile(a.prior_run/'PCA_BALANCED.i32',dtype='<i4');assert np.array_equal(np.sort(perm),np.arange(1000000))
    old=np.load(a.prior_run/'PCA_BALANCED.npz');u_sq=np.array([float.fromhex(t) for t in im['U_star_squared_hex']]);u=np.sqrt(u_sq);queries=z[im['queries']]
    for qi in range(8):assert np.partition(scores[qi],7)[7]==u_sq[qi]
    oldrows=list(csv.DictReader((HERE.parent/'certificate_effectiveness_split_20261012/evidence/per_level_summary.csv').open()))
    oldby={int(r['level']):r for r in oldrows if r['partition']=='PCA_BALANCED'}
    aggregate=[];pq=[];qv=[];overlap=[];regionoverlap=[];cost=[];metas={};masks={};scalar_checks=0;viewchecks=0;multichecks=0
    # Query-independent original-vector region fixtures fixed before prune results.
    rng=np.random.default_rng(20261014);fixtures=[]
    for l,size in [(3,1000),(4,100),(5,10)]:
        for ri in sorted(rng.choice(10**l,4,replace=False)):
            fixtures.append(dict(level=l,region_index=int(ri),object_ids=perm[int(ri)*size:(int(ri)+1)*size]))
    ids=np.unique(np.concatenate([np.array(im['queries']),*[f['object_ids'] for f in fixtures]]))
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960))
    independent=ordered(x[ids],matrices);assert np.array_equal(independent,z[ids]),'full sampled regions original-vector ordered projection'
    positions={int(v):i for i,v in enumerate(ids)}
    for l,size in [(3,1000),(4,100),(5,10)]:
        rz=z[perm].reshape(10**l,size,40);minimum=rz.min(1);maximum=rz.max(1);lo,hi=endpoints(minimum,maximum)
        assert np.all(lo.astype('f8')<=np.nextafter(minimum-ETA,-np.inf)) and np.all(hi.astype('f8')>=np.nextafter(maximum+ETA,np.inf)), 'full coverage'
        assert np.array_equal(lo[:,:8],old[f'low_{l}']) and np.array_equal(hi[:,:8],old[f'high_{l}'])
        truth=np.array([scores[qi,perm].reshape(10**l,size).min(1) for qi in range(8)])
        assert truth.tobytes()==old[f'truth_sq_{l}'].tobytes(),'own-P2 original truth bridge'
        d=np.sqrt(truth);truth_prunable=(truth>u_sq[:,None]).sum(1)*size
        assert np.array_equal(truth>u_sq[:,None],d>u[:,None])
        metas.update({f'low_{l}':lo,f'high_{l}':hi,f'truth_sq_{l}':truth})
        for f in (f for f in fixtures if f['level']==l):
            values=independent[[positions[int(i)] for i in f['object_ids']]];ri=f['region_index']
            assert np.all(lo[ri].astype('f8')<=np.nextafter(values-ETA,-np.inf)) and np.all(hi[ri].astype('f8')>=np.nextafter(values+ETA,np.inf))
        cell_masks={};cell_bounds={}
        for c in cfg:
            groups=c['groups'];v=len(groups);k=len(groups[0]);name=c['config']
            view_lb=np.array([[bounds(lo[:,g],hi[:,g],q[g]) for q in queries] for g in groups])
            assert np.all(view_lb<=d[None,:,:]),'constituent lower bound exceeds own truth'
            multi=view_lb.max(0);assert np.all(multi<=d)
            mask=view_lb>u[None,:,None];union=mask.any(0);multiplicity=mask.sum(0)
            assert not np.any(union & (truth<=u_sq[:,None])) and not np.any(mask & (truth<=u_sq[:,None])[None,:,:])
            viewchecks+=view_lb.size;multichecks+=multi.size
            cell_masks[name]=union;cell_bounds[name]=multi;masks[f'{name}_L{l}']=mask
            index=np.concatenate(groups);packed=np.stack([lo[:,index],hi[:,index]],axis=-1).astype('<f4').reshape(10**l,16)
            assert packed.nbytes==64*10**l
            packed.tofile(a.out/f'{name}_L{l}.metadata.f32')
            numbers=union.sum(1,dtype=np.int64)*size;individual=mask.sum(2,dtype=np.int64)*size
            alignment=numbers/truth_prunable;hard_n=int(numbers[2:].sum());hard_d=int(truth_prunable[2:].sum())
            perview_hard=individual[:,2:].sum(1)/hard_d;perview_all=individual.sum(1)/int(truth_prunable.sum())
            row=dict(config=name,family=c['family'],layout=c['layout'],level=l,views=v,dims_per_view=k,metadata_bytes_per_region=64,
                pruned_objects=int(numbers.sum()),truth_prunable_objects=int(truth_prunable.sum()),alignment=float(numbers.sum()/truth_prunable.sum()),
                hard_pruned_objects=hard_n,hard_truth_prunable_objects=hard_d,hard_alignment=hard_n/hard_d,
                hard_query_pruned=numbers[2:].tolist(),hard_query_truth_prunable=truth_prunable[2:].tolist(),worst_hard_alignment=float(min(alignment[2:])),
                hard_coverage_40=int(sum(Fraction(int(n),int(d0))>=Fraction(2,5) for n,d0 in zip(numbers[2:],truth_prunable[2:]))),
                hard_coverage_60=int(sum(Fraction(int(n),int(d0))>=Fraction(3,5) for n,d0 in zip(numbers[2:],truth_prunable[2:]))),
                complementarity_gain_all=float(numbers.sum()/truth_prunable.sum()-max(perview_all)),complementarity_gain_hard=float(hard_n/hard_d-max(perview_hard)),
                unique_pruned_objects=int((multiplicity==1).sum()*size),shared_union_pruned_objects=int((multiplicity>=2).sum()*size),canary_359924_alignment=float(alignment[2]))
            assert row['unique_pruned_objects']+row['shared_union_pruned_objects']==row['pruned_objects']
            aggregate.append(row)
            for qi,qid in enumerate(im['queries']):
                pq.append(dict(config=name,family=c['family'],layout=c['layout'],level=l,query_id=qid,hard=qi>=2,pruned_objects=int(numbers[qi]),truth_prunable_objects=int(truth_prunable[qi]),alignment=float(alignment[qi]),safe_pruned_fraction=float(numbers[qi]/1000000),
                               complementarity_gain=float(alignment[qi]-max(individual[:,qi]/truth_prunable[qi]))))
                for vi in range(v):
                    unique=int(np.count_nonzero(mask[vi,qi] & (multiplicity[qi]==1))*size)
                    shared=int(np.count_nonzero(mask[vi,qi] & (multiplicity[qi]>=2))*size)
                    assert unique+shared==individual[vi,qi]
                    qv.append(dict(config=name,family=c['family'],layout=c['layout'],level=l,query_id=qid,hard=qi>=2,view=vi,
                        pruned_objects=int(individual[vi,qi]),truth_prunable_objects=int(truth_prunable[qi]),alignment=float(individual[vi,qi]/truth_prunable[qi]),safe_pruned_fraction=float(individual[vi,qi]/1000000),
                        unique_pruned_objects=unique,shared_pruned_objects=shared,unique_pruned_fraction=unique/1000000))
                for ri in [0,len(lo)//2,len(lo)-1]:
                    for vi,g in enumerate(groups):
                        assert scalar_bound(lo[ri,g],hi[ri,g],queries[qi,g])==view_lb[vi,qi,ri];scalar_checks+=1
            for i in range(v):
                for j in range(i+1,v):
                    common=mask[i]&mask[j];either=mask[i]|mask[j]
                    for qi,qid in enumerate(im['queries']):
                        ni=int(common[qi].sum()*size);nu=int(either[qi].sum()*size)
                        overlap.append(dict(config=name,level=l,query_id=qid,view_a=i,view_b=j,intersection_pruned_objects=ni,union_pruned_objects=nu,jaccard=ni/nu if nu else 0.,both_empty=nu==0))
                    # Joint histogram of per-region common/union query counts covers every region.
                    hist=np.bincount(common.sum(0)*9+either.sum(0),minlength=81).reshape(9,9)
                    assert hist.sum()==10**l
                    for ni,nu in zip(*np.nonzero(hist)):
                        regionoverlap.append(dict(config=name,level=l,view_a=i,view_b=j,intersection_query_count=int(ni),union_query_count=int(nu),regions=int(hist[ni,nu])))
            qregions=8*10**l
            cost.append(dict(config=name,level=l,views=v,metadata_bytes_per_region=64,total_metadata_bytes=64*10**l,query_projection_coordinate_updates=8*8*960,
                shared_basis_bytes_per_configuration=8*960*8,query_coordinate_cache_bytes_per_query=64,bound_evaluations=v*qregions,
                gap_subtractions=16*qregions,square_multiplications=8*qregions,sum_additions=8*qregions,sqrt_evaluations=v*qregions,
                slack_subtractions=v*qregions,view_max_comparisons=(v-1)*qregions,strict_prune_comparisons=qregions,
                metadata_read_proxy_bytes=64*qregions,remaining_full_distance_coordinate_updates=(8000000-row['pruned_objects'])*960,
                cost_scope='symbolic scalar arithmetic counts; excludes comparisons/nextafter unless separately named, not timing'))
        for name in ['BLOCKS_2x4','BLOCKS_4x2','BLOCKS_8x1','INTERLEAVED_2x4','INTERLEAVED_4x2']:
            assert np.all(cell_bounds[name]<=cell_bounds['PCA8']), 'same-basis domination failed'
        assert np.all(cell_bounds['BLOCKS_8x1']<=cell_bounds['BLOCKS_4x2']) and np.all(cell_bounds['BLOCKS_4x2']<=cell_bounds['BLOCKS_2x4'])
        keeper=next(r for r in aggregate if r['config']=='PCA8' and r['level']==l)
        assert keeper['pruned_objects']==int(oldby[l]['safe_pruned_objects']) and keeper['hard_pruned_objects']==6000000-int(oldby[l]['hard_certificate_remaining_objects']), 'G5 exact count bridge'
        print('L'+str(l)+': all per-view/max truth checks, full coverage, nesting, keeper bridge PASS',flush=True)
    for r in aggregate:
        b=next(b for b in aggregate if b['level']==r['level'] and b['config']=='PCA8')
        r['hard_gain_over_PCA8']=r['hard_alignment']-b['hard_alignment'];r['worst_gain_over_PCA8']=r['worst_hard_alignment']-b['worst_hard_alignment']
    csv_write(a.out/'per_level_summary.csv',[{k:v for k,v in r.items() if not isinstance(v,list)} for r in aggregate])
    csv_write(a.out/'per_query_summary.csv',pq);csv_write(a.out/'query_view_gain.csv',qv)
    csv_write(a.out/'prune_overlap.csv',overlap);csv_write(a.out/'region_overlap_summary.csv',regionoverlap);csv_write(a.out/'cost_accounting.csv',cost)
    np.savez_compressed(a.out/'metadata_and_truth.npz',**metas,query_projection=queries)
    np.savez_compressed(a.out/'constituent_prune_masks.npz',**masks)
    save(a.out/'aggregate_summary.json',dict(base_commit=im['base_commit'],partition='PCA_BALANCED',metadata_budget_bytes=64,physical_cells=36,logical_cells=48,aliases=aliases,rows=aggregate,**decision(aggregate),
         scientific_scope='only the frozen view families/P2/eight queries; no impossibility theorem, no held-out/GPU/latency result'))
    save(a.out/'SAFETY_VALIDATION.json',dict(status='PASS',G1_exact_rational_views=True,G2_full_coordinate_coverage=True,G3_constituent_bound_truth_comparisons=viewchecks,G3_multi_bound_truth_comparisons=multichecks,
         bound_above_truth=0,false_topK_prunes=0,G5_keeper_exact_counts=True,own_P2_truth_bytes_identical=True,same_basis_domination_and_nested_blocks=True,
         independent_scalar_bound_checks=scalar_checks,independent_original_vector_rows=len(ids),independent_original_projection_values=len(ids)*40,
         independently_covered_regions=[{k:v for k,v in f.items() if k!='object_ids'} for f in fixtures],ETA=ETA,RHO=RHO,GPU_used=False,
         source_hashes={p.name:sha(p) for p in [HERE/'CONTRACT.json',HERE/'views.py',Path(__file__)]},no_latency_measured=True))
    save(a.out/'EVAL_RECEIPT.json',dict(CPU_affinity_count=1,python=sys.version.split()[0],numpy=np.__version__,no_latency_measured=True,elapsed_resource_seconds=time.monotonic()-start,process_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    save(a.out/'OUTPUT_MANIFEST.json',{f.name:dict(bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(a.out.iterdir()) if f.is_file()})
    print(json.dumps(decision(aggregate)),flush=True)

if __name__=='__main__':main()
