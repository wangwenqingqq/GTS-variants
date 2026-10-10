#!/usr/bin/env python3
"""Separately identified guard: observe owned process identities on both sides of a GPU snapshot."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from common import outside_repo


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


def proc_identity(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return int(fields[19])  # Linux starttime prevents accepting a reused PID.
    except (FileNotFoundError,ProcessLookupError):
        return None


def owned_identities(pid):
    result={}
    for child in descendants(pid):
        identity=proc_identity(child)
        if identity is not None:result[child]=identity
    return result


def classify_apps(apps,before,after,current):
    foreign=[];observations=[]
    for line in apps.splitlines():
        pid=int(line.split(',')[0]);live=current.get(pid)
        identities={owners[pid] for owners in (before,after) if pid in owners}
        # No history-only whitelist: ownership must bracket this very snapshot.
        admitted=len(identities)==1 and (live is None or live in identities)
        if not admitted:foreign.append(line)
        observations.append(dict(pid=pid,current_starttime=live,observed_owned_starttimes=sorted(identities),owned=admitted))
    return foreign,observations


def stop_owned(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)


def acquire_locks(stack,paths):
    seen=set()
    for index,path in enumerate(paths):
        if path.exists():lock=stack.enter_context(path.open('r'))
        elif index<2:lock=stack.enter_context(path.open('a+'))
        else:continue
        stat=os.fstat(lock.fileno());identity=(stat.st_dev,stat.st_ino)
        if identity in seen:continue
        seen.add(identity)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--numa-node',type=int,required=True,
                        help='Explicit verified NUMA placement for the admitted GPU')
    parser.add_argument('--legacy-lock-root',type=Path,default=Path('/tmp'),
                        help='Optional shared legacy lock alias directory')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    cmd=args.command[1:] if args.command and args.command[0]=='--' else args.command
    if not cmd: parser.error('command required after --')
    args.output=outside_repo(args.output)
    args.output.mkdir(parents=True,exist_ok=False)
    before=snapshot(args.gpu)
    if before['apps']:raise RuntimeError('GPU occupied before admission')
    gpu_index=before['device'].split(',')[0].strip()
    command=['numactl',f'--cpunodebind={args.numa_node}',f'--membind={args.numa_node}',*cmd]
    (args.output/'command.json').write_text(json.dumps(command)+'\n')
    (args.output/'before.json').write_text(json.dumps(before)+'\n')
    checks=[];reason=None
    with ExitStack() as stack:
        paths=[Path(f'/tmp/gtspp_gpu{gpu_index}.lock'),
               Path(f'/tmp/gts_auto_knn_pro6000_gpu{gpu_index}.lock'),
               args.legacy_lock_root/f'gtspp_gpu{gpu_index}.lock',
               args.legacy_lock_root/f'gts_auto_knn_pro6000_gpu{gpu_index}.lock']
        acquire_locks(stack,paths)
        if snapshot(args.gpu)['apps']:raise RuntimeError('GPU occupied after lock')
        with (args.output/'stdout.log').open('w') as out, \
             (args.output/'stderr.log').open('w') as err, \
             (args.output/'gpu.csv').open('w') as gpu_log:
            monitor=subprocess.Popen(
                ['nvidia-smi','-i',args.gpu,
                 '--query-gpu=timestamp,memory.used,utilization.gpu,power.draw,clocks.current.sm,clocks.current.memory,temperature.gpu,pstate',
                 '--format=csv,noheader,nounits','-lms','200'],
                stdout=gpu_log,stderr=err)
            start=time.monotonic()
            process=None
            try:
                process=subprocess.Popen(command,env={**os.environ,'CUDA_VISIBLE_DEVICES':args.gpu},
                                         stdout=out,stderr=err,start_new_session=True)
                while process.poll() is None:
                    owned_before=owned_identities(process.pid)
                    apps=snapshot(args.gpu)['apps']
                    owned_after=owned_identities(process.pid)
                    live={int(line.split(',')[0]):proc_identity(int(line.split(',')[0])) for line in apps.splitlines()}
                    foreign,observations=classify_apps(apps,owned_before,owned_after,live)
                    checks.append({'seconds':time.monotonic()-start,'foreign':foreign,'apps':apps,'owned_before':owned_before,'owned_after':owned_after,'identities':observations})
                    if foreign:reason='foreign GPU activity'
                    if time.monotonic()-start>1200:reason='timeout'
                    if reason:
                        stop_owned(process)
                        break
                    time.sleep(.2)
            finally:
                stop_owned(process)
                monitor.terminate()
                try:monitor.wait(timeout=10)
                except subprocess.TimeoutExpired:monitor.kill();monitor.wait(timeout=5)
            wall=time.monotonic()-start
        after=snapshot(args.gpu)
    (args.output/'after.json').write_text(json.dumps(after)+'\n')
    (args.output/'checks.json').write_text(json.dumps(checks)+'\n')
    record={'gpu':args.gpu,'command':command,'binary_sha256':hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest(),
            'child_pid':process.pid,'observer':'two-sided-starttime-v1','exit_code':process.returncode,'stop_reason':reason,'wall_s':wall,
            'runtime_valid':process.returncode==0 and reason is None and not after['apps']}
    (args.output/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if not record['runtime_valid']:raise SystemExit(1)


if __name__=='__main__':main()
