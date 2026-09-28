#!/usr/bin/env python3
"""Audit held-out F/S/M result hashes and paired timings."""
import csv
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
RAW=HERE/'local/data'
DATASETS=('GIST','Deep')


def run(dataset,label):
    path=RAW/dataset/'1000000/runs'/label
    receipt=json.loads((path/'receipt.json').read_text())
    assert receipt['exit_code']==0 and receipt['validation']['pass']
    assert not receipt['stop_reason'] and receipt['post_gpu_clear']
    assert not receipt['runtime_errors']
    assert receipt['warmup']==8 and receipt['repeats']==1
    rows=list(csv.DictReader((path/'result.csv').open()))
    assert len(rows)==24
    result=json.loads((path/'result.json').read_text())
    ms=statistics.mean(float(row['query_us']) for row in rows)/1000
    return receipt,rows,result,ms


def same_answers(a,b):
    return all((x['qid'],x['count'],x['ordered_hash'])==
               (y['qid'],y['count'],y['ordered_hash'])
               for x,y in zip(a,b))


def main():
    evidence={'host':'4090-left','gpu':'NVIDIA GeForce RTX 4090',
              'n':1000000,'queries':24,'warmup':8,
              'input_sha256':{},'soa_screen':{},'paired':{},'half_screen':{}}
    main_hashes=set()
    soa_hashes=set()
    for dataset in DATASETS:
        f0,frows,_,fms=run(dataset,'normal_f_0')
        s0,srows,_,sms=run(dataset,'normal_s_0')
        assert same_answers(frows,srows)
        soa_hashes.update((f0['binary_sha256'],s0['binary_sha256']))
        evidence['soa_screen'][dataset]={'F_ms':fms,'S_ms':sms}
        evidence['input_sha256'][dataset]=f0['input_sha256']
        evidence['paired'][dataset]={}
        f_times=[];m_times=[];ratios=[];query_wins=[]
        for i in range(1,4):
            f,fr,_,fm=run(dataset,f'normal_f_{i}')
            m,mr,_,mm=run(dataset,f'normal_m_{i}')
            assert same_answers(fr,mr)
            assert f['radius']==m['radius']
            main_hashes.update((f['binary_sha256'],m['binary_sha256']))
            f_times.append(fm);m_times.append(mm);ratios.append(fm/mm)
            query_wins.append(sum(float(x['query_us'])>float(y['query_us'])
                                  for x,y in zip(fr,mr)))
        evidence['paired'][dataset]={
            'F_round_ms':f_times,'M_round_ms':m_times,
            'F_over_M_round':ratios,
            'F_median_ms':statistics.median(f_times),
            'M_median_ms':statistics.median(m_times),
            'median_speedup':statistics.median(ratios),
            'M_wins_rounds':sum(x>1 for x in ratios),
            'M_wins_queries_per_round':query_wins}
        f,fr,_,fm=run(dataset,'half_f_0')
        m,mr,_,mm=run(dataset,'half_m_0')
        assert same_answers(fr,mr)
        main_hashes.update((f['binary_sha256'],m['binary_sha256']))
        evidence['half_screen'][dataset]={
            'F_ms':fm,'M_ms':mm,'speedup':fm/mm,
            'M_wins_queries':sum(float(x['query_us'])>float(y['query_us'])
                                 for x,y in zip(fr,mr))}
        smoke_label='normal_m_0' if dataset=='Deep' else 'normal_m_0_retry1'
        smoke,smoke_rows,_,_=run(dataset,smoke_label)
        assert same_answers(frows,smoke_rows)
        main_hashes.add(smoke['binary_sha256'])
    assert len(main_hashes)==1 and len(soa_hashes)==1
    evidence['binary_sha256']=main_hashes.pop()
    evidence['soa_screen_binary_sha256']=soa_hashes.pop()
    failed=json.loads((RAW/'GIST/1000000/runs/normal_m_0/receipt.json').read_text())
    assert failed['stop_reason']=='foreign GPU activity' and failed['exit_code']!=0
    evidence['excluded_run']={'dataset':'GIST','label':'normal_m_0',
                              'reason':failed['stop_reason']}
    evidence['validated_runs']=22
    (HERE/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    for dataset in DATASETS:
        print(dataset,'normal paired speedup',evidence['paired'][dataset]['median_speedup'],
              'half screen speedup',evidence['half_screen'][dataset]['speedup'])
    print('Audited 22 valid runs; excluded one interrupted run')


if __name__=='__main__':main()
