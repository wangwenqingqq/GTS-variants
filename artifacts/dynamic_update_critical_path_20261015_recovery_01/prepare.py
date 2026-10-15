"""Bind existing immutable inputs; compile thin clients without changing operators."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from common import HERE, REPO, PARENT, load, save, sha, module
from generate import adapter


def input_prefix(w, n, workload): return w/'inputs'/f'N{n}_W{workload}'


def source_set():
    old = load(PARENT/'evidence/INPUT_IDENTITY.json')['executed_sources']
    for n, h in old.items(): assert sha(REPO/n) == h
    own = {str(p.relative_to(REPO)): sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.cu','.cpp','.json','.md')}
    return {**old, **own}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--parent', type=Path, required=True); p.add_argument('--work', type=Path, required=True)
    p.add_argument('--gpu', required=True); p.add_argument('--numa', type=int, required=True); a = p.parse_args()
    w = a.work.resolve(); old = a.parent.resolve(); c = load(HERE/'CONTRACT.json'); reg = load(old/'REGISTERED.json'); ready = load(old/'READY.json')
    checkpoint=HERE.parent/'dynamic_update_critical_path_20261015'
    assert c['recovery']['human_authorized'] and c['recovery']['R1_GPU_starts']==84 and c['max_GPU_starts']==124
    assert c['recovery']['cumulative_max_GPU_starts']==208 and sha(checkpoint/'PUBLIC_MANIFEST.json')==c['recovery']['checkpoint_manifest_sha256']
    for name,row in load(checkpoint/'PUBLIC_MANIFEST.json')['files'].items():assert sha(checkpoint/name)==row['sha256']
    assert not w.exists() and REPO not in w.parents and c['parent_manifest_sha256'] == sha(PARENT/'PUBLIC_MANIFEST.json')
    for n, r in load(PARENT/'PUBLIC_MANIFEST.json')['files'].items(): assert sha(PARENT/n) == r['sha256']
    assert ready['passed'] and ready['registration_sha256'] == sha(old/'REGISTERED.json')
    assert sha(reg['data']) == c['data_sha256'] and sha(old/'inputs/initial_mean.f32') == c['means_sha256']
    for n, h in reg['sources'].items(): assert sha(REPO/n) == h
    inputs = {reg['data']: c['data_sha256']}
    for n, r in load(old/'CPU_READY.json')['files'].items(): inputs[str(old/n)] = r['sha256']
    for n, h in reg['reference_hashes'].items(): inputs[str(Path(reg['reference'])/n)] = h
    for n, h in inputs.items(): assert sha(n) == h
    for m in ('S1','S2_STALE'): assert sha(old/'build'/m/'service') == ready['binaries'][m]
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    w.mkdir(); (w/'build').mkdir(); (w/'build/adapter.cuh').write_text(adapter())
    shutil.copyfile(old/'build/range_base.cuh', w/'build/range_base.cuh')
    shutil.copyfile(old/'build/S2_STALE/selected.cuh', w/'build/selected.cuh')
    diff = ''.join(difflib.unified_diff((PARENT/'service.cu').read_text().splitlines(True), adapter().splitlines(True), fromfile='parent/service.cu', tofile='generated/adapter.cuh'))
    (w/'build/ADAPTER_DIFF.patch').write_text(diff)
    env = {**os.environ, **reg['environment'], 'CUDA_VISIBLE_DEVICES': a.gpu, 'PYTHONDONTWRITEBYTECODE': '1'}
    commands = {}
    for variant, trace in (('PLAIN',0),('MARKED',1)):
        folder=w/'build'/variant;folder.mkdir()
        cmd=[]
        for value in reg['commands']['S2_STALE']:
            if value.endswith('/artifacts/dynamic_query_aware_exact_gpu_20261015/service.cu'): value=str(HERE/'main.cu')
            elif value == str(old/'build/S2_STALE/service'): value=str(folder/'service')
            elif value in ('-I'+str(old/'build/S2_STALE'), '-I'+str(old/'build')): value='-I'+str(w/'build')
            cmd.append(value)
        cmd += ['-DTRACE='+str(trace)]; assert str(HERE/'main.cu') in cmd and str(folder/'service') in cmd
        commands[variant]=cmd
    replay=['g++','-std=c++17','-O2','-shared','-fPIC',str(HERE/'oracle.cpp'),'-o',str(w/'build/replay.so')]
    save(w/'REGISTERED.json',dict(before_GPU=True,parent=str(old),parent_registration_sha256=sha(old/'REGISTERED.json'),
        parent_ready_sha256=sha(old/'READY.json'),contract_sha256=sha(HERE/'CONTRACT.json'),sources=source_set(),inputs=inputs,
        generated={str(p.relative_to(w)):sha(p) for p in (w/'build').iterdir() if p.is_file()},
        commands=commands,replay_command=replay,environment=reg['environment'],gpu=a.gpu,numa=a.numa,data=reg['data']))
    subprocess.run(replay,check=True)
    binaries={}; libraries={}
    for variant, cmd in commands.items():
        with (w/'build'/variant/'compile.log').open('x') as f: subprocess.run(cmd,env=env,stdout=f,stderr=f,check=True)
        binary=w/'build'/variant/'service';binaries[variant]=sha(binary)
        linked=subprocess.check_output(['ldd',str(binary)],env=env,text=True);assert 'not found' not in linked
        (w/'build'/variant/'ldd.txt').write_text(linked); libs={}
        for line in linked.splitlines():
            words=line.split()
            if '=>' in words and len(words)>2 and words[2].startswith('/'):libs[words[0]]=sha(words[2])
        libraries[variant]=libs
    save(w/'READY.json',dict(passed=True,GPU_starts=0,registration_sha256=sha(w/'REGISTERED.json'),binaries=binaries,
        parent_binaries={m:ready['binaries'][m] for m in ('S1','S2_STALE')},replay_sha256=sha(w/'build/replay.so'),libraries=libraries))
    legacy=REPO/'artifacts/progressive_gpu_gate2_20261013';sys.path.insert(0,str(legacy));helpers=module('immutable_static_helpers',legacy/'static_evidence.py')
    expected=load(PARENT/'evidence/STATIC.json')['records']['S2_STALE']['functions'];records={}
    import hashlib
    for variant in binaries:
        folder=w/'build'/variant
        for flag,name in (('--dump-sass','sass.txt'),('--dump-resource-usage','resources.txt')):
            with (folder/name).open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump',flag,str(folder/'service')],stdout=f,check=True)
        selected={n:body for n,body in helpers.functions((folder/'sass.txt').read_text()).items() if 'progressive_' in n}
        hashes={n:hashlib.sha256(body.encode()).hexdigest() for n,body in selected.items()}
        assert hashes=={n:r['normalized_sass_sha256'] for n,r in expected.items()}
        resources={}
        for m in re.finditer(r' Function (\S+):\n\s*([^\n]+)',(folder/'resources.txt').read_text()):
            if m[1] in hashes:resources[m[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',m[2])}
        assert resources.keys()==hashes.keys() and all(v['STACK']==v['LOCAL']==v['SHARED']==0 for v in resources.values())
        records[variant]=dict(binary_sha256=binaries[variant],selected_function_hashes=hashes,resources=resources,
            sass_sha256=sha(folder/'sass.txt'),resource_sha256=sha(folder/'resources.txt'))
    save(w/'STATIC.json',dict(passed=True,GPU_starts=0,search_SASS_identical=True,new_update_kernels=0,records=records))
    print('PREPARED:inputs/binaries bound,unchanged selected search SASS;0 GPU starts',flush=True)


if __name__=='__main__':main()
