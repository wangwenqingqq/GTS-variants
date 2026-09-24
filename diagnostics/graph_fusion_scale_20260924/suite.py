#!/usr/bin/env python3
"""Bounded, fail-closed four-mode campaign; no timing from previous campaigns."""
import argparse,fcntl,hashlib,json
from pathlib import Path
from run_fusion import execute,snapshot
from check import check
ORDERS=['BCDE','EDCB','CEBD','DBEC','DEBC','CBED']

def admit(root,p,phase):
    prerequisites={'selector':[],'smoke':['selector'],'gates':['selector','smoke'],'timing':['selector','smoke','gates'],'profile':['selector','smoke','gates']}
    binary=hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest()
    fixture=json.loads((p/'fixtures/manifest.json').read_text())
    for name,h in fixture['file_sha256'].items():assert hashlib.sha256((p/'fixtures'/name).read_bytes()).hexdigest()==h
    for needed in prerequisites[phase]:
        target=root/'cases/n2000_k1' if needed=='selector' else p
        r=json.loads((target/(needed+'_complete.json')).read_text())
        assert r['complete'] and r['binary_sha256']==binary
        assert r['selector_sha256']==hashlib.sha256((root/'bin/test_selector').read_bytes()).hexdigest()
        for path,h in r['receipts'].items():
            f=root/path;assert hashlib.sha256(f.read_bytes()).hexdigest()==h
            receipt=json.loads(f.read_text());assert receipt['exit_code']==0 and not receipt['stop_reason'] and receipt['post_gpu_clear'] and not receipt['runtime_errors']
    return binary

def run(root,phase,selected):
    with open('/tmp/gtspp_gpu0.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not snapshot('0')['apps'].strip()
        for name in selected:
            p=root/'cases'/name;n=int(name.split('_')[0][1:]);k=int(name.split('_k')[1])
            assert (n,k) in [(2000,1),(100000,1),(611756,1),(611756,32)]
            binary=admit(root,p,phase);receipts={}
            def call(label,m,r=4,reps=1,warm=0,tool='clean',dump=False,qids='queries.qid'):
                assert execute(p,'0',label,m,r,reps,warm,tool,dump,k,qids),(name,label)
                if tool in ['memcheck','synccheck','initcheck','racecheck']:
                    logs=''.join((p/'runs'/label/f).read_text() for f in ['stdout.log','stderr.log'])
                    needle='RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors'
                    assert needle in logs,(name,label)
                receipt=p/'runs'/label/'receipt.json';receipts[str(receipt.relative_to(root))]=hashlib.sha256(receipt.read_bytes()).hexdigest()
                if dump:return check(p,label,r)[0]
            if phase=='selector':
                assert name=='n2000_k1'
                for tool in ['clean','memcheck','synccheck','initcheck','racecheck']:call('selector_'+tool,'T',tool=tool)
            elif phase=='smoke':
                ref=None
                for m in 'ABCDE':
                    call('smoke_'+m,m,dump=True);out,gold=check(p,'smoke_'+m,4,ref);ref=out
                (p/'fixtures/expected_4.json').write_text(json.dumps(gold,indent=2)+'\n')
                if k==1:
                    for r in [0,256,-1]:
                        ref=None
                        for m in ('ABCDE' if r>=0 else 'BCDE'):
                            out=call(f'boundary_{r}_{m}',m,r,dump=True,qids='boundary.qid')
                            if ref is not None:assert out==ref
                            ref=out
                        # Full-N sustained boundary controls use the same four IDs.
                        _,gold=check(p,f'boundary_{r}_E',r)
                        (p/'fixtures'/f'expected_{r}.json').write_text(json.dumps(gold,indent=2)+'\n')
            elif phase=='gates':
                for tool in ['memcheck','synccheck','initcheck','racecheck']:
                    if tool=='racecheck' and k>1:continue
                    for m in ('BCDE' if tool in ['memcheck','synccheck'] and k==1 else 'DE'):
                        call(f'gate_{tool}_{m}',m,tool=tool,dump=True,qids='boundary.qid' if k==1 else 'bundle.qid')
                for m in 'BCDE':call('stress_'+m,m,reps=16,warm=64)
            elif phase=='timing':
                for i,order in enumerate(ORDERS):
                    for m in order:call(f'timing_{i}_{m}',m,reps=4,warm=64)
                for i,order in enumerate(['BCDE','EDCB']):
                    for m in order:call(f'sustained_{i}_{m}',m,reps=16,warm=64)
                if n==611756 and k==1:
                    for r in [0,256]:
                        for i,order in enumerate(['BCDE','EDCB']):
                            for m in order:call(f'selectivity_{r}_{i}_{m}',m,r,reps=32,warm=64,qids='boundary.qid')
            elif phase=='profile':
                assert n in [2000,611756]
                for m in ('BCDE' if n==611756 and k==1 else 'CE'):call('nsys_'+m,m,tool='nsys-node')
            (p/(phase+'_complete.json')).write_text(json.dumps({'complete':True,'phase':phase,'binary_sha256':binary,
              'selector_sha256':hashlib.sha256((root/'bin/test_selector').read_bytes()).hexdigest(),'receipts':receipts},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('phase',choices=['selector','smoke','gates','timing','profile']);p.add_argument('cases',nargs='+')
    a=p.parse_args();run(a.root.resolve(),a.phase,a.cases)
