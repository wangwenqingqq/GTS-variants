#!/usr/bin/env python3
"""Full-output static gates; reference arithmetic is outside all native timings."""
import csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from qualify import cpu
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text())

def requests(qids,method,order):
    tasks=['knn'] if method=='GPU_FLAT_KNN' else ['range'] if method=='GPU_RANGE_COMPLETE' else order.split(',')
    return [(task,q) for count in (8,32) for task in tasks for q in qids[:count]]

def reference(data,qids,library,output):
    sys.path.insert(0,str(HERE.parent/'unified_target_workflow/phase_b'))
    import oracle
    from campaign import verify_cpu_library
    binding=verify_cpu_library(library);scores=oracle.install(library);x=cpu.validate.load(data)
    output.mkdir(parents=True,exist_ok=False);files={}
    for q in sorted(set(qids)):
        p=output/f'{q}.f64';scores(x,np.arange(len(x)),x[q]).astype('<f8').tofile(p);files[str(q)]=cpu.sha(p)
    cpu.save(output/'REFERENCE.json',dict(data_sha256=cpu.sha(data),library_binding=binding,source_sha256=cpu.sha(__file__),N=len(x),D=x.shape[1],files=files))

def check(prefix,method,schedule,gold):
    meta=read(str(prefix)+'.static.json');expected_method='CPU_FLAT_INCLUSIVE_ADAPT' if method=='CPU_FLAT' else method
    assert meta['method']==expected_method and meta['queries']==len(schedule)
    for key in ('preparation_ms','build_ms','warmup_ms','release_ms'):
        assert math.isfinite(meta[key]) and meta[key]>=0
    tasks=set(t for t,q in schedule)
    for t in tasks:assert math.isfinite(meta[t+'_pass_ms']) and meta[t+'_pass_ms']>0
    p=Path(str(prefix)+'.queries.csv')
    with p.open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(schedule)
    if method=='GTSPP_P':
        with Path(str(prefix)+'.ops.csv').open() as f:ops=list(csv.DictReader(f))
        assert len(ops)==80
        for row,op in zip(rows,ops):row['ack_ms']=op['ack_ms'];row['task']='knn' if int(op['flag'])==3 else 'range'
        s=read(str(prefix)+'.summary.json');region=read(str(prefix)+'.region.json');live=read(str(prefix)+'.unified.json');numeric=read(str(prefix)+'.numeric.json');tiles=read(str(prefix)+'.build_tiles.json');scope=read(str(prefix)+'.scope.json')
        assert s['observe'] and not s['tree_audit'] and not scope['warmup'] and tiles['mode']=='TILED' and not tiles['audit']
        assert region['mode']==1 and live['knn_mode']=='FULL' and region['refreshes']==live['refreshes']==numeric['refreshes']==1 and tiles['build_calls']==1
        assert not region['final_owned_bytes'] and not live['final_owned_bytes'] and not numeric['final_bytes']
        assert meta['host_query_upload_bytes']==80*gold['D']*4 and meta['extra_nonindexed_query_bytes']==gold['D']*4
        assert all(int(o['base_before'])==int(o['base_after'])==gold['N'] and int(o['buffer_before'])==int(o['buffer_after'])==0 and float(o['rebuild_ms'])==0 for o in ops)
    total=sum(int(r['count']) for r in rows);assert total>=0
    arrays=[]
    for suffix,dtype,item in (('.ids.i32','<i4',4),('.dist.f32','<f4',4)):
        p=Path(str(prefix)+suffix);assert p.stat().st_size==total*item;arrays.append(np.fromfile(p,dtype=dtype))
    rawpath=Path(str(prefix)+'.native_squared.f64')
    if method!='GTSPP_P':assert rawpath.stat().st_size==total*8
    raw=np.fromfile(rawpath,dtype='<f8') if method!='GTSPP_P' else arrays[1].astype(np.float64)**2
    at=0;reports=[];canonical={};times={t:[] for t in tasks};warm_count=8*len(tasks)
    for i,(row,(task,q)) in enumerate(zip(rows,schedule)):
        count=int(row['count']);assert count>=0 and int(row['offset'])==at and int(row['qid'])==q and row['task']==task
        assert int(row['step'] if method=='GTSPP_P' else row['query'])==i
        ack=float(row['ack_ms']);assert math.isfinite(ack) and ack>=0
        sq=np.memmap(gold['folder']/f'{q}.f64',dtype='<f8',mode='r');sl=slice(at,at+count)
        assert np.isfinite(arrays[1][sl]).all() and (arrays[1][sl]>=0).all(), 'invalid Euclidean fields'
        if task=='knn':
            assert (np.diff(arrays[1][sl])>=0).all() and (np.diff(raw[sl])>=0).all(), 'unordered native kNN fields'
        result=cpu.quality(arrays[0][sl],arrays[1][sl],raw[sl],sq,task,.705625057220459);assert result['passed'],(i,task,q,result)
        if method=='GTSPP_P':
            expected=np.lexsort((np.arange(len(sq)),sq))[:8] if task=='knn' else np.flatnonzero(sq<=float(np.float32(.705625057220459))**2)
            actual_ids,actual_fields=arrays[0][sl],arrays[1][sl]
            if task=='range':
                order=np.argsort(actual_ids);actual_ids,actual_fields=actual_ids[order],actual_fields[order]
            assert np.array_equal(actual_ids,expected)
            assert np.array_equal(actual_fields.view(np.uint32),np.sqrt(sq[expected]).astype(np.float32).view(np.uint32))
        if method=='GTSPP_P':
            key=f'{task}_{q}';digest=hashlib.sha256(arrays[0][sl].tobytes()+arrays[1][sl].tobytes()).hexdigest()
            assert key not in canonical or canonical[key]==digest
            canonical[key]=digest
        if i>=warm_count:times[task].append(ack)
        reports.append(dict(query=i,task=task,**result));at+=count
    for t in tasks:assert len(times[t])==32 and meta[t+'_pass_ms']+1e-5>=sum(times[t])
    assert at==total
    return dict(passed=True,canonical_sha256=canonical,queries=len(rows),items=total,per_query=reports,timing=meta,per_query_ms=times,
        output_hashes={p.name:cpu.sha(p) for p in prefix.parent.glob(prefix.name+'.*')},scope='all warmup and measured members/fields; P exact per-ID FP64 field bits and kNN order; external native precision with frozen tolerance')
