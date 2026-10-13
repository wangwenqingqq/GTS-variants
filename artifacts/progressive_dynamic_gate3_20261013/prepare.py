"""CPU-only source/input registration and strict ordered oracle preparation."""
import argparse,ctypes,difflib,os,shutil,subprocess,time
from pathlib import Path
import numpy as np
from trace import HERE,ART,read,save,sha,load,replay,freeze_b
GUARDS=('artifacts/unified_target_workflow/run.py','artifacts/unified_search_update/run.py','artifacts/unified_search_update/protocol.py','artifacts/par_range_update/reproduce.py','artifacts/par_range_update/fixtures.py','diagnostics/region_exec_20261008/audit_closure.py')
def sources():
    own=('CONTRACT.json','PRIOR_ART.md','DESIGN.md','trace.py','oracle.cpp','analyze.py','prepare.py','service.cu','campaign.py','quality.py','static.py','test_gate3.py')
    old=('external_closure/pe_e.cu','external_closure/pe_common.hpp','external_closure/range_service.cu','external_closure/static_guard.py','external_closure/common.py','non_padded_b1_baseline_20261012/b1_distance.cuh','progressive_gpu_gate2_20261013/progressive.cuh','progressive_gpu_gate2_20261013/static_evidence.py','progressive_gpu_gate2_20261013/pre_cost.py','exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json')
    files=[HERE/p for p in own]+[ART/p for p in old]+[ART.parent/p for p in GUARDS]
    return {str(p.relative_to(ART.parent)):sha(p) for p in files}
def library_hashes(binary,env):
    s=subprocess.check_output(['ldd',str(binary)],env=env,text=True);assert 'not found' not in s
    libs={}
    for line in s.splitlines():
        v=line.split()
        if '=>' in v and len(v)>2 and v[2].startswith('/'):libs[v[0]]={'sha256':sha(v[2])}
    return libs,s
