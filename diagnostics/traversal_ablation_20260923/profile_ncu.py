#!/usr/bin/env python3
"""Three fixed NCU diagnostics using the already validated monitored runner."""
import argparse
import fcntl
import hashlib
import importlib.util
from pathlib import Path
import subprocess

RUNNER_SHA = '913518ea283b048b299aa96edfde9a96725e19182cac96a60930dad61b850658'
BINARY_SHA = '6811e8ea55bc596e833f4c347d028f1a4822c4c3e1d349e2abb5745a0b492109'
SECTIONS = ['SpeedOfLight','LaunchStats','Occupancy','SchedulerStats',
            'WarpStateStats','MemoryWorkloadAnalysis','InstructionStats']


def derive(source):
    assert hashlib.sha256(source.encode()).hexdigest() == RUNNER_SHA
    anchor = "    elif tool!='clean':"
    assert source.count(anchor) == 1
    branch = '''    elif tool=='ncu':
        kernel,count={'D':('findNextRnn',2),'G':('fusedTraversal',1),'Q':('dedupLevel',2)}[mode]
        cmd=['ncu','--kernel-name-base','demangled','--kernel-name','regex:'+kernel,
             '--launch-count',str(count),'--clock-control','none','--cache-control','none',
             '--export',str(path/'profile')] + SECTIONS_ARGS + cmd
'''
    source = source.replace(anchor, branch + anchor)
    source = source.replace("limit=120 if", "limit=180 if tool=='ncu' else 120 if")
    source = source.replace("if 'error:' in x.lower()", "if '==ERROR==' in x or 'error:' in x.lower()")
    args = [arg for section in SECTIONS for arg in ['--section',section]]
    return source.replace('import argparse\n', 'import argparse\nSECTIONS_ARGS='+repr(args)+'\n')


def main(root, gpu):
    assert hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest() == BINARY_SHA
    assert (root/'full_verified.json').is_file()
    assert (root/'fixtures/expected_4.json').is_file()
    source = derive((root/'run_ablation.py').read_text())
    dest = root/'ncu';dest.mkdir()
    (dest/'runs').mkdir()
    for name in ['bin','fixtures']:(dest/name).symlink_to(root/name, target_is_directory=True)
    runner = dest/'run_ncu.py';runner.write_text(source)
    spec = importlib.util.spec_from_file_location('ncu_runner',runner)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    state = module.snapshot(gpu)
    assert not state['apps'].strip(), 'Occupied GPU; no foreign process touched'
    assert state['gpu'].split(',')[0].strip() == '1', 'Only GPU 1 is admitted'
    with open('/tmp/gtspp_gpu1.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for mode in 'DGQ':
            assert module.execute(dest,gpu,'ncu_'+mode,mode,4,1,0,'ncu',False)
            path = dest/'runs'/('ncu_'+mode)
            for page,filename in [('details','metrics.csv'),('raw','metrics_raw.csv')]:
                with (path/filename).open('w') as out:
                    subprocess.run(['ncu','--import',str(path/'profile.ncu-rep'),
                                    '--page',page,'--csv'],stdout=out,check=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('--gpu',required=True)
    a=p.parse_args();main(a.root.resolve(),a.gpu)
