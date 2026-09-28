#!/usr/bin/env python3
import argparse,fcntl,hashlib,json,subprocess,sys,datetime
from pathlib import Path
SIZES=[2000,4000,8000,16000,32000,64000,128000,256000]
STAGES=['selector','full','gates','stress','timing','sustained','trace']
def repeats(n):return 64 if n<=16000 else 8 if n<=64000 else 2 if n==128000 else 1
def rows(stage):
    # n,label,mode,radius,repeats,warmup,tool,dump,qfile,binary
    def row(n,label,m,r=4,reps=1,warm=0,t='clean',dump=False,small=False,binary='graph_bench'):
        return (n,label,m,r,reps,warm,t,dump,'check_queries.qid' if small else 'queries.qid',binary)
    if stage=='selector':return [row(2000,'selector_'+t,'T',t=t,small=True,binary='test_selector') for t in ['clean','memcheck','synccheck','initcheck','racecheck']]
    if stage=='full':
        out=[]
        for n in SIZES:
            out += [row(n,f'full_{r}_{m}',m,r,dump=True,small=r!=4) for r in [4,0,256,-1] for m in ('CE' if r==-1 else 'ACE')]
            if n==2000:out += [row(n,'anchor_full_'+m,m,dump=True,binary='graph_bench_anchor') for m in 'CE']
        return out
    if stage=='gates':
        return [row(n,f'gate_{t}_{m}',m,t=t,small=True) for n in SIZES for t,m in ([(t,m) for t in ['memcheck','synccheck'] for m in 'CE']+([(t,'E') for t in ['initcheck','racecheck']] if n in [2000,16000,128000,256000] else []))]
    if stage=='stress':return [row(n,'stress_'+m,m,reps=4,warm=64) for n in SIZES for m in 'CE']
    if stage=='timing':
        out=[]
        for i in range(6):
            for n in (SIZES if i%2==0 else SIZES[::-1]):
                order='CE' if i%2==0 else 'EC'
                out += [row(n,f'timing_{i}_{m}',m,reps=repeats(n),warm=64) for m in order]
                if n==2000:out += [row(n,f'anchor_timing_{i}_{m}',m,reps=repeats(n),warm=64,binary='graph_bench_anchor') for m in order]
        return out
    if stage=='sustained':return [row(n,f'sustained_{i}_{m}',m,reps=2*repeats(n),warm=64) for i in range(2) for n in (SIZES if i==0 else SIZES[::-1]) for m in ('CE' if i==0 else 'EC')]
    if stage=='trace':return [row(n,'nsys_'+m,m,warm=8,t='nsys-node',small=True) for n in SIZES for m in 'CE']
    raise ValueError(stage)
def verify_stage(root,stage):
    from verify import clean,sha
    for n,label,m,r,reps,w,t,dump,qf,b in rows(stage):
        p=root/'data'/str(n)/'runs'/label;v=json.loads((p/'receipt.json').read_text());clean(v)
        assert (v['mode'],v['radius'],v['repeats'],v['warmup'],v['tool'],v['dump'],v['qfile'],v['binary'])==(m,r,reps,w,t,dump,qf,b)
        assert v['binary_sha256']==sha(root/'bin'/b) and v['runner_sha256']==sha(root/'run.py')
        if stage!='full':assert v['validation']['pass'],label
        if t in ['memcheck','synccheck','initcheck','racecheck']:
            logs=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards' if t=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs,label
def main(root,gpu,index):
    sys.path.insert(0,str(root));from run import execute,snapshot
    from verify import full
    with open(f'/tmp/gtspp_gpu{index}.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=snapshot(gpu);assert not state['apps'].strip();assert state['gpu'].split(',')[0].strip()==str(index)
        assert state['gpu'].split(',')[1].strip()==gpu
        (root/'logs/admission.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state=state,gpu_index=index,clock_policy='unchanged/uncontrolled',cpu='shared/unpinned'),indent=2)+'\n')
        for stage in STAGES:
            print('START',stage,datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
            with (root/'logs'/f'{stage}.txt').open('x') as out:
                import contextlib
                with contextlib.redirect_stdout(out):
                    for n,label,m,r,reps,w,t,dump,qf,b in rows(stage):
                        assert execute(root/'data'/str(n),gpu,label,m,r,reps,w,t,dump,qf,b),(n,label)
                    if stage=='full':
                        for n in SIZES:print(n,'PASS full',full(root/'data'/str(n)),flush=True)
                    verify_stage(root,stage)
            print('DONE',stage,datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
        (root/'logs/COMPLETE.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runs=sum(len(rows(s)) for s in STAGES))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args();main(a.root.resolve(),a.gpu,a.index)
