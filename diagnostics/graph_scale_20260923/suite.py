#!/usr/bin/env python3
"""Sequential bounded campaign using the existing monitored runner and GPU lock."""
import argparse,fcntl,json
from pathlib import Path
from run_scale import execute,snapshot
from check import check


def run(root,phase,selected):
    with open('/tmp/gtspp_gpu0.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not snapshot('0')['apps'].strip()
        for case in selected:
            p=root/'cases'/case;k=int(case.split('_k')[1]);n=int(case.split('_')[0][1:])
            def call(label,m,r=4,reps=1,warm=0,tool='clean',dump=False,qids='queries.qid'):
                assert execute(p,'0',label,m,r,reps,warm,tool,dump,k,qids),(case,label)
                if tool in ('memcheck','synccheck','initcheck'):
                    logs=''.join((p/'runs'/label/f).read_text() for f in ['stdout.log','stderr.log'])
                    assert 'ERROR SUMMARY: 0 errors' in logs,(case,label)
                if dump:return check(p,label,r)[0]
            if phase=='smoke':
                ref=None;gold=None
                for m in 'ABC':
                    name='smoke_'+m;call(name,m,dump=True)
                    out,gold=check(p,name,4,ref);ref=out
                (p/'fixtures/expected_4.json').write_text(json.dumps(gold,indent=2)+'\n')
            elif phase=='gates':
                for tool in ['memcheck','synccheck','initcheck']:
                    for m in ('ABC' if tool!='initcheck' and k==1 else 'BC'):
                        call(f'gate_{tool}_{m}',m,tool=tool,dump=True,qids='boundary.qid' if k==1 else 'queries.qid')
                if k==1:
                    for r in [0,256]:
                        ref=None
                        for m in 'ABC':
                            name=f'boundary_{r}_{m}';out=call(name,m,r,dump=True,qids='boundary.qid')
                            if ref is not None:assert out==ref
                            ref=out
                    if n==611756:
                        for m in 'BC':call('boundary_negative_'+m,m,-1,tool='memcheck',dump=True,qids='boundary.qid')
                for m in 'ABC':call('stress_'+m,m,reps=16,warm=64)
            elif phase=='timing':
                for i,order in enumerate(['ABC','CBA','BCA','ACB','CAB','BAC']):
                    for m in order:call(f'timing_{i}_{m}',m,reps=4,warm=64)
                for i,order in enumerate(['BC','CB']):
                    for m in order:call(f'sustained_{i}_{m}',m,reps=16,warm=64)
            elif phase=='profile':
                assert n==611756 and k in [1,32]
                for m in 'BC':call('nsys_'+m,m,warm=0,tool='nsys-node')
            (p/(phase+'_complete.json')).write_text(json.dumps({'complete':True,'phase':phase})+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('phase',choices=['smoke','gates','timing','profile']);p.add_argument('cases',nargs='+')
    a=p.parse_args();run(a.root.resolve(),a.phase,a.cases)
