#!/usr/bin/env python3
"""Run one P4 diagnostic under the GPU admission lock and NUMA policy."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def snapshot(gpu):
    def query(field):
        return subprocess.check_output(
            ['nvidia-smi', '-i', gpu, field, '--format=csv,noheader'], text=True).strip()
    return {'device': query('--query-gpu=index,uuid,name,memory.used,utilization.gpu'),
            'apps': query('--query-compute-apps=pid,process_name,used_memory')}


def descendants(pid):
    owned={pid};pending=[pid]
    while pending:
        for path in Path(f'/proc/{pending.pop()}/task').glob('*/children'):
            try: children=[int(x) for x in path.read_text().split()]
            except (FileNotFoundError,ProcessLookupError): continue
            for child in children:
                if child not in owned: owned.add(child);pending.append(child)
    return owned


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    cmd=args.command[1:] if args.command and args.command[0]=='--' else args.command
    if not cmd: parser.error('command required after --')
    args.output.mkdir(parents=True,exist_ok=False)
    before=snapshot(args.gpu)
    if before['apps']:raise RuntimeError('GPU occupied before admission')
    gpu_index=before['device'].split(',')[0].strip()
    command=['numactl','--cpunodebind=3','--membind=3',*cmd]
    (args.output/'command.json').write_text(json.dumps(command)+'\n')
    (args.output/'before.json').write_text(json.dumps(before)+'\n')
    checks=[];reason=None
    with open(f'/tmp/gtspp_gpu{gpu_index}.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if snapshot(args.gpu)['apps']:raise RuntimeError('GPU occupied after lock')
        with (args.output/'stdout.log').open('w') as out, \
             (args.output/'stderr.log').open('w') as err, \
             (args.output/'gpu.csv').open('w') as gpu_log:
            monitor=subprocess.Popen(
                ['nvidia-smi','-i',args.gpu,
                 '--query-gpu=timestamp,memory.used,utilization.gpu,power.draw',
                 '--format=csv,noheader,nounits','-lms','200'],
                stdout=gpu_log,stderr=err)
            start=time.monotonic()
            process=subprocess.Popen(command,env={**os.environ,'CUDA_VISIBLE_DEVICES':args.gpu},
                                     stdout=out,stderr=err,start_new_session=True)
            try:
                while process.poll() is None:
                    apps=snapshot(args.gpu)['apps']
                    owned=descendants(process.pid)
                    foreign=[line for line in apps.splitlines()
                             if int(line.split(',')[0]) not in owned]
                    checks.append({'seconds':time.monotonic()-start,'foreign':foreign})
                    if foreign:reason='foreign GPU activity'
                    if time.monotonic()-start>1200:reason='timeout'
                    if reason:
                        os.killpg(process.pid,signal.SIGTERM)
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
                        break
                    time.sleep(.2)
            finally:monitor.terminate();monitor.wait(timeout=10)
            wall=time.monotonic()-start
        after=snapshot(args.gpu)
    (args.output/'after.json').write_text(json.dumps(after)+'\n')
    (args.output/'checks.json').write_text(json.dumps(checks)+'\n')
    record={'gpu':args.gpu,'command':command,'binary_sha256':hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest(),
            'exit_code':process.returncode,'stop_reason':reason,'wall_s':wall,
            'runtime_valid':process.returncode==0 and reason is None and not after['apps']}
    (args.output/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if not record['runtime_valid']:raise SystemExit(1)


if __name__=='__main__':main()