def fixture(w):
    p=w/'fixtures';p.mkdir();n=65;d=960;x=np.zeros((n,d),dtype='<f4');x[2,0]=1;x[3,0]=np.nextafter(np.float32(1),np.float32(0));x[4,0]=np.nextafter(np.float32(1),np.float32(2))
    for r,j in zip(range(5,9),(127,255,511,959)):x[r,j]=2
    rng=np.random.default_rng(2026101304);x[9:]=rng.integers(-2,3,(n-9,d)).astype(np.float32)/64
    data=p/'data.f32bin';data.write_bytes(np.array([d,n,2],dtype='<i4').tobytes()+x.tobytes());rows=[];src=[];physical=list(range(n));position=list(range(n));next_id=n
    for i in range(40):
        q=0 if i%2==0 else 9+i%40
        rows.append((2,-1));src.append((2,-1,q));oid=next_id;next_id+=1;rows.append((0,oid));src.append((0,oid,0))
        # Keep one duplicate across several operations, remove the other independently.
        physical.append(oid);victim=(i//2 if i%2==0 else oid);assert victim in physical
        rows.append((1,victim));src.append((1,victim,-1));r=physical.index(victim);physical[r]=physical[-1];physical.pop()
        rows.append((3,-1));src.append((3,-1,q))
    def write(name,rr,ss):
        stem=p/name;Path(str(stem)+'.logical').write_text(f'{len(rr)} {n} {d}\n'+''.join(f'{f} {o}\n' for f,o in rr));v=np.zeros((len(rr),d),dtype='<f4')
        for i,(_,_,q) in enumerate(ss):
            if q>=0:v[i]=x[q]
        v.tofile(str(stem)+'.vectors.f32');save(str(stem)+'.source.json',ss)
    write('trace',rows,src)
    # Same19-operation/eight-query warmup schedule, with fixed immutable source vectors.
    flags=[2,3,0,2,3,1,2,3]+[0]*9+[2,3];rr=[];ss=[];next_id=n
    for i,f in enumerate(flags):
        oid=next_id if f==0 else 0 if f==1 else -1
        if f==0:next_id+=1
        rr.append((f,oid));ss.append((f,oid,-1 if f==1 else 0))
    write('trace.warmup',rr,ss)
    return data,p/'trace'
def references(w,data,trace,cache,radius,label):
    (events,n,d),rows,v=load(trace);src=read(str(trace)+'.source.json');assert len(src)==events
    physical,position,states,snaps=replay(n,rows);save(Path(str(trace)+'.cpu_state.json'),dict(states=states,snapshots=list(snaps),physical_sha256=sha(str(trace)+'.physical.i32') if Path(str(trace)+'.physical.i32').exists() else None))
    next_id=n;alive=np.zeros(n+sum(f==0 for f,_ in rows),bool);alive[:n]=True;origin=np.arange(len(alive));ids=[];scores=[];queries=[];at=0;x=np.memmap(data,dtype='<f4',offset=12,mode='r',shape=(n,d))
    for step,((flag,oid),(_,token,q)) in enumerate(zip(rows,src)):
        assert oid==token
        assert 0<=q<n if flag!=1 else q==-1
        if flag==0:
            assert oid==next_id and v[step].tobytes()==x[q].tobytes();next_id+=1;alive[oid]=True;origin[oid]=q
        elif flag==1:assert alive[oid];alive[oid]=False
        else:
            assert v[step].tobytes()==x[q].tobytes();base=np.memmap(cache/f'{q}.f64',dtype='<f8',mode='r',shape=(n,));live=np.flatnonzero(alive);sq=base[origin[live]]
            if flag==2:hit=sq<=radius**2;wanted=live[hit];chosen=sq[hit];boundary=None
            else:
                k=min(8,len(live));boundary=float(np.partition(sq,k-1)[k-1]) if k else None
                low=sq<boundary if k else np.zeros(len(live),bool);wanted=live[low];chosen=sq[low]
            queries.append(dict(step=step,flag=flag,source=q,offset=at,count=len(wanted),live=len(live),boundary=boundary));ids.extend(wanted.tolist());scores.extend(chosen.tolist());at+=len(wanted)
    out=w/'references'/label;np.array(ids,dtype='<i4').tofile(str(out)+'.ids.i32');np.array(scores,dtype='<f8').tofile(str(out)+'.scores.f64');save(str(out)+'.queries.json',queries)
def prepare(a):
    w=a.work.resolve();assert not w.exists() and ART not in w.parents;parent=read(a.parent/'REGISTERED.json');old=read(Path(parent['keeper_directory'])/'dynamic/REGISTERED.json');assert sha(old['data'])==old['data_sha256']==parent['data_sha256']
    for p,h in old['input_hashes'].items():assert sha(p)==h
    for p,h in parent['source_hashes'].items():assert sha(ART.parent/p)==h,p
    state=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip();assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    os.environ['OMP_NUM_THREADS']='8'
    w.mkdir();(w/'build').mkdir();(w/'references').mkdir();(w/'inputs').mkdir();(w/'cache').mkdir();env={**os.environ,**parent['environment'],'OMP_NUM_THREADS':'8','PYTHONDONTWRITEBYTECODE':'1'}
    subprocess.run([os.sys.executable,'-c','import static_guard; assert callable(static_guard.snapshot)'],cwd=ART/'external_closure',env={**env,'CUDA_VISIBLE_DEVICES':''},check=True)
    save(w/'DEPENDENCY_PREFLIGHT.json',dict(passed=True,no_CUDA_initialization=True,transitive={p:sha(ART.parent/p) for p in GUARDS}))
    for tail in ('.logical','.vectors.f32','.source.json','.warmup.logical','.warmup.vectors.f32','.warmup.source.json'):
        shutil.copyfile(old['trace']+tail,str(w/'inputs/A')+tail)
    data=Path(old['data']);b=freeze_b(data,w/'inputs/A',w/'inputs/B')
    (_,initial_n,_),a_rows,_=load(w/'inputs/A');_,_,a_states,a_snaps=replay(initial_n,a_rows)
    assert len(a_rows)==336 and [sum(f==i for f,_ in a_rows) for i in range(4)]==[40,40,128,128]
    assert len(a_snaps)==4 and all(any(sum(f==0 for f,_ in a_rows[:s+1])==c and sum(f==1 for f,_ in a_rows[:s+1])==c for s in a_snaps if 0<=s<len(a_rows)) for c in (20,40))
    for tail in ('.logical','.vectors.f32','.source.json'):shutil.copyfile(str(w/'inputs/A.warmup')+tail,str(w/'inputs/B.warmup')+tail)
    fxdata,fx=fixture(w);(w/'pool32.txt').write_text('\n'.join(map(str,parent['q32']))+'\n')
    native=(ART/'external_closure/pe_e.cu').read_text();shared=native[:native.index('struct Answer {')]
    raw=(ART/'external_closure/range_service.cu').read_text();call='cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));';assert raw.count(call)==1
    h=(ART/'non_padded_b1_baseline_20261012/b1_distance.cuh').read_text();assert h.count('shape[0]>1000000')==1;h=h.replace('shape[0]>1000000','shape[0]>1000400');(w/'build/b1.cuh').write_text(h)
    range_source='#include "'+str(w/'build/b1.cuh')+'"\n'+raw.replace(call,call.replace('cuvsPairwiseDistance','b1PairwiseDistance'));(w/'build/range.cuh').write_text(range_source)
    shared=shared.replace('"range_service.cu"','"'+str(w/'build/range.cuh')+'"').replace('"pe_common.hpp"','"'+str(ART/'external_closure/pe_common.hpp')+'"');(w/'build/shared_native.cuh').write_text(shared)
    command=[str(HERE/'service.cu') if v.endswith('/candidate.cu') else str(w/'build/D0') if v.endswith('/build/candidate') else v for v in old['command']]
    command+=['-I'+str(w/'build'),'--ftz=false','--fmad=false','-Xcompiler=-ffp-contract=off,-fno-fast-math']
    commands={m:[str(w/'build'/m) if v==str(w/'build/D0') else v for v in command]+['-DG3_PROGRESSIVE='+str(i)] for i,m in enumerate(('D0','D1'))}
    dims={str(Path(parent['gate1_directory'])/'raw'/f'{q}.required.u16'):sha(Path(parent['gate1_directory'])/'raw'/f'{q}.required.u16') for q in parent['q32']}
    historical=read(ART/'exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json')['files']
    assert all(h==historical[Path(p).name]['sha256'] for p,h in dims.items())
    reg=dict(before_GPU=True,base_commit='6baaa376a4b7afe3192ab3ba1b4269993856d479',contract_sha256=sha(HERE/'CONTRACT.json'),sources=sources(),gpu=state,numa=a.numa,environment=parent['environment'],data=str(data),data_sha256=old['data_sha256'],radius=old['radius'],parent_registration_sha256=sha(a.parent/'REGISTERED.json'),legacy_registration_sha256=sha(Path(parent['keeper_directory'])/'dynamic/REGISTERED.json'),legacy_binary=old['native_binary'],legacy_binary_sha256=old['native_sha256'],old_strengthened_binary=str(Path(parent['keeper_directory'])/'dynamic/build/candidate'),old_strengthened_sha256=sha(Path(parent['keeper_directory'])/'dynamic/build/candidate'),Gate2_binary=str(a.parent/'build/candidate'),Gate2_BINARY_sha256=sha(a.parent/'build/candidate'),trace_A_sha256=sha(str(w/'inputs/A')+'.logical'),trace_B=b,commands=commands,stage_reference_hashes=dims,generated_sources={p.name:sha(p) for p in (w/'build').glob('*.cuh')},dependency_preflight_sha256=sha(w/'DEPENDENCY_PREFLIGHT.json'),registered_unix=time.time())
    reg['static_libraries']={p:sha(p) for p in old['command'] if p.endswith('.a')};assert reg['static_libraries'],'Faiss static library binding required'
    save(w/'REGISTERED.json',reg);binaries={};libs=None
    for mode,cmd in commands.items():
        with (w/'build'/(mode+'.compile.log')).open('x') as f:subprocess.run(cmd,env=env,stdout=f,stderr=f,check=True)
        linked,text=library_hashes(w/'build'/mode,env);(w/'build'/(mode+'.ldd.txt')).write_text(text)
        if libs is None:libs=linked
        else:assert libs==linked
        for name,h in parent['libraries'].items():assert libs[name]==h
        binaries[mode]=sha(w/'build'/mode)
    oracle_cmd=['g++','-std=c++17','-O3','-shared','-fPIC','-fopenmp','-ffp-contract=off','-fno-fast-math',str(HERE/'oracle.cpp'),'-o',str(w/'build/oracle.so')];subprocess.run(oracle_cmd,env=env,check=True)
    lib=ctypes.CDLL(str(w/'build/oracle.so'));fn=lib.exact_scores;fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p];fn.restype=None
    for cache,dat,traces in [(w/'cache',data,[w/'inputs/A',w/'inputs/A.warmup',w/'inputs/B']), (w/'fixtures/cache',fxdata,[fx,Path(str(fx)+'.warmup')])]:
        cache.mkdir(exist_ok=True);header=np.fromfile(dat,dtype='<i4',count=3);d,n,fmt=header;assert fmt==2 and dat.stat().st_size==12+int(n)*int(d)*4;x=np.memmap(dat,dtype='<f4',offset=12,mode='r',shape=(n,d));queries=sorted({q for t in traces for f,o,q in read(str(t)+'.source.json') if f>=2}|(set(parent['q32']) if dat==data else set()))
        for q in queries:
            out=np.empty(n,dtype='<f8');qv=np.array(x[q]);fn(x.ctypes.data,qv.ctypes.data,int(n),int(d),out.ctypes.data);assert np.isfinite(out).all();out.tofile(cache/f'{q}.f64')
            # Separate Python/NumPy coordinate-ordered check, not another SIMD reduction.
            sample=np.array(x[np.linspace(0,n-1,min(n,7),dtype=int)],dtype=np.float64);wanted=np.zeros(len(sample))
            for j in range(d):delta=sample[:,j]-float(qv[j]);wanted=wanted+delta*delta
            assert np.array_equal(out[np.linspace(0,n-1,min(n,7),dtype=int)],wanted),'ordered CPU oracle cross-check'
            if dat==data and q in parent['q32']:assert sha(cache/f'{q}.f64')==parent['reference_hashes'][f'{q}.f64'],'ordered oracle drift'
            print('CPU_ORACLE',dat.name,q,flush=True)
    for label,dat,t,c in [('A',data,w/'inputs/A',w/'cache'),('A.warmup',data,w/'inputs/A.warmup',w/'cache'),('B',data,w/'inputs/B',w/'cache'),('B.warmup',data,w/'inputs/B.warmup',w/'cache'),('fixture',fxdata,fx,w/'fixtures/cache'),('fixture.warmup',fxdata,Path(str(fx)+'.warmup'),w/'fixtures/cache')]:references(w,dat,t,c,1.0 if label.startswith('fixture') else reg['radius'],label)
    assert all(sha(p)==h for p,h in reg['static_libraries'].items())
    ready=dict(passed=True,no_GPU_starts=True,registration_sha256=sha(w/'REGISTERED.json'),sources=sources(),binaries=binaries,libraries=libs,oracle_command=oracle_cmd,oracle_sha256=sha(w/'build/oracle.so'),inputs={str(p.relative_to(w)):sha(p) for folder in ('inputs','fixtures','references','cache') for p in (w/folder).rglob('*') if p.is_file()},probe_pool_sha256=sha(w/'pool32.txt'),same_native_storage_updates_and_knn=True)
    assert ready['sources']==reg['sources'];save(w/'READY.json',ready);print('PREPARED both systems,both traces,complete ordered oracles;0 GPU starts',flush=True)
