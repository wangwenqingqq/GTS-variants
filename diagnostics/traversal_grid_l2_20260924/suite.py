#!/usr/bin/env python3
"""Fail-closed three-mode, million-point traversal screen."""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
from pathlib import Path

import numpy as np

from verify import check, clean, read, sha
from run import execute, snapshot

DATASETS = ('GIST', 'Deep', 'Tloc')
ORDERS = ('ESP', 'PSE', 'SPE', 'EPS')

def rows(stage, root):
    for d in DATASETS:
        path = root/'data'/d/'1000000'
        radius = read(path/'fixtures/oracle.json')['radii']['normal']
        if stage == 'full':
            for m in 'SP':
                yield path, f'full_normal_{m}', m, radius, 1, 0, 'clean', True, 'queries.qid'
        elif stage == 'gates':
            for tool in ('memcheck', 'synccheck'):
                for m in 'SP':
                    yield path, f'gate_{tool}_{m}', m, radius, 1, 0, tool, False, 'check.qid'
        elif stage == 'timing':
            for i, order in enumerate(ORDERS):
                for m in order:
                    yield path, f'timing_{i}_{m}', m, radius, 1, 8, 'clean', False, 'queries.qid'
        elif stage == 'trace':
            for m in 'ESP':
                yield path, f'trace_{m}', m, radius, 1, 2, 'nsys', False, 'trace.qid'
        else:
            raise ValueError(stage)

def stage_rows(stage, root):
    if stage != 'timing':
        yield from rows(stage, root)
    else:
        for i, order in enumerate(ORDERS):
            datasets = DATASETS if i % 2 == 0 else DATASETS[::-1]
            for d in datasets:
                path = root/'data'/d/'1000000'
                radius = read(path/'fixtures/oracle.json')['radii']['normal']
                for m in order:
                    yield path, f'timing_{i}_{m}', m, radius, 1, 8, 'clean', False, 'queries.qid'

def validate_full(root):
    for d in DATASETS:
        path = root/'data'/d/'1000000'
        meta = read(path/'fixtures/oracle.json')
        matrix = np.load(path/'fixtures/oracle.npy', mmap_mode='r')
        gold = read(path/'fixtures'/f"expected_{meta['radii']['normal']:g}.json")
        for mode in 'SP':
            got, band = check(path, f'full_normal_{mode}', mode, 'normal', meta, matrix)
            assert all(gold[str(q)] == [count, fnv] for q, count, _, fnv in got), (d, mode)
            print('CPU/full PASS', d, mode, 'boundary', band, flush=True)

def validate_run(path, label, mode, tool, binary_hash, runner_hash):
    run=path/'runs'/label
    receipt=read(run/'receipt.json')
    clean(receipt)
    assert receipt['validation']['pass'] and receipt['mode']==mode and receipt['tool']==tool
    assert receipt['binary_sha256']==binary_hash and receipt['runner_sha256']==runner_hash
    assert not read(run/'before.json')['apps'].strip()
    assert not read(run/'after.json')['apps'].strip()
    assert all(not item['foreign'] for item in read(run/'checks.json'))
    if tool in ('memcheck','synccheck'):
        log=(run/'stdout.log').read_text()+(run/'stderr.log').read_text()
        assert 'ERROR SUMMARY: 0 errors' in log, (path,label)

def main(root, gpu, index):
    root=root.resolve()
    binary_hash=sha(root/'bin/graph_bench')
    runner_hash=sha(root/'run.py')
    assert binary_hash==read(root/'manifest.json')['binary_sha256']
    assert runner_hash==read(root/'manifest.json')['runner_sha256']
    for d in DATASETS:
        p=root/'data'/d/'1000000'
        assert sha(p/'fixtures/oracle.json')==read(root/'manifest.json')['oracle_sha256'][d]
    with open(f'/tmp/gtspp_gpu{index}.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=snapshot(gpu)
        assert not state['apps'].strip() and state['gpu'].split(',')[0].strip()==str(index)
        assert state['gpu'].split(',')[1].strip()==gpu
        (root/'logs/admission.json').write_text(json.dumps({'gpu_index':index,'gpu_uuid':gpu,'state':state},indent=2)+'\n')
        for stage in ('full','gates','timing','trace'):
            print('START',stage,dt.datetime.now(dt.timezone.utc).isoformat(),flush=True)
            with (root/'logs'/f'{stage}.txt').open('x') as output:
                with contextlib.redirect_stdout(output):
                    for path,label,mode,radius,repeats,warmup,tool,dump,qfile in stage_rows(stage,root):
                        assert execute(path,gpu,label,mode,radius,repeats,warmup,tool,dump,qfile), (path,label)
                        validate_run(path,label,mode,tool,binary_hash,runner_hash)
                    if stage=='full': validate_full(root)
            print('DONE',stage,dt.datetime.now(dt.timezone.utc).isoformat(),flush=True)
        (root/'logs/COMPLETE.json').write_text(json.dumps({'runs':6+12+36+9})+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    parser.add_argument('--gpu',required=True);parser.add_argument('--index',required=True,type=int)
    args=parser.parse_args();main(args.root,args.gpu,args.index)
