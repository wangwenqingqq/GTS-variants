"""Freeze sources,build commands and identities;no CUDA target execution."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,hashlib,os,re,shutil,subprocess,sys
from pathlib import Path
from common import HERE,REPO,PARENT,BASE,UPDATES,load,save,sha,module
from generate import adapter,client

def input_prefix(w,n,workload):return w/'inputs'/f'N{n}_W{workload}'
def sources():
    old=load(PARENT/'evidence/INPUT_IDENTITY.json')['executed_sources']
    for name,h in old.items():assert sha(REPO/name)==h
    for directory,expected in ((PARENT,'e7bc8bd13000998ab5198ac2a0a0e1b51a45072c022c2b16c292543a21f9bd77'),(BASE,'483ce2f59c8998203ebd2a30d583d19b8c88e3cdbc0c5c99ec903916c25dc5f0')):
        assert sha(directory/'PUBLIC_MANIFEST.json')==expected
        for n,r in load(directory/'PUBLIC_MANIFEST.json')['files'].items():assert sha(directory/n)==r['sha256']
    own={str(p.relative_to(REPO)):sha(p) for folder in (HERE,BASE) for p in folder.iterdir() if p.is_file() and p.suffix in ('.py','.cu','.cpp','.hpp','.cuh','.md','.json')}
    return {**old,**own}

def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);a=p.parse_args()
    w=a.work.resolve();old=a.parent.resolve();reg=load(old/'REGISTERED.json');ready=load(old/'READY.json');c=load(HERE/'CONTRACT.json');assert not w.exists() and ready['passed']
    assert c['max_GPU_starts']==340 and sha(reg['data'])==c['data_sha256']
    bound=sources();inputs={reg['data']:c['data_sha256']}
    for n,r in load(old/'CPU_READY.json')['files'].items():inputs[str(old/n)]=r['sha256']
    for n,h in reg['reference_hashes'].items():inputs[str(Path(reg['reference'])/n)]=h
    for n,h in inputs.items():assert sha(n)==h
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    w.mkdir();(w/'build').mkdir();(w/'build/adapter.cuh').write_text(adapter());(w/'build/main.cu').write_text(client())
    for n in ('plan.hpp','update.cuh','shapes.cuh'):shutil.copy2(HERE/n,w/'build'/n)
    shutil.copy2(old/'build/range_base.cuh',w/'build/range_base.cuh');shutil.copy2(old/'build/S2_STALE/selected.cuh',w/'build/selected.cuh')
    commands={};env={**os.environ,**reg['environment'],'CUDA_VISIBLE_DEVICES':a.gpu,'PYTHONDONTWRITEBYTECODE':'1'}
    for index,u in enumerate(UPDATES):
        for v,trace in (('PLAIN',0),('MARKED',1)):
            label=u+'_'+v;folder=w/'build'/label;folder.mkdir();cmd=[]
            for value in reg['commands']['S2_STALE']:
                if value.endswith('/artifacts/dynamic_query_aware_exact_gpu_20261015/service.cu'):value=str(w/'build/main.cu')
                elif value==str(old/'build/S2_STALE/service'):value=str(folder/'service')
                elif value in ('-I'+str(old/'build/S2_STALE'),'-I'+str(old/'build')):value='-I'+str(w/'build')
                cmd.append(value)
            cmd+=['-DTRACE='+str(trace),'-DUPDATE='+str(index)];commands[label]=cmd
    replay=['g++','-std=c++17','-O2','-shared','-fPIC',str(BASE/'oracle.cpp'),'-o',str(w/'build/replay.so')]
    save(w/'REGISTERED.json',dict(before_GPU=True,parent=str(old),parent_registration_sha256=sha(old/'REGISTERED.json'),parent_ready_sha256=sha(old/'READY.json'),contract_sha256=sha(HERE/'CONTRACT.json'),sources=bound,inputs=inputs,commands=commands,replay_command=replay,generated={str(p.relative_to(w)):sha(p) for p in (w/'build').iterdir() if p.is_file()},environment=reg['environment'],gpu=a.gpu,numa=a.numa,data=reg['data']))
    subprocess.run(replay,check=True);binaries={};libraries={}
    for label,cmd in commands.items():
        folder=w/'build'/label
        with (folder/'compile.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=f,env=env,check=True)
        binary=folder/'service';binaries[label]=sha(binary);linked=subprocess.check_output(['ldd',str(binary)],env=env,text=True);assert 'not found' not in linked
        (folder/'ldd.txt').write_text(linked);libs={}
        for line in linked.splitlines():
            words=line.split()
            if '=>' in words and len(words)>2 and words[2].startswith('/'):libs[words[0]]=sha(words[2])
        libraries[label]=libs
    save(w/'READY.json',dict(passed=True,GPU_starts=0,registration_sha256=sha(w/'REGISTERED.json'),binaries=binaries,parent_binaries={m:ready['binaries'][m] for m in ('S1','S2_STALE')},libraries=libraries,replay_sha256=sha(w/'build/replay.so')))
    legacy=REPO/'artifacts/progressive_gpu_gate2_20261013';sys.path.insert(0,str(legacy));helpers=module('static_immutable_helpers',legacy/'static_evidence.py')
    expected=load(PARENT/'evidence/STATIC.json')['records']['S2_STALE']['functions'];static={}
    for label,h in binaries.items():
        folder=w/'build'/label
        for flag,n in (('--dump-sass','sass.txt'),('--dump-resource-usage','resources.txt')):
            with (folder/n).open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump',flag,str(folder/'service')],stdout=f,check=True)
        allfunctions=helpers.functions((folder/'sass.txt').read_text());selected={n:hashlib.sha256(body.encode()).hexdigest() for n,body in allfunctions.items() if 'progressive_' in n}
        assert selected=={n:r['normalized_sass_sha256'] for n,r in expected.items()}
        resources={}
        for m in re.finditer(r' Function (\S+):\n\s*([^\n]+)',(folder/'resources.txt').read_text()):
            if 'materialize_final' in m[1] or m[1] in selected:resources[m[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',m[2])}
        assert all(r['STACK']==r['LOCAL']==r['SHARED']==0 for r in resources.values())
        static[label]=dict(binary_sha256=h,selected_function_hashes=selected,resources=resources,sass_sha256=sha(folder/'sass.txt'))
    save(w/'STATIC.json',dict(passed=True,GPU_starts=0,query_SASS_unchanged=True,records=static));print('PREPARED six frozen builds;query SASS unchanged;0 GPU starts',flush=True)

if __name__=='__main__':main()
