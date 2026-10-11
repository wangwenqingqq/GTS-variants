#!/usr/bin/env python3
"""CPU-only bounded pool scan, full interval aggregation, and independent samples."""
import argparse,json,os,resource,struct,subprocess,time
from pathlib import Path
import numpy as np
from audit import load_index,sha,save
from certificates import endpoints


def scalar(q,x):
    s=0.
    for a,b in zip(x,q):
        delta=float(a)-float(b);square=delta*delta;s=s+square
    return s


def main():
    p=argparse.ArgumentParser()
    for key in ['data','index','stage','build','out']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cpu',type=int,default=48);p.add_argument('--numa',type=int,default=3)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert a.cpu>=0 and a.numa>=0,'nonnegative CPU/NUMA affinity required'
    m=json.loads((a.stage/'INPUT_IDENTITY.json').read_text());pm=json.loads((a.stage/'PIVOT_MANIFEST.json').read_text())
    sp=json.loads((a.build/'SOURCE.json').read_text())
    assert sha(a.data)==m['data_sha256'] and sha(a.index)==m['tree_sha256']
    assert sha(a.stage/'ancestors.npz')==pm['ancestors_sha256']
    assert sha(a.stage/'pivot_pool64.ids')==pm['pool_sha256']
    assert sha(a.stage/'INTERVAL_SAMPLE_MANIFEST.json')==pm['interval_sample_manifest_sha256']
    assert sha(a.build/'compute_scores.cpp')==sp['generated_sha256']
    assert json.loads((a.stage/'ANCESTOR_TRUTH.json').read_text())['decision']=='CONTINUE_STAGE_B'
    command=['/usr/bin/g++','-O3','-std=c++17','-fno-fast-math','-ffp-contract=off',str(a.build/'compute_scores.cpp'),'-o',str(a.out/'compute_scores')]
    with (a.out/'build.log').open('w') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=60)
    run=['/usr/bin/numactl','--physcpubind='+str(a.cpu),'--membind='+str(a.numa),'/usr/bin/nice','-n','10',str(a.out/'compute_scores'),str(a.data),str(a.stage/'pivot_pool64.ids'),'8',str(a.out/'pool_topk.bin'),str(a.out/'pool_scores.bin')]
    save(a.out/'COMMAND_PRIVATE.json',dict(build=command,scan=run))
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    with (a.out/'scan.log').open('w') as f:
        child=subprocess.run(run,stdout=f,stderr=subprocess.STDOUT,timeout=240,
                             env={**os.environ,'CUDA_VISIBLE_DEVICES':''})
    elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN)
    save(a.out/'SCAN_RECEIPT.json',dict(exit_code=child.returncode,wall_seconds=elapsed,
        CPU_user_seconds=after.ru_utime-before.ru_utime,CPU_system_seconds=after.ru_stime-before.ru_stime,
        child_peak_RSS_KiB=after.ru_maxrss,GPU_used=False,CPU_threads=1,
        CPU_affinity=a.cpu,NUMA_node=a.numa,
        compiler=subprocess.check_output(['/usr/bin/g++','--version'],text=True).splitlines()[0],
        source_sha256=sp['generated_sha256'],binary_sha256=sha(a.out/'compute_scores'),
        data_sha256=m['data_sha256'],tree_sha256=m['tree_sha256'],pool_sha256=pm['pool_sha256'],
        scope='offline 64-pivot preprocessing, not query latency'))
    assert child.returncode==0 and (a.out/'pool_scores.bin').stat().st_size==16+64*1000000*8
    with (a.out/'pool_scores.bin').open('rb') as f:assert struct.unpack('<4i',f.read(16))==(1000000,960,64,8)
    scores=np.memmap(a.out/'pool_scores.bin',mode='r',dtype='<f8',offset=16,shape=(64,1000000))
    z=np.load(a.stage/'ancestors.npz');cross=scores[:,m['queries']]
    assert cross.tobytes()==z['query_pivot_scores'].T.copy().tobytes()
    matrix=scores[:,pm['pool']].copy();assert matrix.tobytes()==matrix.T.copy().tobytes()
    n,d,h,ids,nodes,flags=load_index(a.index);perm=np.array(ids)
    result={'pool_pair_scores':matrix};mins={};maxs={}
    for level,size in [(3,1000),(4,100),(5,10)]:
        minimum=np.empty((10**level,64));maximum=np.empty_like(minimum)
        for j in range(64):
            distances=np.sqrt(scores[j,perm]).reshape(10**level,size)
            minimum[:,j]=distances.min(axis=1);maximum[:,j]=distances.max(axis=1)
        low,high=endpoints(minimum,maximum)
        result[f'low_{level}']=low;result[f'high_{level}']=high
        mins[level]=minimum;maxs[level]=maximum
    samples=json.loads((a.stage/'INTERVAL_SAMPLE_MANIFEST.json').read_text())['samples']
    rows=set(pm['pool'])
    for s in samples:rows.update(s['object_ids'])
    rowids=sorted(rows);vectors={}
    with a.data.open('rb') as f,(a.out/'sample_vectors.bin').open('wb') as out:
        out.write(struct.pack('<2i',len(rowids),960));out.write(np.array(rowids,dtype='<i4').tobytes())
        for row in rowids:
            f.seek(12+row*960*4);b=f.read(960*4);assert len(b)==960*4
            out.write(b);vectors[row]=np.frombuffer(b,dtype='<f4')
    validation=[]
    for s in samples:
        values=[scalar(vectors[s['pivot_id']],vectors[row]) for row in s['object_ids']]
        expected=[float(scores[s['pivot_index'],row]) for row in s['object_ids']]
        assert np.array(values,dtype='<f8').tobytes()==np.array(expected,dtype='<f8').tobytes()
        ri=s['region_id']-11111;pi=s['pivot_index']
        assert min(map(np.sqrt,values))==mins[5][ri,pi] and max(map(np.sqrt,values))==maxs[5][ri,pi]
        validation.append(dict(pivot_id=s['pivot_id'],region_id=s['region_id'],minimum_squared=min(values),maximum_squared=max(values)))
    np.savez_compressed(a.out/'intervals.npz',**result)
    save(a.out/'VALIDATION.json',dict(status='PASS',query_pivot_scores_checked=512,
        query_pivot_score_bytes_checked=4096,
        pool_pair_symmetry_bitwise=True,independent_pivot_leaf_pairs=128,independent_distances=1280,samples=validation))
    save(a.out/'OUTPUT_MANIFEST.json',{name:dict(bytes=(a.out/name).stat().st_size,sha256=sha(a.out/name))
        for name in ['pool_scores.bin','pool_topk.bin','intervals.npz','sample_vectors.bin','SCAN_RECEIPT.json','VALIDATION.json']})
    print('PASS bounded CPU pool scan, interval metadata, cross-query and independent scalar validation',flush=True)

if __name__=='__main__':main()
