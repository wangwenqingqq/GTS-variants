"""CPU-only full-population diagnostic. Raw arrays and deployment placement stay private."""
import argparse,ctypes,fcntl,hashlib,json,os,platform,struct,subprocess,time,traceback
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def sources():return {n:sha(HERE/n) for n in ('CONTRACT.json','progressive.cpp','run.py','analyze.py','test_gate1.py','PRIOR_ART.md','SOURCES.json')}
def score_function(library):
    f=ctypes.CDLL(str(library)).progressive_scores
    f.argtypes=[ctypes.c_void_p]*6+[ctypes.c_size_t,ctypes.c_int,ctypes.c_double];f.restype=ctypes.c_int
    def score(x,q,threshold):
        assert x.dtype==q.dtype==np.float32 and x.flags.c_contiguous and q.flags.c_contiguous
        assert x.ndim==2 and q.shape==(x.shape[1],) and len(x)>0
        full=np.empty(len(x),'<f8');dims=np.empty(len(x),'<u2');before=np.empty_like(full);at=np.empty_like(full)
        rc=f(x.ctypes.data,q.ctypes.data,full.ctypes.data,dims.ctypes.data,before.ctypes.data,at.ctypes.data,len(x),x.shape[1],threshold)
        if rc:raise ValueError(('progressive_scores',rc))
        return full,dims,before,at
    return score
def histogram(v,d):return np.bincount(v.astype(np.int64),minlength=d+1).tolist()
def query_record(qid,full,dims,before,at,reference,threshold,d):
    mismatch=int(np.count_nonzero(full.view('<u8')!=reference.view('<u8')))
    assert mismatch==0,('full960 bit disagreement',qid,mismatch)
    assert np.isfinite(full).all() and np.isfinite(before).all() and np.isfinite(at).all()
    assert ((dims>=1)&(dims<=d)).all()
    hit=reference<=threshold;reject=at>threshold
    false=int(np.count_nonzero(reject&hit));assert false==0,('false rejection',qid,false)
    assert np.array_equal(reject,~hit),'crossing versus full decision'
    assert (dims[hit]==d).all() and (before[reject]<=threshold).all()
    assert (at[reject]<=full[reject]).all() and (at[hit]==full[hit]).all()
    margin=full-threshold
    masks={'near':(~hit)&(margin<=threshold*.1),'medium':(~hit)&(margin>threshold*.1)&(margin<=threshold),'far':(~hit)&(margin>threshold)}
    groups={k:dict(count=int(v.sum()),histogram=histogram(dims[v],d),margin_min=float(np.min(margin[v])) if v.any() else None,margin_max=float(np.max(margin[v])) if v.any() else None) for k,v in masks.items()}
    assert sum(v['count'] for v in groups.values())==int((~hit).sum())
    return dict(qid=qid,N=len(full),D=d,hits=int(hit.sum()),nonhits=int((~hit).sum()),
        histogram=histogram(dims,d),nonhit_histogram=histogram(dims[~hit],d),margin_groups=groups,
        full960_bit_mismatches=mismatch,false_rejections=false,
        hard_nonhits_at_D=int(((~hit)&(dims==d)).sum()),
        min_crossing_excess=float(np.min(at[reject]-threshold)) if reject.any() else None,
        min_previous_slack=float(np.min(threshold-before[reject])) if reject.any() else None)

