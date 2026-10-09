#!/usr/bin/env python3
"""Two occurrence-preserving static diagnostics, not dynamic performance evidence."""
import argparse
import csv
import fcntl
import json
import os
import shutil
from pathlib import Path
import struct
import sys
import subprocess
import time
import numpy as np
if not __debug__:raise RuntimeError('Assertions required')
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import validate
import oracle
from campaign import sha,save,recipe


def snapshot_rows(n,operations):
    base=np.arange(n,dtype=np.int64);alive=np.ones(n,bool);buffer=[];first=None;queries=[]
    for step,(flag,index) in enumerate(operations):
        if flag==0:
            buffer.append(int(base[index]))
            if len(buffer)==10:
                base=np.r_[base[alive],np.asarray(buffer,dtype=np.int64)];alive=np.ones(len(base),bool);buffer=[]
                if first is None:first=(step,base.copy())
        elif flag==1:
            positions=np.flatnonzero(alive)
            if index<len(positions):alive[positions[index]]=False
            else:buffer.pop(index-len(positions))
        else:queries.append(dict(step=step,physical_qid=index,original_row=int(base[index])))
    assert first is not None
    initial=[dict(q,workflow_qid=q['physical_qid'],physical_qid=q['original_row']) for q in queries[:32]]
    rebuilt=[q for q in queries if q['step']>first[0]][:32]
    assert len(initial)==len(rebuilt)==32
    for q in initial:assert q['original_row']==q['physical_qid']
    for q in rebuilt:assert q['original_row']==first[1][q['physical_qid']]
    return [('initial',np.arange(n,dtype=np.int64),initial,-1),('first_rebuilt',first[1],rebuilt,first[0])]


def prepare(a):
    run=recipe()
    data=validate.verify_target_data(a.data);ops=run.short_operations(len(data))
    assert np.array_equal(np.loadtxt(a.events,skiprows=1,dtype=np.int64),ops)
    a.work.mkdir(parents=True,exist_ok=False);records=[]
    for name,lineage,queries,step in snapshot_rows(len(data),ops):
        folder=a.work/name;folder.mkdir()
        if name=='initial':path=a.data.resolve()
        else:
            path=folder/'data.f32bin'
            with path.open('wb') as f:
                f.write(struct.pack('<iii',data.shape[1],len(lineage),2))
                for start in range(0,len(lineage),4096):f.write(np.asarray(data[lineage[start:start+4096]],dtype='<f4').tobytes())
        np.save(folder/'lineage.npy',lineage)
        (folder/'events.txt').write_text('32\n'+''.join(f"3 {q['physical_qid']}\n" for q in queries))
        snapshot=validate.load(path)
        for q in queries:assert snapshot[q['physical_qid']].tobytes()==data[q['original_row']].tobytes()
        save(folder/'SNAPSHOT.json',dict(name=name,N=len(lineage),D=data.shape[1],Q=32,B=1,K=8,source_step=step,
            data_sha256=sha(path),events_sha256=sha(folder/'events.txt'),lineage_sha256=sha(folder/'lineage.npy'),queries=queries,
            distinct_original_rows=len(np.unique(lineage)),duplicate_occurrences=len(lineage)-len(np.unique(lineage)),
            exact_query_coordinates_verified=True))
        records.append(dict(name=name,data=str(path.resolve()),folder=str(folder.resolve())))
    save(a.work/'REGISTERED.json',dict(records=records,script_sha256=sha(Path(__file__)),source_data_sha256=sha(a.data),
        source_events_sha256=sha(a.events),contract_sha256=sha(HERE/'SNAPSHOT_CONTRACT.json'),status='REGISTERED_BEFORE_GPU_DIAGNOSTICS'))
    print('PASS original and first-rebuilt occurrence lineage; 64 query coordinates verified',flush=True)



