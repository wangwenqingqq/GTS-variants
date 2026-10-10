#!/usr/bin/env python3
"""Run only the frozen E1 diagnostic; no formal rank or automatic E4 expansion."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from audit import sha,save,load_index
from verify import verify,traces
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--guard',type=Path,required=True)
    p.add_argument('--numa-node',type=int,required=True)
    p.add_argument('--bench',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--inside-guard',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    if not a.inside_guard:
        a.work.mkdir(parents=True,exist_ok=False)
        # One existing guard holds both advisory locks for the entire campaign.
        subprocess.run([sys.executable,str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa_node),
            '--output',str(a.work/'guard'),'--',sys.executable,str(Path(__file__).resolve()),
            *sys.argv[1:],'--inside-guard'],check=True)
        verify(a.work,a.work/'oracle.bin',HERE/'dev32.qid',a.work/'E1_FINAL_VALIDATION.json')
        return
    parent=Path('/proc')/str(os.getppid())/'cmdline'
    if str(a.guard.resolve()).encode() not in parent.read_bytes().split(b'\0') or os.environ.get('CUDA_VISIBLE_DEVICES')!=a.gpu:
        raise RuntimeError('inside-guard requires the actual admitted parent guard')
    manifest=json.loads((HERE/'QUERY_MANIFEST.json').read_text())
    for path,key in [(a.data,'data_sha256'),(a.index,'tree_sha256'),(HERE/'dev32.qid','development_sha256')]:
        if sha(path)!=manifest[key]:raise ValueError('input drift: '+key)
    load_index(a.index)
    save(a.work/'campaign_identity.json',dict(binary_sha256=sha(a.bench),oracle_binary_sha256=sha(a.oracle),
        guard_sha256=sha(a.guard),contract_sha256=sha(HERE/'CONTRACT.yaml'),query_manifest_sha256=sha(HERE/'QUERY_MANIFEST.json'),
        data_sha256=manifest['data_sha256'],tree_sha256=manifest['tree_sha256'],
        scope='E1 diagnostic-only; resident query ID input; not E2 or E3',formal_processes_used=0))
    def run(label,cmd,env):
        base_env={k:v for k,v in os.environ.items() if k not in ['NAV_MODE','NAV_DIAGNOSTIC','NAV_REPLAY']}
        folder=a.work/label;folder.mkdir(exist_ok=False)
        save(folder/'command.json',list(map(str,cmd)))
        with (folder/'stdout.log').open('w') as stdout,(folder/'stderr.log').open('w') as stderr:
            r=subprocess.run(list(map(str,cmd)),env={**base_env,**env},stdout=stdout,stderr=stderr)
        save(folder/'receipt.json',dict(exit_code=r.returncode,guard_context='whole_campaign_pending'))
        if r.returncode:raise RuntimeError('child failed: '+label)
        print('COMPLETE '+label,flush=True)
    qids=HERE/'dev32.qid';oracleout=a.work/'oracle.bin'
    run('oracle',[a.oracle,a.data,qids,8,oracleout],{})
    for mode in range(4):
        label='G'+str(mode)
        run(label,[a.bench,a.data,qids,8,1,1,a.index,a.work/label/'out',0],{'NAV_MODE':str(mode),'NAV_DIAGNOSTIC':'1'})
    timeline=[r['upper'] for r in traces(a.work/'G0/stdout.log') if r['level']>=3]
    (a.work/'G0_upper.txt').write_text(''.join(format(x,'.17g')+'\n' for x in timeline))
    label='G2_G0_U_REPLAY'
    run(label,[a.bench,a.data,qids,8,1,1,a.index,a.work/label/'out',0],
        {'NAV_MODE':'2','NAV_DIAGNOSTIC':'1','NAV_REPLAY':str(a.work/'G0_upper.txt')})
    verify(a.work,oracleout,qids,a.work/'E1_CORRECTNESS.json',guard_pending=True)
    # Instrumented durations are never used as comparator times.
    # Fresh reverse-order uninstrumented samples are diagnostic only, not promotion.
    for mode in [3,2,1,0]:
        label='timing_G'+str(mode)
        env={k:v for k,v in os.environ.items() if k not in ['NAV_DIAGNOSTIC','NAV_REPLAY']}
        env['NAV_MODE']=str(mode)
        run(label,[a.bench,a.data,qids,8,1,1,a.index,a.work/label/'out',1],env)
        if (a.work/label/'out.bin').read_bytes()!=oracleout.read_bytes():raise ValueError('timing output mismatch')
    save(a.work/'E1_COMPLETE.json',dict(diagnostic_only=True,formal_admission=False,formal_processes_used=0,
        order=['oracle','G0','G1','G2','G3','G2_G0_U_REPLAY','timing_G3','timing_G2','timing_G1','timing_G0']))

if __name__=='__main__':main()
