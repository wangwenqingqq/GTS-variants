#!/usr/bin/env python3
import argparse,datetime,fcntl,json,sys
from pathlib import Path
from verify import DATASETS,radii,read,clean,full,sha
STAGES=['full','gates','stress','timing','sustained','trace']
def repeats(d):return 64 if d in ['Words','Tloc'] else 8
def rows(stage,root):
    # dataset,label,mode,radius,repeats,warmup,tool,dump,qfile,binary
    def row(d,label,m,r,rep=1,warm=0,tool='clean',dump=False,q='queries.qid',binary='graph_bench'):
        return d,label,m,r,rep,warm,tool,dump,q,binary
    if stage=='full':
        out=[]
        for d in DATASETS:
            rr=radii(read(root/'data'/d/'fixtures/oracle.json'),d)
            for name in ['normal','zero','all','empty']:
                out += [row(d,f'full_{name}_{m}',m,rr[name],dump=True) for m in ('CE' if name=='empty' else 'ACE')]
            if d=='Words':out += [row(d,'anchor_full_'+m,m,4,dump=True,binary='graph_bench_anchor') for m in 'CE']
        return out
    if stage=='gates':
        return [row(d,f'gate_{t}_{m}',m,radii(read(root/'data'/d/'fixtures/oracle.json'),d)['normal'],tool=t,q='check_queries.qid')
                for d in DATASETS for t,m in ([(t,m) for t in ['memcheck','synccheck'] for m in 'CE']+[(t,'E') for t in ['initcheck','racecheck']])]
    if stage=='stress':return [row(d,'stress_'+m,m,radii(read(root/'data'/d/'fixtures/oracle.json'),d)['normal'],4,64) for d in DATASETS for m in 'CE']
    if stage=='timing':
        out=[]
        for i in range(6):
            for d in (DATASETS if i%2==0 else DATASETS[::-1]):
                r=radii(read(root/'data'/d/'fixtures/oracle.json'),d)['normal']
                for m in ('CE' if i%2==0 else 'EC'):
                    out.append(row(d,f'timing_{i}_{m}',m,r,repeats(d),64))
                if d=='Words':
                    for m in ('CE' if i%2==0 else 'EC'):out.append(row(d,f'anchor_timing_{i}_{m}',m,r,repeats(d),64,binary='graph_bench_anchor'))
        return out
    if stage=='sustained':
        return [row(d,f'sustained_{i}_{m}',m,radii(read(root/'data'/d/'fixtures/oracle.json'),d)['normal'],2*repeats(d),64)
                for i in range(2) for d in (DATASETS if i==0 else DATASETS[::-1]) for m in ('CE' if i==0 else 'EC')]
    if stage=='trace':
        return [row(d,'nsys_'+m,m,radii(read(root/'data'/d/'fixtures/oracle.json'),d)['normal'],warm=8,tool='nsys-node',q='check_queries.qid') for d in DATASETS for m in 'CE']
    raise ValueError(stage)
def verify_stage(root,stage):
    for d,label,m,r,rep,w,t,dump,q,b in rows(stage,root):
        p=root/'data'/d/'runs'/label;v=read(p/'receipt.json');clean(v)
        assert (v['mode'],v['radius'],v['repeats'],v['warmup'],v['tool'],v['dump'],v['qfile'],v['binary'])==(m,r,rep,w,t,dump,q,b),(d,label)
        assert v['binary_sha256']==sha(root/'bin'/b) and v['runner_sha256']==sha(root/'run.py')
        if stage!='full':assert v['validation']['pass'],(d,label)
        if t in ['memcheck','synccheck','initcheck','racecheck']:
            logs=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards' if t=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs,(d,label)
def main(root,gpu,index):
    sys.path.insert(0,str(root));from run import execute,snapshot
    with open(f'/tmp/gtspp_gpu{index}.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=snapshot(gpu);assert not state['apps'].strip() and state['gpu'].split(',')[0].strip()==str(index)
        assert state['gpu'].split(',')[1].strip()==gpu
        (root/'logs/admission.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':state,'gpu_index':index},indent=2)+'\n')
        for stage in STAGES:
            print('START',stage,datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
            with (root/'logs'/f'{stage}.txt').open('x') as out:
                import contextlib
                with contextlib.redirect_stdout(out):
                    for d,label,m,r,rep,w,t,dump,q,b in rows(stage,root):
                        assert execute(root/'data'/d,gpu,label,m,r,rep,w,t,dump,q,b),(d,label)
                    if stage=='full':
                        for d in DATASETS:print(d,'PASS full',len(full(root/'data'/d,d)['full_checks']),flush=True)
                    verify_stage(root,stage)
            print('DONE',stage,datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
        (root/'logs/COMPLETE.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':sum(len(rows(s,root)) for s in STAGES)})+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--index',type=int,required=True)
    a=p.parse_args();main(a.root.resolve(),a.gpu,a.index)
