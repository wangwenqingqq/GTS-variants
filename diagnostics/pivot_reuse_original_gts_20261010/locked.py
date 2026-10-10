#!/usr/bin/env python3
"""Reuse the owned-process runner; bound its inherited GPU telemetry calls."""
import importlib.util
from pathlib import Path
import subprocess

def snapshot(gpu):
    def query(field):
        return subprocess.check_output(['nvidia-smi','-i',gpu,field,'--format=csv,noheader'],
                                       text=True,timeout=10).strip()
    return {'device':query('--query-gpu=index,uuid,name,memory.used,utilization.gpu'),
            'apps':query('--query-compute-apps=pid,process_name,used_memory')}

if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('preserved_runner',Path(__file__).parent/'helpers/run_locked.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    runner.snapshot=snapshot
    runner.main()
