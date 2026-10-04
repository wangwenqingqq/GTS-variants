#!/usr/bin/env python3
"""Serial task controller: bounded attribution, native replay, static campaign."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from campaign10k import ROOT,common,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--u0',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);a=p.parse_args()
    lock=open('/tmp/gts_10k_20261004_controller.lock','a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert (ROOT/'F0_SMALL.json').exists()
    prior=int((ROOT/'DIAGNOSTIC_CONTROLLER.pid').read_text()) if (ROOT/'DIAGNOSTIC_CONTROLLER.pid').exists() else -1
    while Path(f'/proc/{prior}/cmdline').exists():
        cmd=Path(f'/proc/{prior}/cmdline').read_bytes()
        if b'diagnose10k.py' not in cmd:break
        save(ROOT/'PROGRESS.json',{'state':'running','phase':'waiting_owned_diagnostics','owned_pid':prior})
        time.sleep(15)
    assert (ROOT/'INPUT_IDENTITIES.json').exists()
    phases=[('native_development',[a.faiss_python,ROOT/'campaign10k.py','native-lane',*common(a)]),
            ('static_campaign',[a.faiss_python,ROOT/'campaign10k.py','pipeline',*common(a)])]
    try:
        for phase,cmd in phases:
            save(ROOT/'PROGRESS.json',{'state':'running','phase':phase,'controller_pid':os.getpid()})
            subprocess.run(list(map(str,cmd)),check=True)
        save(ROOT/'CONTROLLER_COMPLETE.json',{'state':'static_matrix_collection_complete',
             'remaining':['K10_30k_sustained','R10_5_workloads','full_operator_attribution','native_timed_adapter'],
             'U10_ARRIVAL':'not admitted: unified keeper/real-vector API absent'})
    except Exception as e:
        save(ROOT/'CONTROLLER_STOPPED.json',{'state':'stopped','phase':phase,'error':str(e)});raise

if __name__=='__main__':main()
