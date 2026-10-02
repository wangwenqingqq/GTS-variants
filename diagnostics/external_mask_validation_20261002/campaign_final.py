#!/usr/bin/env python3
"""P5 fresh-query oracle, complete-output audit, and rotated formal rounds."""
import csv
import filecmp
import json
import math
import os
from pathlib import Path
import statistics
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
P4=Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
P0=Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
BASE=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
MODES=('SCAN_L','SCAN_E','C_MASK_E','LIB64_U','LIB64_X','LIB32_U')
WORK=(('GIST','half','0x3f34a3d8',4),('GIST','normal','0x3fb4a3d8',4),
      ('GIST','all','0x41cb7260',4),('Deep','normal','0x3f8a3818',1))


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def execute(label,command):
    folder=ROOT/'runs'/label
    if not folder.exists():
        subprocess.run([sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,
                        '--output',str(folder),'--',*map(str,command)],
                       check=True,stdout=subprocess.DEVNULL,env=os.environ)
    receipt=json.loads((folder/'receipt.json').read_text())
    assert receipt['runtime_valid'],label
    return folder,receipt


def oracle(dataset,radius,bits):
    return ROOT/'runs'/f'oracle_p5_{dataset.lower()}_{radius}'


def expected_rows(dataset,radius,bits):
    folder=oracle(dataset,radius,bits)
    result=rows(folder/'result.csv')
    assert len(result)==1024
    expected=[(int(r['qid']),int(r['count']),int(r['ordered_hash'])) for r in result]
    if radius=='all':assert all(r[1]==1000000 for r in expected)
    return expected


def make_oracles():
    for dataset,radius,bits,_ in WORK:
        folder=oracle(dataset,radius,bits)
        data=BASE/f'data/{dataset}/1000000/fixtures/data.f32bin'
        qids=ROOT/'fixtures'/f'{dataset}_p5_final1024.qid'
        value=struct.unpack('<f',struct.pack('<I',int(bits,16)))[0]
        binary=BASE/f'data/{dataset}/1000000/bin/graph_bench_strict'
        output=folder/'result'
        execute(folder.name,[binary,data,qids,'FR',repr(value),'1','8',output,
                             '0' if radius=='all' else '1'])
        expected=expected_rows(dataset,radius,bits)
        print('ORACLE',dataset,radius,sum(x[1] for x in expected),flush=True)


def command(dataset,radius,bits,depth,b,mode,reverse,output,dump,config):
    data=BASE/f'data/{dataset}/1000000/fixtures/data.f32bin'
    order=BASE/f'reference_v2/{dataset}_idlist.i32'
    index=BASE/f'replay/{dataset}_index.bin'
    qids=ROOT/'fixtures'/f'{dataset}_p5_final1024.qid'
    warm=P0/'fixtures'/f'{dataset}_dev256.qid'
    if mode.startswith('LIB'):
        chunk=config[f'{dataset}:{b}:{mode}']
        return [ROOT/'p5_external',data,order,qids,warm,mode,bits,b,2,int(reverse),
                output,int(dump),chunk]
    return [P4/'bin/p4_bench_v3',data,order,qids,warm,mode,bits,b,2,int(reverse),
            output,int(dump),index,depth]


def audit(config):
    output=[]
    for dataset,radius,bits,depth in WORK:
        expected=expected_rows(dataset,radius,bits)
        reference=oracle(dataset,radius,bits)/'result.bin'
        for mode in MODES:
            name=f'audit_p5_{dataset.lower()}_{radius}_b32_{mode}'
            folder=ROOT/'runs'/name
            binary=radius!='all'
            execute(name,command(dataset,radius,bits,depth,32,mode,False,
                                 folder/'result',binary,config))
            got=rows(folder/'result_queries.csv')
            assert len(got)==1024
            entries=[(int(r['qid']),int(r['count']),int(r['ordered_hash'])) for r in got]
            count_diff=sum(x[1]!=y[1] for x,y in zip(expected,entries))
            hash_diff=sum(x[2]!=y[2] for x,y in zip(expected,entries))
            assert all(x[0]==y[0] for x,y in zip(expected,entries))
            if mode in ('SCAN_L','SCAN_E','C_MASK_E'):
                assert count_diff==hash_diff==0,name
            qualification={'qualification':'NOT_FIELD_AUDITED_ALL_RADIUS',
                           'queries':1024,'count_mismatch_queries':count_diff,
                           'hash_mismatch_queries':hash_diff}
            if binary:
                if mode in ('SCAN_L','SCAN_E','C_MASK_E'):
                    assert filecmp.cmp(reference,folder/'result.bin',shallow=False),name
                result=subprocess.check_output([sys.executable,str(ROOT/'compare_outputs.py'),
                                                str(reference),str(folder/'result.bin')],text=True)
                qualification=json.loads(result)
                (folder/'qualification.json').write_text(result)
                (folder/'result.bin').unlink()
            output.append((dataset,radius,mode,qualification['qualification'],
                           qualification.get('false_negatives',''),
                           qualification.get('false_positives',''),
                           qualification.get('bitwise_field_mismatches',''),
                           qualification.get('tolerance_field_mismatches',''),
                           count_diff,hash_diff))
            print('AUDIT',dataset,radius,mode,qualification['qualification'],
                  count_diff,hash_diff,flush=True)
    with (ROOT/'numerical_qualification.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('dataset','radius','mode','qualification',
                                    'false_negatives','false_positives',
                                    'bitwise_field_mismatches','tolerance_field_mismatches',
                                    'count_mismatch_queries','hash_mismatch_queries'))
        w.writerows(output)


