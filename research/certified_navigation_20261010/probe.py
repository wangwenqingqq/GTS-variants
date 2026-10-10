#!/usr/bin/env python3
"""Bounded real-shape sanitizer/NSYS subset; never creates a formal timing sample."""
import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
from audit import sha,save


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--bench',type=Path,required=True);p.add_argument('--qids',type=Path,required=True)
    p.add_argument('--sanitizer',type=Path,required=True);p.add_argument('--nsys',type=Path,required=True)
    p.add_argument('--memory-only',action='store_true',help='Explicitly suppress API-error reporting; never a full API gate')
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
    if not os.environ.get('CUDA_VISIBLE_DEVICES'):raise RuntimeError('requires admitted parent GPU guard')
    query_ids=list(map(int,a.qids.read_text().split()))
    q2=a.work/'first2.qid';q2.write_text('2\n'+str(query_ids[1])+'\n'+str(query_ids[2])+'\n')
    identity={'scope':'sanitizer/NSYS first two frozen development queries; diagnostic only',
              'bench_sha256':sha(a.bench),'sanitizer_sha256':sha(a.sanitizer),'nsys_sha256':sha(a.nsys),
              'formal_processes_used':0,'full_E2_matrix_passed':False,
              'api_error_reporting_disabled':a.memory_only}
    save(a.work/'IDENTITY.json',identity)
    jobs=[('memcheck_G0',0,'memcheck'),('memcheck_G3',3,'memcheck'),
          ('initcheck_G0',0,'initcheck'),('initcheck_G3',3,'initcheck'),
          ('synccheck_G0',0,'synccheck'),('synccheck_G3',3,'synccheck'),
          ('nsys_G0',0,None),('nsys_G3',3,None)]
    for label,mode,tool in jobs:
        folder=a.work/label;folder.mkdir()
        args=[str(a.bench),str(a.data),str(q2),'8','1','1',str(a.index),str(folder/'out'),'0']
        api_flags=['--report-api-errors','no'] if a.memory_only else []
        cmd=([str(a.sanitizer),'--tool',tool,'--error-exitcode','86','--print-limit','10',*api_flags,*args] if tool else
             [str(a.nsys),'profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--output',str(folder/'trace'),*args])
        save(folder/'command.json',cmd)
        env={k:v for k,v in os.environ.items() if k not in ['NAV_MODE','NAV_DIAGNOSTIC','NAV_REPLAY']};env['NAV_MODE']=str(mode)
        with (folder/'stdout.log').open('w') as o,(folder/'stderr.log').open('w') as e:
            process=subprocess.Popen(cmd,env=env,stdout=o,stderr=e,start_new_session=True)
            timed_out=False
            try:code=process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(process.pid,signal.SIGTERM)
                try:code=process.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);code=process.wait()
        save(folder/'receipt.json',{'exit_code':code,'timed_out':timed_out,'binary_sha256':sha(a.bench),'guard_context':'whole_probe_pending'})
        if code or timed_out:raise RuntimeError(label+' failed; preserve evidence and stop')
        if tool:
            text=(folder/'stdout.log').read_text()+(folder/'stderr.log').read_text()
            if 'ERROR SUMMARY: 0 errors' not in text:raise RuntimeError(label+' missing sanitizer zero-error receipt')
        else:
            subprocess.run([str(a.nsys),'export','--type=sqlite','--output',str(folder/'trace.sqlite'),str(folder/'trace.nsys-rep')],check=True)
        print('COMPLETE '+label,flush=True)
    blobs=[(a.work/label/'out.bin').read_bytes() for label,_,_ in jobs]
    if any(x!=blobs[0] for x in blobs):raise RuntimeError('probe output mismatch')
    save(a.work/'COMPLETE.json',{'real_shape_subset_passed':True,'API_gate_passed':not a.memory_only,
         'formal_admission':False,'full_E2_matrix_passed':False,'result_sha256':sha(a.work/'memcheck_G0/out.bin')})

if __name__=='__main__':main()