def run(a):
    w=a.work.resolve();assert not w.exists() and HERE.parent not in w.parents
    c=load(HERE/'CONTRACT.json');identity=load(HERE.parent/'non_padded_b1_baseline_20261012/evidence/INPUT_IDENTITY.json')
    parent=load(a.parent/'REGISTERED.json');N=c['workload']['N'];D=c['workload']['D']
    assert parent['q32']==c['workload']['qids']==identity['original_queries']
    assert parent['data_sha256']==c['workload']['data_sha256']==identity['data_sha256']
    assert sha(parent['data'])==parent['data_sha256']
    with Path(parent['data']).open('rb') as f:assert struct.unpack('<iii',f.read(12))==(D,N,2)
    assert Path(parent['data']).stat().st_size==12+N*D*4
    radius=struct.unpack('<f',struct.pack('<I',int(c['workload']['radius_bits'],16)))[0];threshold=radius*radius
    assert radius==parent['radius'] and threshold.hex()==c['numerics']['threshold_hex']
    references={str(q)+'.f64':parent['reference_hashes'][str(q)+'.f64'] for q in parent['q32']}
    assert references=={k:v for k,v in identity['reference_hashes'].items()}
    for name,h in references.items():
        p=Path(parent['reference'])/name;assert p.stat().st_size==N*8 and sha(p)==h
    w.mkdir();(w/'build').mkdir();(w/'raw').mkdir();(w/'scalars').mkdir()
    compiler=c['execution']['compiler'];binary=w/'build/progressive.so'
    command=[compiler,*c['execution']['compiler_flags'],str(HERE/'progressive.cpp'),'-o',str(binary)]
    registered=dict(before_measurement=True,contract_sha256=sha(HERE/'CONTRACT.json'),source_hashes=sources(),
        parent_registration_sha256=sha(a.parent/'REGISTERED.json'),data=parent['data'],data_sha256=parent['data_sha256'],
        reference=parent['reference'],reference_hashes=references,qids=parent['q32'],radius=radius,threshold=threshold,
        compile_command=command,compiler_version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
        machine=platform.uname()._asdict(),python=platform.python_version(),numpy=np.__version__,registered_unix=time.time(),GPU_starts=0,CPU_workers=1)
    save(w/'REGISTERED.json',registered)
    with (w/'build/compile.log').open('x') as f:subprocess.run(command,stdout=f,stderr=f,check=True)
    save(w/'build/BUILD.json',dict(binary_sha256=sha(binary),registration_sha256=sha(w/'REGISTERED.json')))
    score=score_function(binary);x=np.memmap(parent['data'],'<f4',mode='r',offset=12,shape=(N,D))
    with (w/'campaign.lock').open('x') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            env={**os.environ,'GATE1_TEST_LIBRARY':str(binary),'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
            with (w/'QUALIFICATION.log').open('x') as f:subprocess.run(['python3','-m','unittest','-v','test_gate1'],cwd=HERE,env=env,stdout=f,stderr=f,check=True)
            bounded=[]
            for q in parent['q32']:
                ref=np.memmap(Path(parent['reference'])/f'{q}.f64','<f8',mode='r',shape=(N,))
                bounded.append(query_record(q,*score(x[:4096],np.ascontiguousarray(x[q]),threshold),ref[:4096],threshold,D))
            save(w/'QUALIFICATION.json',dict(passed=True,queries=32,objects_per_query=4096,fixtures_passed=True,full960_bit_mismatches=0,false_rejections=0,bounded_records=bounded))
            save(w/'START.json',dict(before_full_population=True,source_hashes=sources(),registration_sha256=sha(w/'REGISTERED.json'),qualified_sha256=sha(w/'QUALIFICATION.json'),CPU_workers=1,GPU_starts=0,started_unix=time.time()))
            records=[];raw_hashes={}
            for i,q in enumerate(parent['q32']):
                assert sources()==registered['source_hashes'] and sha(binary)==load(w/'build/BUILD.json')['binary_sha256']
                refpath=Path(parent['reference'])/f'{q}.f64';assert sha(refpath)==references[refpath.name]
                ref=np.memmap(refpath,'<f8',mode='r',shape=(N,))
                full,dims,before,at=score(x,np.ascontiguousarray(x[q]),threshold)
                rec=query_record(q,full,dims,before,at,ref,threshold,D);rec['query_index']=i
                for suffix,v in (('.f64',full),('.required.u16',dims)):
                    p=w/'raw'/f'{q}{suffix}';v.tofile(p);raw_hashes[p.name]=sha(p)
                assert raw_hashes[f'{q}.f64']==references[f'{q}.f64']
                records.append(rec);save(w/'scalars'/f'q{i:02}.json',rec)
                save(w/'PROGRESS.json',dict(complete=False,queries_completed=len(records),last_qid=q,GPU_starts=0))
                print('PASSED',i+1,'/',32,'qid',q,'mean_dims',float(dims.mean()),'hits',rec['hits'],flush=True)
            assert sha(parent['data'])==registered['data_sha256'] and sources()==registered['source_hashes']
            save(w/'RAW_MANIFEST.json',dict(files=raw_hashes))
            save(w/'RESULTS.json',dict(complete=True,queries=32,pairs=N*32,GPU_starts=0,CPU_workers=1,full960_bit_mismatches=0,false_rejections=0,registration_sha256=sha(w/'REGISTERED.json'),start_sha256=sha(w/'START.json'),raw_manifest_sha256=sha(w/'RAW_MANIFEST.json'),finished_unix=time.time()))
        except Exception:
            save(w/'FAILURE.json',dict(complete=False,error=traceback.format_exc(),stop='No automatic retry or source replacement',GPU_starts=0));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--work',type=Path,required=True);run(p.parse_args())
