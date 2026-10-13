"""CPU-only bounded numerical-replay cost screen; keeps input placement private."""
import argparse,ctypes,hashlib,json,os,subprocess,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ART=HERE.parent
def read(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()
def run(a):
    w=a.work.resolve();assert not w.exists() and ART not in w.parents
    c=read(HERE/'CONTRACT.json');old=read(a.keeper/'REGISTERED.json')
    g=read(a.gate1/'REGISTERED.json');result=read(a.gate1/'RESULTS.json')
    assert result['complete'] and result['GPU_starts']==0
    assert g['qids']==old['q32']
    assert old['q32']==c['workload']['query_ids']
    assert sha(old['data'])==old['data_sha256']==c['workload']['data_sha256']
    assert g['data_sha256']==old['data_sha256']
    w.mkdir();(w/'build').mkdir()
    frozen={x:sha(HERE/x) for x in ('CONTRACT.json','NUMERICS.md','PRIOR_ART.md','SOURCES.json','DESIGN.md','pre_cost.cpp','pre_cost.py','cost/PRE_GPU_COST.json')}
    save(w/'REGISTERED.json',dict(before_GPU=True,source_hashes=frozen,keeper=str(a.keeper.resolve()),gate1=str(a.gate1.resolve()),parent_registration_sha256=sha(a.keeper/'REGISTERED.json'),gate1_results_sha256=sha(a.gate1/'RESULTS.json'),data_sha256=old['data_sha256'],started_unix=time.time()))
    command=['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-fno-associative-math','-shared','-fPIC',str(HERE/'pre_cost.cpp'),'-o',str(w/'build/pre_cost.so')]
    with (w/'build/compile.log').open('x') as log:subprocess.run(command,stdout=log,stderr=log,check=True)
    f=ctypes.CDLL(str(w/'build/pre_cost.so')).prefix_cost
    f.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_double,ctypes.c_void_p,ctypes.c_void_p];f.restype=ctypes.c_int
    x=np.memmap(old['data'],dtype='<f4',offset=12,mode='r',shape=(1000000,960));assert np.isfinite(x).all() and np.max(np.abs(x))<=16
    cutoff=old['radius']**2;rows=[]
    identities=read(ART/'exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json')['files']
    for q in old['q32']:
        out=np.empty(1000000,'<f8');counts=np.zeros(8,'<u8')
        assert f(x.ctypes.data,x[q].ctypes.data,1000000,cutoff,counts.ctypes.data,out.ctypes.data)==0
        assert hashlib.sha256(out.tobytes()).hexdigest()==old['reference_hashes'][f'{q}.f64']
        raw=a.gate1/'raw'/f'{q}.required.u16';assert sha(raw)==identities[raw.name]['sha256']
        dims=np.fromfile(raw,'<u2');fullhit=out<=cutoff
        expected=[int(np.count_nonzero(dims>k)) if k<960 else int(np.count_nonzero(fullhit)) for k in (128,256,512,960)]
        assert counts[:4].tolist()==expected
        rows.append(dict(qid=q,checkpoint_survivors=expected,replay_upper_counts=counts[4:].tolist(),full_bit_match=True))
        save(w/'PROGRESS.json',dict(rows=rows));print('CPU COST',q,flush=True)
    total=np.sum([r['replay_upper_counts'] for r in rows],axis=0,dtype=np.uint64)
    replay=float(sum(int(z)*k*4 for z,k in zip(total,(128,256,512,960)))/32)
    base=read(HERE/'cost/PRE_GPU_COST.json')
    closure=dict(complete=True,GPU_starts=0,CPU_workers=1,queries=32,rows=rows,replay_upper_counts=total.tolist(),replay_upper_coordinate_bytes_per_query=replay,base_including_padding_flags=base['including_padding_flags'],strict_payload_upper=base['including_padding_flags']+replay,admitted=base['including_padding_flags']+replay<=1.25e9,source_hashes=frozen,binary_sha256=sha(w/'build/pre_cost.so'),registration_sha256=sha(w/'REGISTERED.json'),finished_unix=time.time())
    assert all(sha(HERE/k)==v for k,v in frozen.items());assert sha(old['data'])==old['data_sha256']
    save(w/'RESULTS.json',closure);print('PRE-GPU COST',closure['strict_payload_upper'],'admit',closure['admitted'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('work','keeper','gate1'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
