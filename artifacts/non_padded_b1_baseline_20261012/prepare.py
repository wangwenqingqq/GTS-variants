"""CPU registration and minimal private adapter generation; no CUDA launch."""
import argparse,hashlib,json,os,subprocess,time
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
def sources():
    paths=[HERE/x for x in ('CONTRACT.json','PRIOR_ART.md','SOURCES.json','b1_distance.cuh','fixtures.hpp','prepare.py','campaign.py','test_contract.py')]
    paths += [ART/'query_tile_padding_20261012'/x for x in ('batch.cu',)]
    paths += [ART/'external_closure'/x for x in ('range_service.cu','static_guard.py','common.py')]
    paths += [ART/x for x in ('unified_target_workflow/run.py','unified_search_update/run.py',
        'unified_search_update/protocol.py','par_range_update/reproduce.py','par_range_update/fixtures.py')]
    paths += [ART.parent/'diagnostics/region_exec_20261008/audit_closure.py']
    return {str(p.relative_to(ART.parent)):sha(p) for p in paths}

def prepare(a):
    w=a.work.resolve();assert not w.exists() and ART not in w.parents
    old=read(a.padding/'REGISTERED.json');ready=read(a.padding/'READY.json');build=read(a.padding/'build/BUILD.json')
    roof=read(a.roof/'REGISTERED.json');roofbuild=read(a.roof/'build/BUILD.json')
    assert ready['passed'] and build['registration_sha256']==sha(a.padding/'REGISTERED.json')
    assert sha(old['data'])==old['data_sha256']=='f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'
    assert sha(a.padding/'build/batch')==build['binary_sha256']
    assert sha(a.roof/'build/probe')==roofbuild['binaries']['probe']
    uuid=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
    assert old['gpu']==uuid and old['numa']==a.numa and build['libraries']==roofbuild['libraries']
    w.mkdir();(w/'build').mkdir();qids=old['q32'];assert len(qids)==len(set(qids))==32
    (w/'pool32.txt').write_text('\n'.join(map(str,qids))+'\n')
    radius=float(np.array([0x3f34a3d8],np.uint32).view(np.float32)[0])
    original=(ART/'external_closure/range_service.cu').read_text()
    call='cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));'
    assert original.count(call)==1
    candidate='#include "'+str(HERE/'b1_distance.cuh')+'"\n'+original.replace(call,call.replace('cuvsPairwiseDistance','b1PairwiseDistance'))
    generated=w/'build/candidate_range.cuh';generated.write_text(candidate)
    batch=(ART/'query_tile_padding_20261012/batch.cu').read_text()
    include='"../external_closure/range_service.cu"';entry='int main(int argc,char** argv)try{'
    assert batch.count(include)==1 and batch.count(entry)==1
    batch=batch.replace(include,'"'+str(generated)+'"').replace(entry,'#include "'+str(HERE/'fixtures.hpp')+'"\n'+entry+'\n    if(argc==2&&std::string(argv[1])=="--fixtures")return b1Fixtures();')
    source=w/'build/candidate.cu';source.write_text(batch)
    command=[str(source) if v.endswith('/batch.cu') else str(w/'build/candidate') if v.endswith('/build/batch') else v for v in old['build_command']]
    environment={**old['environment'],'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    refs={name:h for name,h in ready['reference_hashes'].items() if int(Path(name).stem) in qids}
    assert len(refs)==32
    for name,h in refs.items():assert sha(a.padding/'reference'/name)==h
    x=np.memmap(old['data'],dtype='<f4',offset=12,mode='r',shape=(1000000,960))
    read_sums={str(n):float(x[:n].sum(dtype=np.float64)) for n in (4096,1000000)}
    reg=dict(before_GPU=True,source_hashes=sources(),contract_sha256=sha(HERE/'CONTRACT.json'),gpu=uuid,numa=a.numa,
        data=old['data'],data_sha256=old['data_sha256'],q32=qids,radius=radius,environment=environment,
        native_binary=str(a.padding/'build/batch'),native_sha256=sha(a.padding/'build/batch'),
        readonly_binary=str(a.roof/'build/probe'),readonly_sha256=sha(a.roof/'build/probe'),
        reference=str(a.padding/'reference'),reference_hashes=refs,read_sums=read_sums,
        libraries=build['libraries'],parent_ready_sha256=sha(a.padding/'READY.json'),
        command=command,generated_sources={p.name:sha(p) for p in (source,generated)},registered_unix=time.time())
    save(w/'REGISTERED.json',reg)
    import difflib
    (w/'build/ADAPTER_DIFF.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='range_service.cu',tofile='candidate_range.cuh')))
    with (w/'build/compile.log').open('x') as log:subprocess.run(command,env={**os.environ,**environment},stdout=log,stderr=log,check=True)
    ldd=subprocess.check_output(['ldd',str(w/'build/candidate')],env={**os.environ,**environment},text=True)
    assert 'not found' not in ldd;(w/'build/ldd.txt').write_text(ldd)
    libs={}
    for line in ldd.splitlines():
        v=line.split()
        if '=>' in v and len(v)>2 and v[2].startswith('/'):libs[v[0]]={'sha256':sha(v[2])}
    assert libs==reg['libraries'],'library drift'
    save(w/'build/BUILD.json',dict(binary_sha256=sha(w/'build/candidate'),libraries=libs,registration_sha256=sha(w/'REGISTERED.json')))
    save(w/'READY.json',dict(passed=True,registration_sha256=sha(w/'REGISTERED.json'),build_sha256=sha(w/'build/BUILD.json'),source_hashes=sources()))
    print('PREPARED same libraries,32 original references,one candidate; no GPU launch',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','padding','roof'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    prepare(p.parse_args())
