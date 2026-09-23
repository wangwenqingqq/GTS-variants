#!/usr/bin/env python3
"""Serial, fail-closed full-query campaign on explicitly admitted GPU0."""
import argparse
import fcntl
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
ORDERS=['OSTD','TDOS','SODT','DTSO','DSOT','TOSD']

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True);ap.add_argument('--stage',choices=['check','sanitizer','timing','profile'],required=True);a=ap.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
    assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0','physical GPU0 only'
    locks=[]
    for path in [Path('/tmp/gtspp_gpu0.lock'),root/'run.lock']:
        f=path.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    def invoke(label,cmd,binary):
        out=root/'runs'/label;out.mkdir(exist_ok=False);pre=base.snapshot(a.gpu)
        (out/'before.json').write_text(json.dumps(pre,indent=2)+'\n');assert not pre['apps'].strip(),'GPU0 occupied; stop'
        start=time.time();cpu=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
            try:rc=subprocess.run(list(map(str,cmd)),cwd=out,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu},stdout=stdout,stderr=stderr,timeout=300).returncode
            except subprocess.TimeoutExpired:rc=124
        end=resource.getrusage(resource.RUSAGE_CHILDREN);post=base.snapshot(a.gpu)
        text=(out/'stdout.log').read_text()+(out/'stderr.log').read_text()
        correct=all('correct,'+v+',full_integer_oracle' in text for v in 'OSTD') and 'pass' in text.splitlines()
        rec={'label':label,'command':list(map(str,cmd)),'gpu_uuid':a.gpu,'start':start,'wall_s':time.time()-start,'user_s':end.ru_utime-cpu.ru_utime,'system_s':end.ru_stime-cpu.ru_stime,'exit_code':rc,'binary_sha256':base.sha(binary),'post_clear':not post['apps'].strip(),'correct':correct}
        (out/'after.json').write_text(json.dumps(post,indent=2)+'\n');(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(label,'rc',rc,'correct',correct,'wall_s',round(rec['wall_s'],3),flush=True)
        assert rc==0 and correct and rec['post_clear'],'failed/contaminated process; retain and stop'
    for n,q,r in CASES:
        name=f'n{n}_q{q}_r{r}';fixture=root/'fixtures'/f'n{n}';binary=root/'bin'/('bench3' if n==2000 else 'bench5')
        manifest=json.loads((fixture/'manifest.json').read_text())
        expected=json.loads((HERE.parent/'tc_leaf_probe/EVIDENCE.json').read_text())['fixtures'][f'n{n}']
        assert manifest==expected,'fixture not identical to parent campaign'
        for fname,h in manifest['file_sha256'].items():assert base.sha(fixture/fname)==h
        cmd=[binary,fixture/'data.txt',fixture/f'q{q}.txt',r]
        if a.stage=='check':invoke('check_'+name,cmd+['OSTD','check'],binary)
        elif a.stage=='sanitizer':
            for tool in (['memcheck','synccheck','initcheck','racecheck'] if n==2000 else ['memcheck','synccheck']):
                invoke(tool+'_'+name,['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd+['OSTD','check'],binary)
        elif a.stage=='profile' and (n,q,r)==(65536,128,500):
            out=root/'runs'/('profile_'+name)
            invoke('profile_'+name,['nsys','profile','--trace=cuda','--sample=none','--cpuctxsw=none','--cuda-um-cpu-page-faults=true','--cuda-um-gpu-page-faults=true','--force-overwrite=false','--output='+str(out/'trace')]+cmd+['OSTD','check'],binary)
        elif a.stage=='timing' and n==65536:
            for case in ['n2000_q32_r300',name]:
                for tool in (['check','memcheck','synccheck','initcheck','racecheck'] if case.startswith('n2000_') else ['check','memcheck','synccheck']):
                    rec=json.loads((root/'runs'/(tool+'_'+case)/'receipt.json').read_text());assert rec['exit_code']==0 and rec['correct'] and rec['post_clear'];assert rec['binary_sha256']==base.sha(root/'bin'/('bench3' if case.startswith('n2000_') else 'bench5'))
            for i,order in enumerate(ORDERS):invoke(f'timing_{name}_{i}',cmd+[order,'timing'],binary)

if __name__=='__main__':main()
