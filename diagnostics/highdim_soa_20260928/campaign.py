#!/usr/bin/env python3
"""Run held-out exact F versus tiled-SoA scans on 4090-left."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/ls/tmp/gts_highdim_soa_20260928')
REFERENCE=Path('/home/ls/tmp/gts_fixed_cutoff_holdout_20260927')
DATASETS=('GIST','Deep')


def setup():
    for dataset in DATASETS:
        path=ROOT/'data'/dataset/'1000000'
        fixture=path/'fixtures'
        fixture.mkdir(parents=True,exist_ok=True)
        (path/'runs').mkdir(exist_ok=True)
        reference=REFERENCE/'data'/dataset/'1000000/fixtures'
        for name in ('data.f32bin','queries.qid','oracle.json'):
            dst=fixture/name
            if not dst.exists():dst.symlink_to(reference/name)
        for gold in reference.glob('expected_*.json'):
            dst=fixture/gold.name
            if not dst.exists():dst.symlink_to(gold)
        binary=path/'bin'
        if not binary.exists():binary.symlink_to(ROOT/'bin',target_is_directory=True)


def run_one(dataset,kind,mode,label):
    path=ROOT/'data'/dataset/'1000000'
    radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
    if kind=='half':radius*=0.5
    assert kind in ('normal','half')
    base=label
    attempt=0
    while (path/'runs'/label).exists():
        previous=path/'runs'/label/'receipt.json'
        if previous.exists():
            old=json.loads(previous.read_text())
            if old['exit_code']==0 and old['validation']['pass'] and not old['stop_reason']:
                break
        attempt+=1
        label=f'{base}_retry{attempt}'
    else:
        command=['python3',str(ROOT/'run.py'),str(path),'--gpu','0',
                 '--label',label,'--mode',mode,'--radius',str(radius),
                 '--warmup','8','--repeats','1']
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        if result.returncode:
            print(result.stdout,result.stderr,flush=True)
            raise RuntimeError((dataset,label))
    folder=path/'runs'/label
    receipt=json.loads((folder/'receipt.json').read_text())
    assert receipt['exit_code']==0 and receipt['validation']['pass']
    assert not receipt['stop_reason'] and receipt['post_gpu_clear']
    assert not receipt['runtime_errors']
    rows=list(csv.DictReader((folder/'result.csv').open()))
    assert len(rows)==24
    mean_ms=sum(float(row['query_us']) for row in rows)/24000
    setup=json.loads((folder/'result.json').read_text()).get('setup_s')
    print(dataset,kind,mode,label,f'{mean_ms:.6f} ms','setup',setup,flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('setup','smoke','paired','half',
                                         'filter_smoke','filter_paired','filter_half'))
    phase=parser.parse_args().phase
    if phase=='setup':setup();return
    if phase=='smoke':
        for dataset in ('Deep','GIST'):
            for mode in ('F','S'):
                run_one(dataset,'normal',mode,f'normal_{mode.lower()}_0')
    elif phase=='paired':
        for round_index,order in enumerate((('S','F'),('F','S'),('S','F')),1):
            datasets=DATASETS if round_index%2 else DATASETS[::-1]
            for dataset in datasets:
                for mode in order:
                    run_one(dataset,'normal',mode,
                            f'normal_{mode.lower()}_{round_index}')
    elif phase=='half':
        for dataset in DATASETS:
            for mode in ('F','S'):
                run_one(dataset,'half',mode,f'half_{mode.lower()}_0')
    elif phase=='filter_smoke':
        for dataset in ('Deep','GIST'):
            run_one(dataset,'normal','M','normal_m_0')
    elif phase=='filter_paired':
        for round_index,order in enumerate((('M','F'),('F','M'),('M','F')),1):
            datasets=DATASETS if round_index%2 else DATASETS[::-1]
            for dataset in datasets:
                for mode in order:
                    run_one(dataset,'normal',mode,
                            f'normal_{mode.lower()}_{round_index}')
    elif phase=='filter_half':
        for dataset in DATASETS:
            for mode in ('F','M'):
                run_one(dataset,'half',mode,f'half_{mode.lower()}_0')


if __name__=='__main__':main()
