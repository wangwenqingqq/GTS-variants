#!/usr/bin/env python3
"""Serialize bounded extraction/check/timing runs on the explicitly admitted GPU0."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import time
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('original_run',HERE.parent/'original_tree_profile/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
CASES=[(2000,32,300)]+[(65536,q,r) for q in [32,128] for r in [300,500]]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True);ap.add_argument('--stage',choices=['extract','check','sanitizer','timing','profile'],required=True);a=ap.parse_args();root=a.root.resolve()
    (root/'runs').mkdir(exist_ok=True)
    assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0','only physical GPU0 admitted'
    locks=[]
    for path in [Path('/tmp/gtspp_gpu0.lock'),root/'run.lock']:
        f=path.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    def invoke(label,cmd,binary,env_extra=None):
        out=root/'runs'/label;out.mkdir(exist_ok=False)
        pre=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(pre,indent=2)+'\n')
        assert not pre['apps'].strip(),'GPU0 occupied; stop'
        env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu,'GTS_DIAG_BLOCKING':'1',**(env_extra or {})}
        start=time.time();cpu=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
            try:rc=subprocess.run(list(map(str,cmd)),cwd=out,env=env,stdout=stdout,stderr=stderr,timeout=300).returncode
            except subprocess.TimeoutExpired:rc=124
        end=resource.getrusage(resource.RUSAGE_CHILDREN);post=base.snapshot(a.gpu)
        receipt={'label':label,'command':list(map(str,cmd)),'environment_overrides':env_extra or {},'gpu_uuid':a.gpu,'binary_sha256':base.sha(binary),'exit_code':rc,'start':start,'wall_s':time.time()-start,'user_s':end.ru_utime-cpu.ru_utime,'system_s':end.ru_stime-cpu.ru_stime,'post_clear':not post['apps'].strip()}
        (out/'after.json').write_text(json.dumps(post,indent=2)+'\n');(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(label,'rc',rc,'wall_s',round(receipt['wall_s'],3),flush=True)
        assert rc==0 and receipt['post_clear'],f'failed run {label}; preserve and stop'
        if a.stage!='extract':assert 'pass' in (out/'stdout.log').read_text().splitlines(),f'no success marker {label}'
        else:assert not any('error:' in l.lower() for l in (out/'stderr.log').read_text().splitlines()),'native runtime error'
    for n,q,r in CASES:
        name=f'n{n}_q{q}_r{r}';fixture=root/'fixtures'/f'n{n}';export=root/'runs'/f'extract_{name}'
        manifest=json.loads((fixture/'manifest.json').read_text())
        for fname,h in manifest['file_sha256'].items():assert base.sha(fixture/fname)==h
        if a.stage=='extract':
            binary=root/'bin'/('export3' if n==2000 else 'export5')
            invoke(f'extract_{name}',[binary,fixture/'data.txt',fixture/f'q{q}.txt',1,r,export/'cost.txt'],binary,{'GTS_TC_EXPORT':str(export/'pairs.txt'),'GTS_TC_INDEX':str(export/'index.txt')})
            continue
        binary=root/'bin/probe'
        cmd=[binary,fixture/'data.txt',fixture/f'q{q}.txt',export/'index.txt',export/'pairs.txt',export/'cost.txt',r]
        if a.stage=='check':invoke('check_'+name,cmd+['AB','check'],binary)
        elif a.stage=='sanitizer':
            if (n,q,r) not in [(2000,32,300),(65536,128,500)]:continue
            for tool in (['memcheck','synccheck','initcheck','racecheck'] if n==2000 else ['memcheck','synccheck']):
                invoke(tool+'_'+name,['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd+['AB','check'],binary)
        elif a.stage=='profile' and (n,q,r)==(65536,128,500):
            out=root/'runs'/('profile_'+name)
            invoke('profile_'+name,['nsys','profile','--trace=cuda','--sample=none','--cpuctxsw=none','--force-overwrite=false','--output='+str(out/'trace')]+cmd+['AB','check'],binary)
        elif a.stage=='timing' and n==65536:
            assert (root/'runs'/('check_'+name)/'receipt.json').is_file()
            for case in ['n2000_q32_r300','n65536_q128_r500']:
                for tool in (['memcheck','synccheck','initcheck','racecheck'] if case.startswith('n2000_') else ['memcheck','synccheck']):
                    rec=json.loads((root/'runs'/(tool+'_'+case)/'receipt.json').read_text());assert rec['exit_code']==0 and rec['binary_sha256']==base.sha(binary)
            for i in range(6):invoke(f'timing_{name}_{i}',cmd+['AB' if i%2==0 else 'BA','timing'],binary)

if __name__=='__main__':main()
