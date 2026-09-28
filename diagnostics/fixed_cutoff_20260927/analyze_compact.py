#!/usr/bin/env python3
"""Audit the exact compact-frontier screen and paired repetitions."""
import csv
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
RAW=HERE/'local/compact_artifacts/data'
DATASETS=('GIST','Deep','Tloc')
SCREEN_MODES=('F','C1','C2','C3','C4','C5','J')
PAIRED_MODES={'GIST':('F','C1'),'Deep':('F','C1'),
              'Tloc':('F','C2','C3','C4','J')}

def run_dir(dataset,label):
    return RAW/dataset/'1000000/runs'/label

def read_run(dataset,label):
    path=run_dir(dataset,label)
    receipt=json.loads((path/'receipt.json').read_text())
    assert receipt['exit_code']==0 and receipt['validation']['pass']
    assert not receipt['stop_reason'] and receipt['post_gpu_clear']
    assert not receipt['runtime_errors']
    rows=list(csv.DictReader((path/'result.csv').open()))
    assert len(rows)==receipt['validation']['rows']
    ms=sum(float(row['query_us']) for row in rows)/len(rows)/1000
    return receipt,ms

def main():
    receipts=[]
    for dataset in DATASETS:
        for path in (RAW/dataset/'1000000/runs').glob('*/receipt.json'):
            record=json.loads(path.read_text())
            assert record['exit_code']==0 and record['validation']['pass']
            assert not record['stop_reason'] and record['post_gpu_clear']
            assert not record['runtime_errors']
            receipts.append(record)
    assert len(receipts)==67
    binaries={record['binary_sha256'] for record in receipts}
    assert len(binaries)==1
    evidence={'host':'4090-left','gpu':'NVIDIA GeForce RTX 4090',
              'n':1000000,'binary_sha256':next(iter(binaries)),
              'validated_runs':len(receipts),'screen':{},'paired':{},
              'dataset_input_sha256':{}}
    for dataset in DATASETS:
        evidence['screen'][dataset]={}
        for mode in SCREEN_MODES:
            receipt,ms=read_run(dataset,f'screen_{dataset.lower()}_{mode.lower()}')
            evidence['screen'][dataset][mode]=ms
            evidence['dataset_input_sha256'][dataset]=receipt['input_sha256']
        evidence['paired'][dataset]={}
        rounds=5 if dataset=='Tloc' else 3
        for mode in PAIRED_MODES[dataset]:
            values=[read_run(dataset,f'paired_{i}_{dataset.lower()}_{mode.lower()}')[1]
                    for i in range(rounds)]
            evidence['paired'][dataset][mode]={'round_ms':values,
                                               'median_ms':statistics.median(values)}
    for mode in ('F','J'):
        numerator=[read_run('Tloc',f'paired_{i}_tloc_{mode.lower()}')[1] for i in range(5)]
        denominator=[read_run('Tloc',f'paired_{i}_tloc_c3')[1] for i in range(5)]
        ratios=[a/b for a,b in zip(numerator,denominator)]
        evidence['paired']['Tloc'][mode+'/C3']={
            'round_ratios':ratios,'median_ratio':statistics.median(ratios),
            'wins':sum(x>1 for x in ratios)}
    for dataset in ('GIST','Deep'):
        numerator=[read_run(dataset,f'paired_{i}_{dataset.lower()}_c1')[1] for i in range(3)]
        denominator=[read_run(dataset,f'paired_{i}_{dataset.lower()}_f')[1] for i in range(3)]
        ratios=[a/b for a,b in zip(numerator,denominator)]
        evidence['paired'][dataset]['C1/F']={
            'round_ratios':ratios,'median_ratio':statistics.median(ratios),
            'wins':sum(x>1 for x in ratios)}
    frontier=run_dir('Tloc','frontier_tloc_c3')/'result.work.csv'
    counts=[int(row['candidates']) for row in csv.DictReader(frontier.open())]
    assert len(counts)==8
    evidence['tloc_c3_candidates']={'per_query':counts,'min':min(counts),
        'max':max(counts),'mean':statistics.mean(counts)}
    boundary={}
    for dataset,kind,tool,suffix in (
        ('Tloc','zero','clean',''),('Tloc','all','clean',''),
        ('Tloc','empty','clean',''),('GIST','zero','clean',''),
        ('GIST','empty','clean',''),('Tloc','normal','memcheck','_retry1'),
        ('Tloc','normal','synccheck','')):
        label=f'boundary_{dataset.lower()}_{kind}_{tool}{suffix}'
        receipt,_=read_run(dataset,label)
        assert receipt['tool']==tool
        if tool!='clean':
            assert 'ERROR SUMMARY: 0 errors' in (run_dir(dataset,label)/'stdout.log').read_text()
        boundary[label]='pass'
    evidence['boundary_and_sanitizer']=boundary
    (HERE/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('Validated',len(receipts),'runs; binary',next(iter(binaries)))

if __name__=='__main__':main()
