#!/usr/bin/env python3
"""Audit 4090-left receipts and summarize paired F/PCA query latency."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOCAL=HERE/'local'
MODES=('F','P32','P64')
DATASETS=('GIST','Deep')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_run(ds,label):
    path=LOCAL/'data'/ds/'1000000'/'runs'/label
    receipt=json.loads((path/'receipt.json').read_text())
    assert receipt['exit_code']==0 and receipt['stop_reason'] is None
    assert receipt['post_gpu_clear'] and not receipt['runtime_errors']
    assert receipt['validation']['pass']
    before=json.loads((path/'before.json').read_text())
    after=json.loads((path/'after.json').read_text())
    checks=json.loads((path/'checks.json').read_text())
    assert not before['apps'].strip() and not after['apps'].strip()
    assert all(not x['foreign'] for x in checks)
    rows=list(csv.DictReader((path/'result.csv').open()))
    summary=json.loads((path/'result.json').read_text())
    assert len(rows)==receipt['validation']['rows']
    return receipt,rows,summary

def main():
    complete=json.loads((LOCAL/'logs/timing_COMPLETE.json').read_text())
    assert len(complete['runs'])==24
    evidence={'host':'4090-left','gpu':'NVIDIA GeForce RTX 4090',
              'metric':'mean of eight complete host-ready queries per process; median across four processes',
              'warmup_queries_per_process':8,'measured_queries_per_process':8,
              'rounds':4,'datasets':{},'binary_sha256':None,
              'validation':{'timing_runs':24,'all_timing_receipts_pass':True,
                            'all_round_results_identical':True,'no_foreign_gpu_apps':True}}
    for ds in DATASETS:
        build=json.loads((LOCAL/'projection'/f'BUILD_{ds}.json').read_text())['datasets'][ds]
        runs={mode:[] for mode in MODES}
        for round_id in range(4):
            round_hashes=[]
            for mode in MODES:
                label=f'timing_{round_id}_{mode}'
                receipt,rows,summary=load_run(ds,label)
                assert receipt['mode']==mode and len(rows)==8
                if evidence['binary_sha256'] is None:evidence['binary_sha256']=receipt['binary_sha256']
                assert evidence['binary_sha256']==receipt['binary_sha256']
                round_hashes.append([(x['qid'],x['count'],x['ordered_hash']) for x in rows])
                runs[mode].append({'round':round_id,
                    'mean_ms':sum(float(x['query_us']) for x in rows)/8000,
                    'setup_s':summary['setup_s'],
                    'process_before_cleanup_s':summary['before_cleanup_process_s'],
                    'receipt_sha256':sha(LOCAL/'data'/ds/'1000000'/'runs'/label/'receipt.json')})
            assert round_hashes[0]==round_hashes[1]==round_hashes[2]
        stats={}
        for mode,values in runs.items():
            stats[mode]={'rounds':values,
                         'median_ms':statistics.median(x['mean_ms'] for x in values),
                         'median_setup_s':statistics.median(x['setup_s'] for x in values),
                         'median_process_before_cleanup_s':statistics.median(
                             x['process_before_cleanup_s'] for x in values)}
        for mode in ('P32','P64'):
            ratios=[f['mean_ms']/p['mean_ms'] for f,p in zip(runs['F'],runs[mode])]
            stats[mode]['paired_speedups']=ratios
            stats[mode]['median_paired_speedup']=statistics.median(ratios)
            stats[mode]['wins']=sum(x>1 for x in ratios)
        build_s=build['build_seconds']
        extra_setup=max(stats['P64']['median_setup_s']-stats['F']['median_setup_s'],0)
        saved_s=(stats['F']['median_ms']-stats['P64']['median_ms'])/1000
        approx_break_even=(build_s+extra_setup)/saved_s
        evidence['datasets'][ds]={'modes':stats,'projection_build':build,
                                  'p64_extra_setup_s':extra_setup,
                                  'p64_approx_break_even_queries':approx_break_even}
    special={}
    for ds,labels in {'Deep':('deep_P64_zero','deep_P64_all','deep_P64_empty',
                              'deep_P64_memcheck','deep_P64_synccheck'),
                      'GIST':('gist_P64_memcheck','gist_P64_synccheck')}.items():
        for label in labels:
            receipt,rows,_=load_run(ds,label)
            special[label]={'pass':receipt['validation']['pass'],'rows':len(rows),
                            'tool':receipt['tool'],'receipt_sha256':sha(
                                LOCAL/'data'/ds/'1000000'/'runs'/label/'receipt.json')}
    evidence['validation']['special']=special
    (HERE/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    for ds,x in evidence['datasets'].items():
        modes=x['modes']
        print(ds,[(m,round(modes[m]['median_ms'],3)) for m in MODES],
              'F/P64',round(modes['P64']['median_paired_speedup'],3),
              'break_even_queries',round(x['p64_approx_break_even_queries']))

if __name__=='__main__':main()