def recover(a):
    """Human-approved CPU-only re-registration; never rewrite an old failure."""
    old=a.recovery_from.resolve();w=a.work.resolve();approval=read(a.approval)
    assert approval['human_approved'] and approval['max_total_starts']==30 and approval['scope']=='fixture_empty_probe_pool_only'
    assert not w.exists() and ART not in w.parents
    previous=read(old/'REGISTERED.json');ready=read(old/'READY.json');result=read(old/'qualification/RESULTS.json');ledger=(old/'STARTS.jsonl').read_text().splitlines()
    assert len(ledger)==1 and not result['complete'] and result['rows'][0]['label']=='D0_fixtures' and result['rows'][0]['status']=='failed'
    receipt=read(old/'qualification/guards/D0_fixtures/receipt.json');assert receipt['exit_code']==1 and receipt['stop_reason'] is None
    assert (old/'qualification/guards/D0_fixtures/stderr.log').read_text().strip()=='FAIL probe query ID'
    assert not list((old/'qualification/outputs').iterdir()),'failure must be before any CUDA service output'
    current=sources();changed={p for p in current if current[p]!=previous['sources'][p]}
    assert changed=={str((HERE/p).relative_to(ART.parent)) for p in ('prepare.py','campaign.py','test_gate3.py')},'only recovery/argument preflight source changes'
    assert a.gpu==previous['gpu'] and a.numa==previous['numa'] and ready['registration_sha256']==sha(old/'REGISTERED.json')
    w.mkdir()
    for folder in ('build','inputs','fixtures','references','cache'):shutil.copytree(old/folder,w/folder)
    for file in ('pool32.txt','DEPENDENCY_PREFLIGHT.json'):shutil.copyfile(old/file,w/file)
    for p,h in ready['inputs'].items():assert sha(w/p)==h
    for m,h in ready['binaries'].items():assert sha(w/'build'/m)==h
    previous['sources']=current;previous['recovery']=dict(human_approved=True,scope=approval['scope'],max_total_starts=30,prior_starts=1,prior_work=str(old),prior_registration_sha256=sha(old/'REGISTERED.json'),prior_ledger_sha256=sha(old/'STARTS.jsonl'),prior_failure_sha256=sha(old/'qualification/RESULTS.json'),approval_sha256=sha(a.approval),compile_sources=read(old/'REGISTERED.json')['sources'],changed_non_GPU_sources=sorted(changed),unchanged_binaries=ready['binaries'])
    previous['registered_unix']=time.time();save(w/'REGISTERED.json',previous)
    ready['sources']=current;ready['registration_sha256']=sha(w/'REGISTERED.json');ready['recovery_CPU_only']=True;save(w/'READY.json',ready)
    static=read(w/'build/STATIC.json');static['registration_sha256']=sha(w/'REGISTERED.json');save(w/'build/STATIC.json',static)
    from campaign import command
    cmd=command(dict(mode='D0',fixture=True),w,previous,w/'qualification/outputs/D0_fixtures');assert cmd[5]=='/dev/null' and cmd[6]=='0'
    save(w/'RECOVERY_PREFLIGHT.json',dict(passed=True,CPU_only=True,fixture_probe_pool=cmd[5],data_traces_reference_hashes_unchanged=True,binaries_unchanged=True,prior_failure_preserved=True,no_new_GPU_starts=True))
    print('RECOVERY PREPARED: argument fix only;unchanged binaries/inputs/oracles;prior failure retained',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--parent',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);p.add_argument('--recovery-from',type=Path);p.add_argument('--approval',type=Path);a=p.parse_args()
    if a.recovery_from:recover(a)
    else:assert a.parent;prepare(a)
