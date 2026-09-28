#!/usr/bin/env python3
"""Five-mode large-L2 campaign; no timing until all new gates pass."""
import argparse
import contextlib
import datetime
import fcntl
import json
import sys
from pathlib import Path

import numpy as np
from verify import check, clean, read, sha

DATASETS = ('GIST', 'Deep', 'Tloc')
SIZES = (65536, 1000000)
STAGES = ('full', 'gates', 'stress', 'timing', 'sustained', 'trace')
ORDERS = ('ABCDE', 'EDCBA', 'CDEAB', 'BAEDC')


def rows(stage, root):
    # dataset, N, label, mode, radius, repeats, warmup, tool, dump, qfile
    def row(d, n, label, mode, radius, reps=1, warm=0, tool='clean', dump=False, qfile='queries.qid'):
        return d, n, label, mode, radius, reps, warm, tool, dump, qfile
    out = []
    if stage == 'full':
        for d in DATASETS:
            for n in SIZES:
                radii = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']
                out.extend(row(d, n, f'full_normal_{m}', m, radii['normal'], dump=True) for m in 'BD')
                if n == 1000000:
                    for name, qfile in (('zero', 'zero.qid'), ('all', 'all.qid'), ('empty', 'negative.qid')):
                        out.extend(row(d, n, f'full_{name}_{m}', m, radii[name], dump=True, qfile=qfile) for m in 'BD')
    elif stage == 'gates':
        for d in DATASETS:
            for n in SIZES:
                radius = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                out.extend(row(d, n, f'gate_{tool}_{m}', m, radius, tool=tool, qfile='check.qid')
                           for tool in ('memcheck', 'synccheck') for m in 'BD')
                if n == 1000000:
                    out.extend(row(d, n, f'gate_{tool}_D', 'D', radius, tool=tool, qfile='check.qid')
                               for tool in ('initcheck', 'racecheck'))
    elif stage == 'stress':
        for d in DATASETS:
            for n in SIZES:
                radius = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                out.extend(row(d, n, f'stress_{m}', m, radius, reps=2, warm=8) for m in 'BD')
    elif stage == 'timing':
        for i, order in enumerate(ORDERS):
            ds = DATASETS if i % 2 == 0 else DATASETS[::-1]
            ns = SIZES if i % 2 == 0 else SIZES[::-1]
            for d in ds:
                for n in ns:
                    radius = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                    out.extend(row(d, n, f'timing_{i}_{m}', m, radius,
                                   reps=4 if n == 65536 else 1, warm=16 if n == 65536 else 8)
                               for m in order)
    elif stage == 'sustained':
        for i, order in enumerate((ORDERS[0], ORDERS[1])):
            ds = DATASETS if i == 0 else DATASETS[::-1]
            ns = SIZES if i == 0 else SIZES[::-1]
            for d in ds:
                for n in ns:
                    radius = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                    out.extend(row(d, n, f'sustained_{i}_{m}', m, radius,
                                   reps=8 if n == 65536 else 2, warm=16 if n == 65536 else 8)
                               for m in order)
    elif stage == 'trace':
        for d in DATASETS:
            for n in SIZES:
                radius = read(root/'data'/d/str(n)/'fixtures/oracle.json')['radii']['normal']
                out.extend(row(d, n, f'nsys_{m}', m, radius, warm=2, tool='nsys', qfile='trace.qid') for m in 'BD')
    else:
        raise ValueError(stage)
    return out


def verify_stage(root, stage):
    for d, n, label, mode, radius, reps, warm, tool, dump, qfile in rows(stage, root):
        path = root/'data'/d/str(n)/'runs'/label
        receipt = read(path/'receipt.json')
        clean(receipt)
        assert (receipt['mode'], receipt['radius'], receipt['repeats'], receipt['warmup'],
                receipt['tool'], receipt['dump'], receipt['qfile'], receipt['binary']) == (
                mode, radius, reps, warm, tool, dump, qfile, 'graph_bench'), (d, n, label)
        assert receipt['validation']['pass'], (d, n, label)
        assert receipt['binary_sha256'] == sha(root/'bin/graph_bench')
        assert receipt['runner_sha256'] == sha(root/'run.py')
        if tool in ('memcheck', 'synccheck', 'initcheck', 'racecheck'):
            logs = (path/'stdout.log').read_text() + (path/'stderr.log').read_text()
            phrase = 'RACECHECK SUMMARY: 0 hazards' if tool == 'racecheck' else 'ERROR SUMMARY: 0 errors'
            assert phrase in logs, (d, n, label)


def verify_full(root):
    for d in DATASETS:
        for n in SIZES:
            path = root/'data'/d/str(n)
            meta = read(path/'fixtures/oracle.json')
            matrix = np.load(path/'fixtures/oracle.npy', mmap_mode='r')
            checked = {}
            for name in ('normal', 'zero', 'all', 'empty') if n == 1000000 else ('normal',):
                for mode in 'BD':
                    label = f'full_{name}_{mode}'
                    got, band = check(path, label, mode, name, meta, matrix)
                    gold = read(path/'fixtures'/f"expected_{meta['radii'][name]:g}.json")
                    assert all(gold[str(q)] == [count, fnv] for q, count, _, fnv in got), (d, n, label)
                    checked[label] = {'output_sha256': sha(path/'runs'/label/'result.results'),
                                      'normal_boundary_count': band if name == 'normal' else None}
            (path/'full_verified_new.json').write_text(json.dumps(checked, indent=2)+'\n')
            print(d, n, 'PASS full', len(checked), flush=True)


def main(root, gpu, index):
    sys.path.insert(0, str(root))
    from run import execute, snapshot
    with open(f'/tmp/gtspp_gpu{index}.lock', 'r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = snapshot(gpu)
        assert not state['apps'].strip()
        assert state['gpu'].split(',')[0].strip() == str(index)
        assert state['gpu'].split(',')[1].strip() == gpu
        (root/'logs/admission.json').write_text(json.dumps({
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'state': state, 'gpu_index': index}, indent=2)+'\n')
        assert sum(len(rows(stage, root)) for stage in STAGES) == 264
        for stage in STAGES:
            print('START', stage, datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
            with (root/'logs'/f'{stage}.txt').open('x') as out:
                with contextlib.redirect_stdout(out):
                    for d, n, label, mode, radius, reps, warm, tool, dump, qfile in rows(stage, root):
                        assert execute(root/'data'/d/str(n), gpu, label, mode, radius,
                                       reps, warm, tool, dump, qfile), (d, n, label)
                    if stage == 'full':
                        verify_full(root)
                    verify_stage(root, stage)
            print('DONE', stage, datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
        (root/'logs/COMPLETE.json').write_text(json.dumps({
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'runs': 264})+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--gpu', required=True)
    parser.add_argument('--index', type=int, required=True)
    args = parser.parse_args()
    main(args.root.resolve(), args.gpu, args.index)
