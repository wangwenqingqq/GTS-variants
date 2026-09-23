#!/usr/bin/env python3
"""Fail-closed analysis of the frozen campaign; publishes summaries, not fixtures."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import statistics as st
from oracle import check, digest

HERE=Path(__file__).resolve().parent
ORDERS=['ABC','CBA','BCA','ACB','CAB','BAC']


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def percentile(xs,p):
    xs=sorted(xs)
    return xs[min(len(xs)-1,math.ceil(p*len(xs))-1)]


def paired_interval(b,c):
    logs=[math.log(x/y) for x,y in zip(b,c)]
    samples=sorted(math.exp(st.mean(x)) for x in itertools.product(logs,repeat=len(logs)))
    return {'geomean':math.exp(st.mean(logs)), 'bootstrap_95':[percentile(samples,.025),percentile(samples,.975)],
            'wins':sum(x>y for x,y in zip(b,c)), 'method':'Exact percentile bootstrap of paired process log ratios; 6^6 resamples'}


def clean(record):
    assert record['exit_code']==0 and record['stop_reason'] is None
    assert not record['runtime_errors'] and record['post_gpu_clear']


def trace(path):
    with sqlite3.connect(path) as db:
        kernels=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,k in enumerate(kernels) if k[0].startswith('initQnode('))
        assert first==9
        query=kernels[first:];assert len(query)==193*24
        signature=[k[:-1] for k in query[:24]]
        assert all([k[:-1] for k in query[i:i+24]]==signature for i in range(0,len(query),24))
        api={n:c for n,c in db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId')}
        assert not db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]
        return {'query_instances':193,'kernels_per_query':24,'ordered_signature':signature,
                'query_kernel_sum_us_mean':sum(k[-1] for k in query)/193/1000,
                'getQresultCount_us_mean':st.mean(k[-1]/1000 for k in query if k[0].startswith('getQresultCount(')),
                'whole_trace_api_counts':{k:v for k,v in api.items() if k.startswith(('cudaLaunchKernel','cudaGraphLaunch','cudaMemcpyAsync','cudaStreamSynchronize'))},
                'sqlite_sha256':sha(path)}


def analyze(root,oracle,archive):
    runs=root/'runs';o=read(oracle)
    required={'native_anchor'}
    for m in 'ABC':
        required.update([f'smoke_{m}',f'stress_{m}',f'nsys_{m}',f'boundary_negative_{m}',
                         f'boundary_0_{m}',f'boundary_256_{m}',f'gate_memcheck_{m}',f'gate_synccheck_{m}'])
        required.update(f'timing_{i}_{m}' for i in range(6))
    for m in 'BC':
        required.update([f'gate_initcheck_{m}',f'nsys_node_{m}',f'edge_memcheck_-1_{m}',f'edge_memcheck_256_{m}'])
        required.update(f'sustained_{i}_{m}' for i in range(2))
    assert {p.name for p in runs.iterdir()}==required,'Missing or unclassified observation'
    assert len(o['queries'])==len(set(o['queries']))==64
    assert sha(root/'fixtures/words_2000.txt')==o['data_sha256']
    assert sha(root/'fixtures/queries.qid')==o['qids_sha256']
    pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
    for n,h in pins.items():
        if n.startswith('GTS/'):assert sha(root/'source'/n.removeprefix('GTS/'))==h,n
    references={r:check(runs/name,oracle,r) for r,name in [(0,'boundary_0_A'),(4,'smoke_A'),(256,'boundary_256_A'),(-1,'boundary_negative_B')]}
    gold={r:{str(q):[len(p),digest(p)] for q,p in pairs} for r,pairs in references.items()}
    inventory={};dump_pass=[];sanitizer_pass=[]
    for p in sorted(runs.iterdir()):
        if p.name=='native_anchor':continue
        rec=read(p/'receipt.json')
        assert rec['binary_sha256']==sha(root/'bin/graph_bench')
        assert rec['mode']==p.name[-1]
        if p.name.startswith(('stress_','sustained_')):
            assert rec['tool']=='clean' and rec['repeats']==256 and rec['warmup']==64 and rec['radius']==4
            assert read(p/'result.json')['queries']==16384 and rec['validation']['pass']
        if p.name=='boundary_negative_A':
            assert len(rec['runtime_errors'])==65 and all('invalid argument' in e for e in rec['runtime_errors'])
            verdict='rejected: original zero-grid leaf launch'
        else:
            clean(rec)
            if (p/'result.results').exists():
                actual=check(p,oracle,rec['radius']);assert actual==references[rec['radius']],p.name
                dump_pass.append(p.name)
            rows=list(csv.DictReader((p/'result.csv').open()))
            assert len(rows)==rec['repeats']*64
            assert [int(row['qid']) for row in rows]==o['queries']*rec['repeats']
            assert all([int(row['count']),row['ordered_hash']]==gold[rec['radius']][row['qid']] for row in rows),p.name
            if rec['tool'] in ('memcheck','synccheck','initcheck'):
                assert 'ERROR SUMMARY: 0 errors' in ((p/'stderr.log').read_text()+(p/'stdout.log').read_text()),p.name
                sanitizer_pass.append(p.name)
            verdict='pass: external oracle/order/hash admission'
        inventory[p.name]={'verdict':verdict,'receipt_sha256':sha(p/'receipt.json'),'samples_sha256':sha(p/'result.csv')}
    bymode={};times={}
    for mode in 'ABC':
        vals=[read(runs/f'timing_{i}_{mode}/result.json') for i in range(6)]
        receipts=[read(runs/f'timing_{i}_{mode}/receipt.json') for i in range(6)]
        assert all(v['queries']==4096 and v['radius']==4 and v['mode']==mode for v in vals)
        assert all(r['validation']['pass'] and r['tool']=='clean' and r['warmup']==64 for r in receipts)
        times[mode]=[v['sum_query_s']*1e6/v['queries'] for v in vals]
        rows=[[float(r['query_us']) for r in csv.DictReader((runs/f'timing_{i}_{mode}/result.csv').open())] for i in range(6)]
        assert all(math.isclose(st.mean(rs),t,rel_tol=1e-9) for rs,t in zip(rows,times[mode]))
        bymode[mode]={'process_mean_query_us':times[mode], 'median_process_mean_query_us':st.median(times[mode]),
            'process_query_p10_p50_p90_us':[[percentile(rs,p) for p in (.1,.5,.9)] for rs in rows],
            'loop_cpu_us_per_query':[v['loop_cpu_s']*1e6/v['queries'] for v in vals],
            'loop_cpu_one_core_percent':[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vals],
            'setup_us':[v['setup_s']*1e6 for v in vals], 'capture_instantiate_us':[v['capture_instantiate_s']*1e6 for v in vals],
            'first_query_us':[v['first_query_s']*1e6 for v in vals]}
    paired=paired_interval(times['B'],times['C'])
    ratios={'A_over_B':st.median(times['A'])/st.median(times['B']), 'B_over_C':st.median(times['B'])/st.median(times['C']),
            'A_over_C':st.median(times['A'])/st.median(times['C'])}
    sustained=[]
    for i in range(2):
        pair={m:read(runs/f'sustained_{i}_{m}/result.json') for m in 'BC'}
        assert all(v['queries']==16384 for v in pair.values())
        avg={m:v['sum_query_s']*1e6/v['queries'] for m,v in pair.items()}
        sustained.append({'order':['BC','CB'][i], 'query_us':avg,'B_over_C':avg['B']/avg['C']})
    traces={m:trace(runs/f'nsys_node_{m}/trace.sqlite') for m in 'BC'}
    assert traces['B']['ordered_signature']==traces['C']['ordered_signature']
    signature=traces['B']['ordered_signature']
    for t in traces.values():del t['ordered_signature']
    native=read(runs/'native_anchor/receipt.json');clean(native);assert native['validation']['pass']
    saving=st.median(times['B'])-st.median(times['C'])
    return {'experiment':'gts_20260923_graph_single_query','scope':'Words N=2000, batch=1, radius=4, immutable H=3 tree; full ordered host results; common-driver A/B/C, not native executable ratios',
        'hardware':{'gpu':'RTX PRO 6000 Blackwell Server Edition','cuda':'13.1.115','arch':'sm_120','nsys':'2025.5.2','driver':'590.48.01'},
        'source_revision':'3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639','original_source_hashes_verified':True,
        'binary_sha256':sha(root/'bin/graph_bench'),'benchmark_source_sha256':sha(root/'graph_bench.cu'),
        'data_sha256':o['data_sha256'],'qids_sha256':o['qids_sha256'],'raw_archive_sha256':sha(archive),
        'timing_orders':ORDERS,'queries_per_process':4096,'warmup_queries':64,'results':bymode,'ratios_of_medians':ratios,
        'paired_B_over_C':paired,'sustained':sustained,
        'capture_only_amortization_queries':math.ceil(st.median(bymode['C']['capture_instantiate_us'])/saving),
        'amortization_caveat':'Descriptive capture+instantiate cost divided by steady saving; not a measured cold-start crossover',
        'gates':{'full_output_runs':dump_pass,'sanitizer_runs':sanitizer_pass,'stress_queries_per_mode':16384,
                 'normal_six_round_wins':paired['wins']==6,'paired_lower_bound_gt_1_05':paired['bootstrap_95'][0]>1.05,
                 'sustained_no_regression_gt_5_percent':all(p['B_over_C']>1/1.05 for p in sustained)},
        'nsys':{'scope':'Mechanism evidence only; timings include profiler perturbation. 1 first + 64 warmup + 128 sampled queries.',
                'B_C_sequence_geometry_resources_equal':True,'query_kernel_signature':signature,'traces':traces},
        'native_anchor':{'scope':'Original main; older 32-query sample repeated 128 times; native count-only check and lifecycle, NOT the A/B/C denominator',
                         'wall_s':native['wall_s'],'cpu_s':native['user_s']+native['system_s'],'count_validation':native['validation'],
                         'binary_sha256':native['binary_sha256'],'receipt_sha256':sha(runs/'native_anchor/receipt.json')},
        'negative_evidence':{'target':'Native A at radius -1','effect':'65 invalid-argument leaf launches despite exit code zero','decision':'Reject this boundary run; B/C independently validated empty output; do not claim native A supports every boundary',
                             'reopen_condition':'Fix native zero-grid handling in a separately pinned correctness variant'},
        'run_inventory':inventory}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['root','oracle','archive','out']:p.add_argument(arg,type=Path)
    a=p.parse_args();result=analyze(a.root,a.oracle,a.archive);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['ratios_of_medians','paired_B_over_C','sustained','capture_only_amortization_queries']},indent=2))