def execute(a):
    registered=json.loads((a.work/'REGISTERED.json').read_text())
    assert registered['contract_sha256']==sha(HERE/'SNAPSHOT_CONTRACT.json')
    if not a.remaining_only:assert registered['script_sha256']==sha(Path(__file__))
    binary=a.build/'bin/target';binary_hash=sha(binary)
    for name in ('QUALIFICATION.json','OBSERVER.json'):
        gate=json.loads((a.admission/name).read_text())
        assert gate['passed'] and gate['evidence_binding'] and gate['binary_sha256']==binary_hash
        assert gate['data_sha256']==registered['source_data_sha256']
    if a.remaining_only:
        original=json.loads((a.work/'EXECUTION_REGISTERED.json').read_text())
        assert a.executed_driver and sha(a.executed_driver)==original['script_sha256'] and original['binary_sha256']==binary_hash
        for label in ('initial_FULL','initial_BOUND'):assert json.loads((a.work/'guard'/label/'receipt.json').read_text())['runtime_valid']
        failed=a.work/'guard/initial_FLAT';receipt=json.loads((failed/'receipt.json').read_text())
        assert not receipt['runtime_valid'] and receipt['exit_code']==1 and receipt['stop_reason'] is None
        assert "ModuleNotFoundError: No module named 'faiss'" in (failed/'stderr.log').read_text()
        assert not list((a.work/'outputs').glob('initial_FLAT.*')),'failed native import must precede all measured payloads'
        assert not (a.work/'RESUME_REGISTERED.json').exists(),'only this one non-GPU import recovery is admitted'
        save(a.work/'RESUME_REGISTERED.json',dict(script_sha256=sha(Path(__file__)),parent_execution_sha256=sha(a.work/'EXECUTION_REGISTERED.json'),
            original_driver_sha256=sha(a.executed_driver),binary_sha256=binary_hash,
            remaining=['initial_FLAT','first_rebuilt_FULL','first_rebuilt_BOUND','first_rebuilt_FLAT'],
            reason='preserve virtual-environment executable symlink path; failed import occurred before any GPU native work; retain two completed GTS diagnostics',
            invalid_import_receipt_sha256=sha(failed/'receipt.json'),failed_stderr_sha256=sha(failed/'stderr.log')))
    else:
        registered.update(binary_sha256=binary_hash,guard_sha256=sha(a.guard),executor_registered_unix=time.time())
        save(a.work/'EXECUTION_REGISTERED.json',registered)
        (a.work/'outputs').mkdir(exist_ok=False)
    with Path(f'/tmp/gts_target_workflow_campaign_{a.gpu}.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for record in registered['records']:
            folder=Path(record['folder']);spec=json.loads((folder/'SNAPSHOT.json').read_text())
            assert sha(record['data'])==spec['data_sha256'] and sha(folder/'events.txt')==spec['events_sha256']
            for mode in ('FULL','BOUND','FLAT'):
                label=record['name']+'_'+mode
                if a.remaining_only and label in ('initial_FULL','initial_BOUND'):continue
                prefix=a.work/'outputs'/label
                if mode=='FLAT':
                    command=[str(a.faiss_python.absolute()),str(Path(__file__).resolve()),'native','--data',record['data'],'--snapshot',record['folder'],'--output',str(prefix)]
                else:
                    command=[str(Path(shutil.which('env')).resolve()),'REGION_MODE=PAR_STRONG','KNN_MODE='+mode,'TARGET_WARMUP=1','U10_OBSERVE=1','U10_TREE_AUDIT=0','TARGET_RESTORE_AUDIT=0',
                        str(binary.resolve()),record['data'],str(folder/'events.txt'),'2','0.705625057220459',str(prefix),'8']
                env=dict(os.environ)
                for key in list(env):
                    if key.startswith(('TARGET_','U10_','KNN_','REGION_','PAR_STALE')):env.pop(key,None)
                assert Path(command[0]).is_absolute() and Path(command[0]).is_file(),'guard requires an absolute executable for identity receipt'
                guard=a.work/'guard'/(label+'_retry' if a.remaining_only and label=='initial_FLAT' else label)
                result=subprocess.run([sys.executable,str(a.guard.resolve()),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(guard),'--',*command],
                    env=env,text=True,capture_output=True)
                (a.work/(label+('_retry' if a.remaining_only and label=='initial_FLAT' else '')+'.outer.log')).write_text(result.stdout+result.stderr)
                assert result.returncode==0,result.stdout+result.stderr
                receipt=json.loads((guard/'receipt.json').read_text());assert receipt['runtime_valid']
                assert not any(check['foreign'] for check in json.loads((guard/'checks.json').read_text()))
                assert sha(binary)==binary_hash
                if not a.remaining_only:assert sha(Path(__file__))==registered['script_sha256']
                print('PASS guarded static',label,flush=True)


def native(a):
    import faiss
    assert faiss.__version__=='1.15.1' and 'GPU' in faiss.get_compile_options()
    assert os.environ.get('CUDA_VISIBLE_DEVICES'),'existing guarded single GPU required'
    spec=json.loads((a.snapshot/'SNAPSHOT.json').read_text());assert sha(a.data)==spec['data_sha256']
    data=validate.load(a.data);qids=[q['physical_qid'] for q in spec['queries']]
    binding=sys.modules[faiss.GpuIndexFlatL2.__module__]
    extensions={name:sha(Path(module.__file__)) for name,module in vars(binding).items() if name.startswith('_swigfaiss') and hasattr(module,'__file__')}
    assert extensions,'runtime-loaded native Faiss extension identity required'
    faiss.omp_set_num_threads(16);setup=time.perf_counter()
    resources=faiss.StandardGpuResources();config=faiss.GpuIndexFlatConfig();config.device=0;config.useFloat16=False
    if hasattr(config,'use_cuvs'):config.use_cuvs=False
    index=faiss.GpuIndexFlatL2(resources,data.shape[1],config);index.add(data);resources.syncDefaultStreamCurrentDevice()
    setup_ms=(time.perf_counter()-setup)*1000;assert index.ntotal==len(data)
    def query(qid):
        q=np.array(data[qid:qid+1],dtype=np.float32,order='C',copy=True)
        ds,ids=index.search(q,8);ids=ids.astype(np.int32);fields=np.sqrt(np.maximum(ds,np.float32(0)))
        resources.syncDefaultStreamCurrentDevice();return ids[0],fields[0],ds[0]
    warm=time.perf_counter()
    for qid in qids[:8]:query(qid)
    warm_ms=(time.perf_counter()-warm)*1000
    # Retaining full returned payloads is part of the Host-ready pass.
    ids=np.empty((32,8),np.int32);fields=np.empty((32,8),np.float32);squared=np.empty_like(fields);per_query=[]
    begin=time.perf_counter()
    for i,qid in enumerate(qids):
        tick=time.perf_counter();ids[i],fields[i],squared[i]=query(qid);per_query.append((time.perf_counter()-tick)*1000)
    pass_ms=(time.perf_counter()-begin)*1000
    release=time.perf_counter();del index;resources.syncDefaultStreamCurrentDevice();del resources
    release_ms=(time.perf_counter()-release)*1000;service_ms=(time.perf_counter()-begin)*1000
    ids.tofile(str(a.output)+'.ids.i32');fields.tofile(str(a.output)+'.dist.f32');squared.tofile(str(a.output)+'.native_squared.f32')
    save(Path(str(a.output)+'.native.json'),dict(backend='native Faiss GpuIndexFlatL2, FP32 storage, no cuVS',faiss_version=faiss.__version__,
        compile_options=faiss.get_compile_options(),faiss_extension_sha256=extensions,setup_ms=setup_ms,warmup_ms=warm_ms,warmup_queries=8,
        query_pass_ms=pass_ms,final_release_ms=release_ms,service_trace_ms=service_ms,per_query_ms=per_query,
        negative_squared_slots=int((squared<0).sum()),snapshot_sha256=sha(a.snapshot/'SNAPSHOT.json'),
        scope='one static 32-query B1K8 Host-ready pass plus final index/resource release; no updates or tree maintenance; not dynamic e2e'))
    print('PASS native Flat diagnostic payload',flush=True)



def native_outputs(prefix):
    arrays=[]
    for suffix,dtype in (('.ids.i32','<i4'),('.dist.f32','<f4'),('.native_squared.f32','<f4')):
        path=Path(str(prefix)+suffix);assert path.stat().st_size==32*8*4,'native complete payload byte length'
        arrays.append(np.fromfile(path,dtype=dtype).reshape(32,8))
    return arrays


def field_quality(fields,native_squared,reference_squared):
    finite=bool(np.isfinite(fields).all() and np.isfinite(native_squared).all() and len(fields)>0)
    if not finite:return float('inf'),float('inf'),False
    denominator=np.maximum(reference_squared,1.)
    field_error=float((np.abs(fields.astype(np.float64)**2-reference_squared)/denominator).max())
    raw_error=float((np.abs(native_squared.astype(np.float64)-reference_squared)/denominator).max())
    return field_error,raw_error,True


def check(a):
    registered=json.loads((a.work/'EXECUTION_REGISTERED.json').read_text());records=registered['records']
    resume=None
    if (a.work/'RESUME_REGISTERED.json').exists():
        resume=json.loads((a.work/'RESUME_REGISTERED.json').read_text())
        assert resume['script_sha256']==sha(Path(__file__)) and resume['parent_execution_sha256']==sha(a.work/'EXECUTION_REGISTERED.json')
        assert a.executed_driver and sha(a.executed_driver)==registered['script_sha256']==resume['original_driver_sha256']
    else:assert registered['script_sha256']==sha(Path(__file__))
    guard_hashes={}
    for record in records:
        for mode in ('FULL','BOUND','FLAT'):
            label=record['name']+'_'+mode
            folder=a.work/'guard'/(label+'_retry' if resume and label=='initial_FLAT' else label)
            receipt=json.loads((folder/'receipt.json').read_text());checks=json.loads((folder/'checks.json').read_text())
            assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and checks and not any(check['foreign'] for check in checks)
            assert not json.loads((folder/'after.json').read_text())['apps']
            guard_hashes[str(folder.relative_to(a.work))]=dict(receipt_sha256=sha(folder/'receipt.json'),checks_sha256=sha(folder/'checks.json'))
    from campaign import verify_cpu_library
    CPU_binding=verify_cpu_library(a.library)
    scores=oracle.install(a.library);reports=[]
    for record in records:
        folder=Path(record['folder']);data=validate.load(record['data']);spec=json.loads((folder/'SNAPSHOT.json').read_text())
        assert sha(record['data'])==spec['data_sha256'] and sha(folder/'events.txt')==spec['events_sha256']
        quality={};internal=[]
        for mode in ('FULL','BOUND'):
            prefix=a.work/'outputs'/f"{record['name']}_{mode}"
            validate.scores=scores;quality[mode]=validate.check(record['data'],folder/'events.txt',prefix,.705625057220459,8,(1,mode))
            validate.check(record['data'],a.warm_events,Path(str(prefix)+'.warmup'),.705625057220459,8,(1,mode))
            internal.append(tuple(sha(Path(str(prefix)+s)) for s in ('.ids.i32','.dist.f32','.queries.csv')))
        assert internal[0]==internal[1]
        prefix=a.work/'outputs'/f"{record['name']}_FLAT"
        ii,dd,native_sq=native_outputs(prefix)
        recalls=[];field_errors=[];raw_errors=[];bad_queries=[];invalid_slots=0;repeated_slots=0
        for q,query in enumerate(spec['queries']):
            sq=scores(data,np.arange(len(data)),data[query['physical_qid']]);order=np.lexsort((np.arange(len(data)),sq))[:8]
            boundary=sq[order[-1]];closer=set(map(int,np.flatnonzero(sq<boundary)));ties=set(map(int,np.flatnonzero(sq==boundary)))
            valid=(ii[q]>=0)&(ii[q]<len(data));returned=set(map(int,ii[q][valid]))
            invalid_slots+=int((~valid).sum());repeated_slots+=int(valid.sum())-len(returned)
            recall=(len(returned&closer)+min(8-len(closer),len(returned&ties)))/8;recalls.append(recall)
            field_error,raw_error,finite=field_quality(dd[q][valid],native_sq[q][valid],sq[ii[q][valid]])
            field_errors.append(field_error);raw_errors.append(raw_error)
            if recall!=1 or field_error>5e-5 or raw_error>5e-5 or not valid.all() or len(returned)!=8:
                bad_queries.append(dict(query=q,recall=recall,field_max_relative_scale1=field_error if finite else None,
                    native_squared_max_relative_scale1=raw_error if finite else None,all_fields_finite=finite,
                    returned_ids=ii[q].tolist(),reference_ids=order.tolist()))

        quality['FLAT']=dict(recall_tie_aware=float(np.mean(recalls)),complete_query_fraction=float(np.mean(np.asarray(recalls)==1)),
            per_query_recall=recalls,invalid_slots=invalid_slots,repeated_slots=repeated_slots,
            squared_distance_max_relative_scale1=max(field_errors) if np.isfinite(field_errors).all() else None,distance_tolerance=5e-5,
            native_squared_max_relative_scale1=max(raw_errors) if np.isfinite(raw_errors).all() else None,distance_tolerance_pass=max(field_errors)<=5e-5 and max(raw_errors)<=5e-5,mismatched_queries=bad_queries,
            passed=not bad_queries,scope='independent CPU ordered-FP64 full scan; genuine exact-distance boundary ties allowed')
        timing={}
        for mode in ('FULL','BOUND'):
            prefix=a.work/'outputs'/f"{record['name']}_{mode}"
            s=json.loads(Path(str(prefix)+'.summary.json').read_text());r=json.loads(Path(str(prefix)+'.region.json').read_text())
            with Path(str(prefix)+'.ops.csv').open() as f:ops=list(csv.DictReader(f))
            timing[mode]=dict(service_trace_ms=s['trace_ms'],final_release_ms=s['final_drain_ms'],
                query_ack_sum_ms=sum(float(o['ack_ms']) for o in ops),initial_setup_ms=r['setup_ms'],
                scope='static 32-query continuous U10 trace including buffer preparation and final service release; cloned warmup/setup separate')
        timing['FLAT']=json.loads((a.work/'outputs'/f"{record['name']}_FLAT.native.json").read_text())
        reports.append(dict(snapshot=spec,quality=quality,timing=timing,internal_complete_byte_identity=True))
    save(a.work/'STATIC_RESULTS.json',dict(status='SIX_SINGLE_STATIC_DIAGNOSTICS_NOT_DYNAMIC_E2E',reports=reports,
        CPU_library_sha256=sha(a.library),CPU_binding=CPU_binding,guard_hashes=guard_hashes,execution_registered_sha256=sha(a.work/'EXECUTION_REGISTERED.json'),resume_registration=resume,output_hashes={p.name:sha(p) for p in sorted((a.work/'outputs').iterdir()) if p.is_file()},external_speed_preserved=True,default_promoted=False,long_admitted=False))
    print('PASS static diagnostic report; native speed and mismatches retained',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','execute','native','check'))
    for name in ('work','data','events','snapshot','output','library','warm-events','build','guard','admission','faiss-python','executed-driver'):p.add_argument('--'+name,type=Path)
    p.add_argument('--gpu');p.add_argument('--numa-node',type=int);p.add_argument('--remaining-only',action='store_true')
    a=p.parse_args()
    run=recipe()
    if a.work is not None:a.work=run.base.outside_repo(a.work)
    if a.output is not None:a.output=run.base.outside_repo(a.output)
    {'prepare':prepare,'execute':execute,'native':native,'check':check}[a.action](a)