def formal(config):
    result_path=ROOT/'latency_final.csv'
    with result_path.open('w') as f:
        writer=csv.writer(f)
        writer.writerow(('round','dataset','radius','B','mode','host_total_ms','gpu_total_ms',
                         'batch_p50_ms','batch_p95_ms','amortized_ms_per_query','qps',
                         'hits','d2h_bytes','count_mismatch_queries','hash_mismatch_queries',
                         'binary_sha256'))
        for round_no in range(1,7):
            workloads=[(dataset,radius,bits,depth,b)
                       for dataset,radius,bits,depth in WORK for b in (8,32)]
            workloads=workloads[(round_no-1)%len(workloads):]+workloads[:(round_no-1)%len(workloads)]
            for dataset,radius,bits,depth,b in workloads:
                expected=expected_rows(dataset,radius,bits)
                modes=MODES[(round_no-1)%len(MODES):]+MODES[:(round_no-1)%len(MODES)]
                for mode in modes:
                    name=f'formal_p5_r{round_no}_{dataset.lower()}_{radius}_b{b}_{mode}'
                    folder=ROOT/'runs'/name
                    folder,receipt=execute(name,command(dataset,radius,bits,depth,b,mode,
                        round_no%2==0,folder/'result',False,config))
                    query=rows(folder/'result_queries.csv')
                    query.sort(key=lambda x:int(x['query_index']))
                    assert len(query)==1024
                    got=[(int(r['qid']),int(r['count']),int(r['ordered_hash'])) for r in query]
                    assert all(x[0]==y[0] for x,y in zip(expected,got))
                    count_diff=sum(x[1]!=y[1] for x,y in zip(expected,got))
                    hash_diff=sum(x[2]!=y[2] for x,y in zip(expected,got))
                    if mode in ('SCAN_L','SCAN_E','C_MASK_E'):
                        assert count_diff==hash_diff==0,name
                    batches=rows(folder/'result.csv')
                    assert len(batches)==1024//b
                    times=[float(r['host_ms']) for r in batches]
                    host=sum(times);gpu=sum(float(r['gpu_ms']) for r in batches)
                    hits=sum(int(r['result_count_total']) for r in batches)
                    bytes_out=sum(int(r['d2h_bytes']) for r in batches)
                    assert hits==sum(x[1] for x in got)
                    assert bytes_out==len(batches)*(b+1)*8+hits*8
                    assert min(times)>0 and gpu>0
                    order=sorted(times)
                    p95=order[math.ceil(0.95*len(order))-1]
                    writer.writerow((round_no,dataset,radius,b,mode,host,gpu,
                                     statistics.median(times),p95,host/1024,1024000/host,
                                     hits,bytes_out,count_diff,hash_diff,
                                     receipt['binary_sha256']))
                    f.flush()
                    print('FORMAL',round_no,dataset,radius,b,mode,
                          round(host,3),count_diff,hash_diff,flush=True)


if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('oracle','audit','formal'):
        raise SystemExit('usage: campaign_final.py oracle|audit|formal')
    config=json.loads((ROOT/'frozen_external.json').read_text()) if sys.argv[1]!='oracle' else None
    {'oracle':make_oracles,'audit':lambda:audit(config),
     'formal':lambda:formal(config)}[sys.argv[1]]()
