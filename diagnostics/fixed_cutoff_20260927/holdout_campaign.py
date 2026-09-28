#!/usr/bin/env python3
"""Test the fixed cutoff on unseen queries and half/double radii."""
import argparse
import csv
import json
import random
from pathlib import Path
import shutil
import subprocess

SOURCE=Path('/home/ls/tmp/gts_compact_cutoff_20260927')
ROOT=Path('/home/ls/tmp/gts_fixed_cutoff_holdout_20260927')
DATASETS=('GIST','Deep','Tloc')

def setup():
    ROOT.mkdir(parents=True,exist_ok=True)
    binary=ROOT/'bin'
    if not binary.exists():binary.symlink_to(SOURCE/'bin',target_is_directory=True)
    runner=ROOT/'run.py'
    if not runner.exists():shutil.copy2(SOURCE/'run.py',runner)
    old=(SOURCE/'data/GIST/1000000/fixtures/queries.qid').read_text().split()[1:]
    excluded={int(value) for value in old}
    rng=random.Random(240927)
    chosen=[]
    while len(chosen)<24:
        qid=rng.randrange(1000000)
        if qid not in excluded and qid not in chosen:chosen.append(qid)
    for dataset in DATASETS:
        path=ROOT/'data'/dataset/'1000000'
        fixture=path/'fixtures'
        fixture.mkdir(parents=True,exist_ok=True)
        (path/'runs').mkdir(exist_ok=True)
        link=path/'bin'
        if not link.exists():link.symlink_to(ROOT/'bin',target_is_directory=True)
        old_fixture=SOURCE/'data'/dataset/'1000000/fixtures'
        data=fixture/'data.f32bin'
        if not data.exists():data.symlink_to(old_fixture/'data.f32bin')
        (fixture/'queries.qid').write_text(str(len(chosen))+'\n'+'\n'.join(map(str,chosen))+'\n')
        shutil.copy2(old_fixture/'oracle.json',fixture/'oracle.json')
    print('holdout qids',chosen,flush=True)

def run_one(dataset,kind,mode,round_index=0,dump=False):
    path=ROOT/'data'/dataset/'1000000'
    radii=json.loads((path/'fixtures/oracle.json').read_text())['radii']
    radius=radii['normal']
    if kind=='half':radius*=0.5
    elif kind=='double':radius*=2.0
    elif kind=='quad':radius*=4.0
    elif kind=='oct':radius*=8.0
    elif kind=='x16':radius*=16.0
    elif kind=='x32':radius*=32.0
    elif kind=='x64':radius*=64.0
    elif kind=='all':radius=radii['all']
    assert kind in ('normal','half','double','quad','oct','x16','x32','x64','all')
    base=f'{kind}_{mode.lower()}_{round_index}'+('_dump' if dump else '')
    label=base
    attempt=0
    while (path/'runs'/label).exists():
        previous=path/'runs'/label/'receipt.json'
        if previous.exists():
            old=json.loads(previous.read_text())
            if old['exit_code']==0 and not old['stop_reason']:break
        attempt+=1
        label=f'{base}_retry{attempt}'
    else:
        cmd=['python3',str(ROOT/'run.py'),str(path),'--gpu','0','--label',label,
             '--mode',mode,'--radius',str(radius),'--warmup','8','--repeats','1']
        if dump:cmd.append('--dump')
        result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        if result.returncode:
            print(result.stdout,result.stderr,flush=True)
            raise RuntimeError(label)
    folder=path/'runs'/label
    receipt=json.loads((folder/'receipt.json').read_text())
    assert receipt['exit_code']==0 and not receipt['stop_reason']
    with (folder/'result.csv').open() as file:rows=list(csv.DictReader(file))
    assert len(rows)==24
    gold=path/'fixtures'/f'expected_{radius:g}.json'
    if mode=='F':
        expected={row['qid']:[int(row['count']),row['ordered_hash']] for row in rows}
        if not gold.exists():gold.write_text(json.dumps(expected,sort_keys=True,indent=2)+'\n')
        else:assert json.loads(gold.read_text())==expected,label
    else:assert receipt['validation']['pass'],label
    ms=sum(float(row['query_us']) for row in rows)/len(rows)/1000
    print(dataset,kind,mode,round_index,f'{ms:.6f} ms',flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('setup','normal','radius','paired_tloc','dump_tloc','wide_tloc','breakpoint_tloc','paired_wide'))
    args=parser.parse_args()
    if args.phase=='setup':setup();return
    if args.phase=='normal':
        for dataset in DATASETS:
            modes=('F','C1','C3') if dataset!='Tloc' else ('F','C1','C2','C3','C4','C5','J')
            for mode in modes:run_one(dataset,'normal',mode)
    elif args.phase=='radius':
        for dataset in DATASETS:
            kinds=('half',) if dataset!='Tloc' else ('half','double')
            modes=('F','C1','C3') if dataset!='Tloc' else ('F','C1','C2','C3','C4','C5','J')
            for kind in kinds:
                for mode in modes:run_one(dataset,kind,mode)
    elif args.phase=='paired_tloc':
        orders=(('C3','J','F'),('F','J','C3'),('J','C3','F'))
        for round_index,order in enumerate(orders,1):
            for mode in order:run_one('Tloc','normal',mode,round_index)
    elif args.phase=='dump_tloc':
        for kind in ('half','normal','double'):
            run_one('Tloc',kind,'C3',9,True)
    elif args.phase=='wide_tloc':
        for kind in ('quad','oct'):
            for mode in ('F','C2','C3','C4','J'):
                run_one('Tloc',kind,mode)
            run_one('Tloc',kind,'C3',9,True)
    elif args.phase=='breakpoint_tloc':
        for kind in ('x16','x32','x64','all'):
            for mode in ('F','C3','J'):
                run_one('Tloc',kind,mode)
            run_one('Tloc',kind,'C3',9,True)
    elif args.phase=='paired_wide':
        for round_index in range(1,6):
            kinds=('x64','all') if round_index%2 else ('all','x64')
            modes=('F','C3') if round_index%2 else ('C3','F')
            for kind in kinds:
                for mode in modes:run_one('Tloc',kind,mode,round_index)

if __name__=='__main__':main()
