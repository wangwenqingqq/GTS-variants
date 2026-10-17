"""Build and freeze fresh identities in the new persistent root;no target launch."""
import argparse,os,subprocess,shutil,re,sys
from pathlib import Path
from protocol import HERE,REPO,VARIANTS,FAMILIES,STAGES,SEED,sha,load,save,module,jobs,ends
from generate import adapter,client
import truth
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--restore',type=Path,required=True);p.add_argument('--gpu',default='0');p.add_argument('--numa',type=int,default=0);a=p.parse_args();w=a.work.resolve();r=a.restore.resolve()
    assert w.is_dir() and not (w/'build').exists() and load(r/'receipts/FINAL_RESTORATION_PASS.json')['passed']
    parent=r/'rebuild/derived_parent';original=r/'parent_original/work_r1';old=load(r/'raw_original/work_final/REGISTERED.json')
    data=Path(old['data']);assert sha(data)=='f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    environment={**old['environment'],'PDX_MEANS':str(parent/'inputs/initial_mean.f32'),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    inputs={str(data):sha(data)};(w/'inputs').mkdir();prefixes={}
    for n in (4096,1000000):
        for family in FAMILIES:
            trace=w/'cpu/traces'/f'N{n}_{family}_{SEED}';proof=load(trace/'RESULT.json');assert proof['generic_tail_plan_mismatches']==0
            stem=w/'inputs'/f'N{n}_{family}';prefixes[f'N{n}_{family}']=str(stem)
            Path(str(stem)+'.victims.i32').symlink_to(trace/'victims.i32');Path(str(stem)+'.incoming.f32').symlink_to(parent/'inputs'/f'N{n}_W2.incoming.f32')
            Path(str(stem)+'.ends.txt').write_text(' '.join(map(str,ends(n)))+'\n')
    stem=w/'inputs/micro';prefixes['micro']=str(stem)
    with (parent/'inputs/N1000000_W2.incoming.f32').open('rb') as f:incoming=f.read(8192*3840)
    assert len(incoming)==8192*3840
    with Path(str(stem)+'.incoming.f32').open('xb') as f:f.write(incoming)
    with (w/'cpu/traces'/f'N1000000_W2_ORIGINAL_{SEED}'/'victims.i32').open('rb') as f:victims=f.read(8192*4)
    with Path(str(stem)+'.victims.i32').open('xb') as f:f.write(victims)
    Path(str(stem)+'.ends.txt').write_text(' '.join(map(str,ends(1000000,True)))+'\n')
    (w/'truth').mkdir();truth_paths={}
    for n in (4096,1000000):
        for family in FAMILIES:
            key=f'N{n}_{family}';out=w/'truth'/key;truth.build(Path(prefixes[key]),n,512,False,parent,r/'rebuild/bootstrap/reference',out);truth_paths[key]=str(out)
    for b in (1,32,512):
        key=f'micro_B{b}';out=w/'truth'/key;truth.build(stem,1000000,b,True,parent,r/'rebuild/bootstrap/reference',out);truth_paths[key]=str(out)
    for folder in (w/'inputs',parent/'cache/N4096_W2',parent/'cache/N1000000_W2',r/'rebuild/bootstrap/reference',*[Path(p) for p in truth_paths.values()]):
        for f in folder.iterdir():
            if f.is_file():inputs[str(f)]=sha(f)
    for f in (parent/'inputs/initial_mean.f32',parent/'inputs/full_qids.txt',parent/'inputs/bounded_qids.txt'):inputs[str(f)]=sha(f)
    build=w/'build';build.mkdir();(build/'adapter.cuh').write_text(adapter());(build/'main.cu').write_text(client())
    for f in ('candidate.cuh','generic.hpp','bitcheck.cuh'):shutil.copy2(HERE/f,build/f)
    frozen=REPO/'artifacts/ownership_safe_gpu_update_20261015'
    for f in ('plan.hpp','validation.cuh'):shutil.copy2(frozen/f,build/f)
    shutil.copy2(original/'build/range_base.cuh',build/'range_base.cuh');shutil.copy2(original/'build/S2_STALE/selected.cuh',build/'selected.cuh')
    commands={};env={**os.environ,**environment,'CUDA_VISIBLE_DEVICES':a.gpu,'PYTHONDONTWRITEBYTECODE':'1'}
    # Reuse the original compilation contract,changing only paths and TRACE.
    for trace in (0,1):
        folder=build/str(trace);folder.mkdir();cmd=[]
        for value in old['commands']['NATIVE_PLAIN']:
            if value.endswith('/build/main.cu'):value=str(build/'main.cu')
            elif value.endswith('/build/NATIVE_PLAIN/service'):value=str(folder/'service')
            elif value.startswith('-I') and value[2:].endswith('/build'):value='-I'+str(build)
            elif value.startswith('-DTRACE='):value='-DTRACE='+str(trace)
            elif value.startswith('-DUPDATE='):continue
            cmd.append(value)
        cmd+=['-I/usr/local/cuda-13.1/targets/x86_64-linux/include/cccl'];commands[str(trace)]=cmd
    bound={str(f.relative_to(REPO)):sha(f) for f in HERE.iterdir() if f.is_file()}
    # Freeze all parent source files as well,not an unverified scratch subset.
    for folder in ('dynamic_query_aware_exact_gpu_20261015','dynamic_update_critical_path_20261015_recovery_01','ownership_safe_gpu_update_20261015','progressive_gpu_gate2_20261013','external_closure'):
        for f in (REPO/'artifacts'/folder).iterdir():
            if f.is_file() and f.suffix in ('.py','.cu','.cuh','.hpp','.json','.cpp'):bound[str(f.relative_to(REPO))]=sha(f)
    schedule={s:jobs(s) for s in STAGES};assert sum(map(len,schedule.values()))==368
    registration=dict(state='REGISTERED_BEFORE_GPU',parent_commit='4b413f26cb058d8157c02641eb8bfa2c80f9863c',contract_sha256=sha(HERE/'GPU_CONTRACT.json'),sources=bound,inputs=inputs,prefixes=prefixes,truth_paths=truth_paths,commands=commands,environment=environment,gpu=a.gpu,numa=a.numa,data=str(data),reference=str(r/'rebuild/bootstrap/reference'),derived_parent=str(parent),schedule=schedule,max_GPU_starts=368,generated={str(f.relative_to(w)):sha(f) for f in build.iterdir() if f.is_file()})
    save(w/'REGISTERED.json',registration)
    subprocess.run(['g++','-std=c++17','-O2','-fPIC','-shared',str(HERE/'oracle.cpp'),'-o',str(build/'oracle.so')],check=True)
    binaries={};static={}
    sys.path.insert(0,str(REPO/'artifacts/progressive_gpu_gate2_20261013'))
    helpers=module('frozen_static_helpers',REPO/'artifacts/progressive_gpu_gate2_20261013/static_evidence.py')
    expected={n:r['normalized_sass_sha256'] for n,r in load(REPO/'artifacts/dynamic_query_aware_exact_gpu_20261015/evidence/STATIC.json')['records']['S2_STALE']['functions'].items()}
    for trace,cmd in commands.items():
        folder=build/trace
        with (folder/'compile.log').open('x') as f:subprocess.run(cmd,env=env,stdout=f,stderr=f,check=True)
        binary=folder/'service';binaries[trace]=sha(binary);linked=subprocess.check_output(['ldd',str(binary)],env=env,text=True);assert 'not found' not in linked;(folder/'ldd.txt').write_text(linked)
        for flag,name in (('--dump-sass','sass.txt'),('--dump-resource-usage','resources.txt')):
            with (folder/name).open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump',flag,str(binary)],stdout=f,check=True)
        functions=helpers.functions((folder/'sass.txt').read_text());query={n:__import__('hashlib').sha256(body.encode()).hexdigest() for n,body in functions.items() if 'progressive_' in n};assert query==expected
        resources={}
        for m in re.finditer(r' Function (\S+):\n\s*([^\n]+)',(folder/'resources.txt').read_text()):
            resources[m[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',m[2])}
        static[trace]=dict(binary_sha256=binaries[trace],query_functions=query,resources=resources,sass_sha256=sha(folder/'sass.txt'))
    save(w/'STATIC.json',dict(passed=True,query_SASS_unchanged=True,records=static,GPU_starts=0))
    save(w/'READY.json',dict(passed=True,registration_sha256=sha(w/'REGISTERED.json'),binaries=binaries,oracle_sha256=sha(build/'oracle.so'),GPU_starts=0))
    from preflight import capture
    capture(w,r,registration,load(w/'READY.json'))
    print('PREPARED:2 builds,6 runtime variants,368 maximum target starts,0 GPU starts',flush=True)
if __name__=='__main__':main()
