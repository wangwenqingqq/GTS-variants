#!/usr/bin/env python3
"""Run one batch condition under the existing GPU admission lock."""
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
    owned = {pid}
    pending = [pid]
    while pending:
        parent = pending.pop()
        for children in Path(f'/proc/{parent}/task').glob('*/children'):
            try:
                found = [int(x) for x in children.read_text().split()]
            except (FileNotFoundError, ProcessLookupError):
                continue
            for child in found:
                if child not in owned:
                    owned.add(child)
                    pending.append(child)
    return owned


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    p.add_argument('data', type=Path)
    p.add_argument('idlist', type=Path)
    p.add_argument('measured', type=Path)
    p.add_argument('warmup', type=Path)
    p.add_argument('mode')
    p.add_argument('radius')
    p.add_argument('batch', type=int)
    p.add_argument('tile', type=int)
    p.add_argument('output', type=Path)
    p.add_argument('--gpu', required=True)
    p.add_argument('--reverse', action='store_true')
    p.add_argument('--dump', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    for key in ('binary', 'data', 'idlist', 'measured', 'warmup'):
        setattr(a, key, getattr(a, key).resolve())
    radius = a.radius
    if radius.startswith('@'):
        radius = '@' + str(Path(radius[1:]).resolve())
    before = snapshot(a.gpu)
    index = before['device'].split(',')[0].strip()
    if before['apps']:
        raise RuntimeError('GPU occupied before admission')
    cmd = ['numactl', '--cpunodebind=3', '--membind=3', str(a.binary),
           str(a.data), str(a.idlist), str(a.measured), str(a.warmup),
           a.mode, radius, str(a.batch), str(a.tile), str(int(a.reverse)),
           str(a.output / 'result'), str(int(a.dump))]
    (a.output / 'command.json').write_text(json.dumps(cmd) + '\n')
    (a.output / 'before.json').write_text(json.dumps(before) + '\n')
    reason = None
    checks = []
    with open(f'/tmp/gtspp_gpu{index}.lock', 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if snapshot(a.gpu)['apps']:
            raise RuntimeError('GPU occupied after lock')
        with (a.output / 'stdout.log').open('w') as out, \
             (a.output / 'stderr.log').open('w') as err, \
             (a.output / 'gpu.csv').open('w') as gpu_log:
            monitor = subprocess.Popen(
                ['nvidia-smi', '-i', a.gpu,
                 '--query-gpu=timestamp,memory.used,utilization.gpu,power.draw',
                 '--format=csv,noheader,nounits', '-lms', '200'],
                stdout=gpu_log, stderr=err)
            start = time.monotonic()
            proc = subprocess.Popen(cmd, env={**os.environ, 'CUDA_VISIBLE_DEVICES': a.gpu},
                                    stdout=out, stderr=err, start_new_session=True)
            try:
                while proc.poll() is None:
                    apps = snapshot(a.gpu)['apps']
                    owned = descendants(proc.pid)
                    foreign = [line for line in apps.splitlines()
                               if int(line.split(',')[0]) not in owned]
                    checks.append({'seconds': time.monotonic()-start, 'foreign': foreign})
                    if foreign:
                        reason = 'foreign GPU activity'
                    if time.monotonic()-start > 600:
                        reason = 'timeout'
                    if reason:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                        break
                    time.sleep(0.2)
            finally:
                monitor.terminate()
                monitor.wait(timeout=10)
            wall = time.monotonic()-start
        after = snapshot(a.gpu)
    (a.output / 'after.json').write_text(json.dumps(after) + '\n')
    (a.output / 'checks.json').write_text(json.dumps(checks) + '\n')
    record = {'mode': a.mode, 'batch': a.batch, 'tile': a.tile,
              'gpu': a.gpu, 'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
              'exit_code': proc.returncode, 'stop_reason': reason, 'wall_s': wall,
              'runtime_valid': proc.returncode == 0 and reason is None and not after['apps']}
    (a.output / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    if not record['runtime_valid']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
