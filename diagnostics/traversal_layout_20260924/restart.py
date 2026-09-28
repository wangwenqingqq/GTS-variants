#!/usr/bin/env python3
"""Start a fresh, fully repeated campaign from the interrupted pinned artifact."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('previous', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--gpu-index', type=int, required=True)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    old, root = a.previous.resolve(), a.output.resolve()
    assert not root.exists(), 'Fresh directory required; preserve every attempt'
    rec = json.loads((old/'preregistration.json').read_text())
    for name, digest in rec['generated_sha256'].items():
        assert sha(old/name) == digest, name
    for name, digest in json.loads((old/'source_pins.json').read_text()).items():
        assert sha(old/'source'/name.removeprefix('GTS/')) == digest, name
    for ds, pins in rec['fixture_sha256'].items():
        for name, digest in pins.items():
            assert sha(old/'data'/ds/'fixtures'/name) == digest, (ds, name)
    binary = sha(old/'bin/graph_bench')
    assert binary == '588a7d2a8690e1c724dc3825dd1b423e854003dc1001dadc405b347652634929'
    failed = json.loads((old/'data/Deep/runs/gate_memcheck_R/receipt.json').read_text())
    assert failed['stop_reason'] == 'foreign GPU activity'
    with open(f'/tmp/gtspp_gpu{a.gpu_index}.lock', 'r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def query(arg):
            return subprocess.check_output(['nvidia-smi', '-i', a.gpu, arg,
                                            '--format=csv,noheader'], text=True).strip()
        apps = query('--query-compute-apps=pid,process_name,used_memory')
        assert not apps, 'GPU occupied'
        state = query('--query-gpu=index,uuid,name,driver_version,compute_cap,power.limit')
        fields = state.split(', ')
        assert fields[:2] == [str(a.gpu_index), a.gpu]
        assert fields[3:] == ['590.48.01', '12.0', '600.00 W']
        root.mkdir()
        for name in rec['generated_sha256']:
            shutil.copy2(old/name, root/name)
        for name in ['preregistration.json', 'source_pins.json']:
            shutil.copy2(old/name, root/name)
        for name in ['source', 'bin', 'static']:
            shutil.copytree(old/name, root/name)
        (root/'logs').mkdir()
        for ds, pins in rec['fixture_sha256'].items():
            dest = root/'data'/ds/'fixtures'
            dest.mkdir(parents=True)
            for name in pins:
                shutil.copy2(old/'data'/ds/'fixtures'/name, dest/name)
            (dest.parent/'runs').mkdir()
            (dest.parent/'bin').symlink_to('../../bin')
        amendment = dict(
            recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reason='Original GPU 0 campaign stopped during Deep memcheck R on foreign GPU activity; no timing completed.',
            previous_root=str(old), previous_failed_receipt_sha256=sha(old/'data/Deep/runs/gate_memcheck_R/receipt.json'),
            gpu_index=a.gpu_index, gpu_uuid=a.gpu,
            policy='Fresh full/gates/stress/screen/sustained/trace on one idle device; no old observations pooled. Same binary, fixtures, code, orders and estimator.',
            binary_sha256=binary, production_promoted=False)
        (root/'amendment.json').write_text(json.dumps(amendment, indent=2)+'\n')
        admission = dict(utc=amendment['recorded_at_utc'], state=state, apps=apps,
                         clock_policy='unchanged/uncontrolled', cpu='shared/unpinned',
                         amendment_sha256=sha(root/'amendment.json'))
        (root/'logs/admission.json').write_text(json.dumps(admission, indent=2)+'\n')
    for cmd, name in [(['/usr/local/cuda-13.1/bin/nvcc', '--version'], 'toolkit.txt'),
                      (['nsys', '--version'], 'nsys_version.txt'),
                      (['compute-sanitizer', '--version'], 'sanitizer_version.txt')]:
        (root/'logs'/name).write_text(subprocess.check_output(cmd, text=True))
    shutil.copy2(old/'logs/build.txt', root/'logs/build.txt')
    env = {**os.environ, 'PATH': '/usr/local/cuda-13.1/bin:'+os.environ['PATH']}
    for stage in ['full', 'gates', 'stress', 'screen', 'sustained', 'trace']:
        print('START', stage, datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
        with (root/'logs'/f'{stage}.txt').open('w') as out:
            subprocess.run(['python3', str(root/'suite.py'), str(root), stage,
                            '--gpu', a.gpu, '--gpu-index', str(a.gpu_index)],
                           env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        print('DONE', stage, datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)


if __name__ == '__main__':
    main()
