#!/usr/bin/env python3
import argparse,contextlib,datetime,fcntl,json,sys
from pathlib import Path
from verify import DATASETS,SIZES,clean,full,read,sha
STAGES=['full','gates','stress','timing','sustained','trace']
def repeats(n):return 4 if n==65536 else 1
def rows(stage,root):
    # dataset,size,label,mode,radius,repeats,warmup,tool,dump,qfile,binary
    def row(d,n,label,m,r,reps=1,warm=0,t='clean',dump=False,q='queries.qid'):
        return (d,n,label,m,r,reps,warm,t,dump,q,'graph_bench')
    if stage=='full':
        out=[]
        for d in DATASETS:
            for n in SIZES:
                r=read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']
                out += [row(d,n,'full_normal_'+m,m,r['normal'],dump=True) for m in 'ACE']
                if n==1000000:
                    out += [row(d,n,'full_zero_'+m,m,r['zero'],dump=True,q='zero.qid') for m in 'ACE']
                    out += [row(d,n,'full_all_'+m,m,r['all'],dump=True,q='all.qid') for m in 'ACE']
                    out += [row(d,n,'full_empty_'+m,m,r['empty'],dump=True,q='negative.qid') for m in 'CE']
        return out
    if stage=='gates':
        out=[]
        for d in DATASETS:
            for n in SIZES:
                r=read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                out += [row(d,n,f'gate_{t}_{m}',m,r,t=t,q='check.qid') for t in ['memcheck','synccheck'] for m in 'CE']
                if n==1000000:out += [row(d,n,f'gate_{t}_E','E',r,t=t,q='check.qid') for t in ['initcheck','racecheck']]
        return out
    if stage=='stress':
        return [row(d,n,'stress_'+m,m,read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal'],4,16)
                for d in DATASETS for n in SIZES for m in 'CE']
    if stage=='timing':
        out=[]
        for i in range(6):
            ds=DATASETS if i%2==0 else DATASETS[::-1]
            ns=SIZES if i%2==0 else SIZES[::-1]
            for d in ds:
                for n in ns:
                    r=read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                    out += [row(d,n,f'timing_{i}_{m}',m,r,repeats(n),16) for m in ('CE' if i%2==0 else 'EC')]
        return out
    if stage=='sustained':
        return [row(d,n,f'sustained_{i}_{m}',m,read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal'],2*repeats(n),16)
                for i in range(2) for d in (DATASETS if i==0 else DATASETS[::-1]) for n in (SIZES if i==0 else SIZES[::-1])
                for m in ('CE' if i==0 else 'EC')]
    if stage=='trace':
        return [row(d,n,'nsys_'+m,m,read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal'],1,2,'nsys-node',False,'trace.qid')
                for d in DATASETS for n in SIZES for m in 'CE']
    raise ValueError(stage)
def verify_stage(root,stage):
    for d,n,label,m,r,reps,w,t,dump,q,b in rows(stage,root):
        p=root/'data'/d/str(n)/'runs'/label;x=read(p/'receipt.json');clean(x)
        assert (x['mode'],x['radius'],x['repeats'],x['warmup'],x['tool'],x['dump'],x['qfile'],x['binary'])==(m,r,reps,w,t,dump,q,b),(d,n,label)
        assert x['binary_sha256']==sha(root/'bin'/b) and x['runner_sha256']==sha(root/'run.py')
        if stage!='full':assert x['validation']['pass'],(d,n,label)
        if t in ['memcheck','synccheck','initcheck','racecheck']:
            log=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards' if t=='racecheck' else 'ERROR SUMMARY: 0 errors') in log,(d,n,label)
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
                with contextlib.redirect_stdout(out):
                    for d,n,label,m,r,reps,w,t,dump,q,b in rows(stage,root):
                        assert execute(root/'data'/d/str(n),gpu,label,m,r,reps,w,t,dump,q,b),(d,n,label)
                    if stage=='full':
                        for d in DATASETS:
                            for n in SIZES:print(d,n,'PASS full',full(root/'data'/d/str(n),d,n),flush=True)
                    verify_stage(root,stage)
            print('DONE',stage,datetime.datetime.now(datetime.timezone.utc).isoformat(),flush=True)
        (root/'logs/COMPLETE.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':sum(len(rows(s,root)) for s in STAGES)})+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--index',type=int,required=True)
    a=p.parse_args();main(a.root.resolve(),a.gpu,a.index)
