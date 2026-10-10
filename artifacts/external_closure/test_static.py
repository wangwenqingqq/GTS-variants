#!/usr/bin/env python3
"""Balanced scheduling and fail-closed complete static-output regression check."""
import copy,json,tempfile,subprocess,sys
from pathlib import Path
import numpy as np
from static_campaign import CONTRACT,jobs,admission_structure,guard_labels
from static_check import requests,check

def main():
    from static_preflight import inspect
    assert inspect(sys.executable,"modules=[];versions={'fixture':True}")['versions']['fixture']
    try:inspect(sys.executable,"raise ImportError('missing dependency fixture')")
    except subprocess.CalledProcessError:pass
    else:raise AssertionError('missing dependency passed preflight')
    run=jobs('primary');assert len(run)==72 and len(jobs('qualification'))==6
    methods=set(j['method'] for j in run);assert len(methods)==6
    for left in methods:
        for right in methods-{left}:assert sum(o.index(left)<o.index(right) for o in CONTRACT['orders'])==3
    assert sum(j['method'].startswith('CPU') for j in run)==36
    for m in methods:
        schedule=requests(list(range(32)),m,'range,knn');tasks=set(t for t,q in schedule)
        assert len(schedule)==40*len(tasks)
        assert all(sum(t==task for t,q in schedule)==40 for task in tasks)
    labels={j['label'] for j in jobs('qualification')}
    reg=dict(jobs=jobs('qualification'),source_sha256={'runner':'old'},contract_sha256='contract',build_sha256='build',inputs_sha256='inputs',guard_sha256='guard',gpu='gpu',numa_node=2)
    binding={k:v for k,v in reg.items() if k!='jobs'};binding['registration_sha256']='registered'
    admitted=dict(passed=True,jobs=reg['jobs'],source_sha256=reg['source_sha256'],contract_sha256='contract',build_sha256='build',registration_sha256='registered',rows={k:{'passed':True} for k in labels},guard_hashes={k:{} for k in labels})
    admission_structure(admitted,reg,labels,binding)
    for mutation in ('drop_sanitizer','registration','inputs','guard','gpu','numa'):
        bad=copy.deepcopy(admitted);r=copy.deepcopy(reg)
        if mutation=='drop_sanitizer':bad['rows'].pop('P_bounded_synccheck');bad['guard_hashes'].pop('P_bounded_synccheck')
        elif mutation=='registration':bad['registration_sha256']='other'
        else:r[{'inputs':'inputs_sha256','guard':'guard_sha256','gpu':'gpu','numa':'numa_node'}[mutation]]='other'
        try:admission_structure(bad,r,labels,binding)
        except AssertionError:pass
        else:raise AssertionError('incomplete or stale qualification admitted')
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);guards=root/'guards';guards.mkdir()
        for label in labels:(guards/label).mkdir()
        admission_structure(admitted,reg,guard_labels(guards),binding)
        (guards/'extra_failed_without_receipt').mkdir()
        try:admission_structure(admitted,reg,guard_labels(guards),binding)
        except AssertionError:pass
        else:raise AssertionError('extra unreceipted process hidden from budget')
        prefix=root/'output';sq=np.arange(9,dtype='<f8');sq.tofile(root/'0.f64')
        ids=np.arange(8,dtype='<i4');fields=np.sqrt(sq[:8]).astype('<f4');np.tile(ids,40).tofile(str(prefix)+'.ids.i32');np.tile(fields,40).tofile(str(prefix)+'.dist.f32');np.tile(sq[:8],40).tofile(str(prefix)+'.native_squared.f64')
        Path(str(prefix)+'.queries.csv').write_text('task,query,qid,count,offset,ack_ms\n'+''.join(f'knn,{i},0,8,{i*8},1\n' for i in range(40)))
        meta=dict(method='GPU_FLAT_KNN',queries=40,preparation_ms=0,build_ms=1,warmup_ms=8,release_ms=1,knn_pass_ms=33)
        p=Path(str(prefix)+'.static.json');p.write_text(json.dumps(meta));gold=dict(N=9,D=1,folder=root)
        check(prefix,'GPU_FLAT_KNN',[('knn',0)]*40,gold)
        for key,val in [('knn_pass_ms',float('nan')),('knn_pass_ms',31),('queries',39)]:
            p.write_text(json.dumps({**meta,key:val}))
            try:check(prefix,'GPU_FLAT_KNN',[('knn',0)]*40,gold)
            except AssertionError:pass
            else:raise AssertionError('invalid static timing admitted')
        p.write_text(json.dumps(meta))
        for invalid in ('negative','reversed','nan'):
            bad=-fields if invalid=='negative' else fields[::-1] if invalid=='reversed' else np.full(8,np.nan,dtype='<f4')
            np.tile(bad,40).astype('<f4').tofile(str(prefix)+'.dist.f32')
            np.tile(ids[::-1] if invalid=='reversed' else ids,40).tofile(str(prefix)+'.ids.i32')
            np.tile(sq[:8][::-1] if invalid=='reversed' else sq[:8],40).tofile(str(prefix)+'.native_squared.f64')
            try:check(prefix,'GPU_FLAT_KNN',[('knn',0)]*40,gold)
            except AssertionError:pass
            else:raise AssertionError('negative/nonfinite/unordered native kNN admitted')
        np.tile(fields,40).tofile(str(prefix)+'.dist.f32');np.tile(sq[:8],40).tofile(str(prefix)+'.native_squared.f64')
        Path(str(prefix)+'.ids.i32').write_bytes(ids.tobytes())
        try:check(prefix,'GPU_FLAT_KNN',[('knn',0)]*40,gold)
        except AssertionError:pass
        else:raise AssertionError('truncated full payload admitted')
    print('PASS 72 balanced entries,6 remaining qualifiers, complete-payload and timing rejection')
if __name__=='__main__':main()
