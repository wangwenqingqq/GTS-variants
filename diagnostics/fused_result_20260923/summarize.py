#!/usr/bin/env python3
"""Fail-closed numerical summary of the preregistered fusion campaign."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import sqlite3
import statistics as st
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import clean,paired_interval,percentile
sys.path.insert(0,str(HERE))
from suite import ORDERS
from prepare import transform
from verify_full import verify


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def trace(path,width):
    with sqlite3.connect(path) as db:
        kernels=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,k in enumerate(kernels) if k[0].startswith('initQnode('));assert first==9
        query=kernels[first:];assert len(query)==193*width
        signature=[list(k[:-1]) for k in query[:width]]
        assert all([list(k[:-1]) for k in query[i:i+width]]==signature for i in range(0,len(query),width))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
        api={n:c for n,c in db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId') if n.startswith(('cudaLaunchKernel','cudaGraphLaunch','cudaMemcpyAsync','cudaStreamSynchronize'))}
        return {'queries':193,'kernels_per_query':width,'signature':signature,'whole_trace_api_counts':api,
                'sum_kernel_us_per_query':sum(k[-1] for k in query)/193/1000,
                'selection_kernel_us_per_query':sum(k[-1] for k in query if k[0].startswith(('fusedResultSelect(','getQresultCount(')))/193/1000,
                'sqlite_sha256':sha(path)}


def summarize(root,oracle,archive):
    full=verify(root,oracle);o=read(oracle);runs=root/'runs'
    expected={r:read(root/'fixtures'/f'expected_{r}.json') for r in [-1,0,4,256]}
    required=set(full['full_output_checks'])|{'selector_clean'}
    required.update('selector_'+t for t in ['memcheck','synccheck','initcheck','racecheck'])
    required.update('gate_'+t+'_'+m for t in ['memcheck','synccheck'] for m in 'BCDE')
    required.update('gate_'+t+'_'+m for t in ['initcheck','racecheck'] for m in 'DE')
    required.update('stress_'+m for m in 'BCDE');required.update('nsys_'+m for m in 'CE')
    required.update(f'timing_{i}_{m}' for i in range(6) for m in 'BCDE')
    required.update(f'sustained_{r}_{i}_{m}' for r in [0,4,256] for i in range(2) for m in 'BCDE')
    assert {p.name for p in runs.iterdir()}==required,'Missing or unclassified observations'
    assert (root/'graph_bench.cu').read_text()==transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    assert sha(root/'fused_result.cuh')==sha(HERE/'fused_result.cuh')
    declared=[f'timing_{i}_{m}' for i,order in enumerate(ORDERS) for m in order]+[f'sustained_{r}_{i}_{m}' for r in [0,4,256] for i,order in enumerate(['BCDE','EDCB']) for m in order]
    observed=[json.loads(line)['label'] for line in (root/'logs/timing.txt').read_text().splitlines() if line.startswith('{')]
    assert observed==declared,'Actual process order differs from contract'
    pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
    for n,h in pins.items():
        if n.startswith('GTS/'):assert sha(root/'source'/n.removeprefix('GTS/'))==h,n
    inventory={};sanitizers=[]
    for p in sorted(runs.iterdir()):
        r=read(p/'receipt.json');clean(r)
        assert r['label']==p.name
        assert r['mode']==('T' if p.name.startswith('selector_') else p.name[-1])
        radius=int(p.name.split('_')[1]) if p.name.startswith(('full_','sustained_')) else 4
        assert r['radius']==radius
        if r['mode']!='T':
            v=read(p/'result.json');assert v['mode']==r['mode'] and v['radius']==radius and v['queries']==r['repeats']*64
        assert r['runner_sha256']==sha(root/'run_fusion.py')
        assert r['binary_sha256']==sha(root/'bin'/('test_selector' if r['mode']=='T' else 'graph_bench'))
        logs=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
        if r['mode']=='T':assert r['validation']['pass'] and 'PASS selector 132 cases' in logs
        else:
            rows=list(csv.DictReader((p/'result.csv').open()))
            assert len(rows)==r['repeats']*64 and [int(x['qid']) for x in rows]==o['queries']*r['repeats']
            assert all([int(x['count']),x['ordered_hash']]==expected[r['radius']][x['qid']] for x in rows),p.name
            if not r['dump']:assert r['validation']['pass']
            if p.name.startswith(('stress_','sustained_')):assert r['repeats']==256 and r['warmup']==64 and r['tool']=='clean'
            if p.name.startswith('timing_'):assert r['repeats']==64 and r['warmup']==64 and r['radius']==4 and r['tool']=='clean'
        if r['tool'] not in ['clean','nsys-node']:
            marker='RACECHECK SUMMARY: 0 hazards' if r['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
            assert marker in logs,p.name
            sanitizers.append(p.name)
        inventory[p.name]={'mode':r['mode'],'tool':r['tool'],'radius':r['radius'],'repeats':r['repeats'],
                          'receipt_sha256':sha(p/'receipt.json'),'verdict':'pass: independent full output or validated ordered hashes' if r['mode']!='T' else 'pass: standalone selector cases'}
    stats={};times={}
    for m in 'BCDE':
        vals=[read(runs/f'timing_{i}_{m}/result.json') for i in range(6)]
        rows=[[float(r['query_us']) for r in csv.DictReader((runs/f'timing_{i}_{m}/result.csv').open())] for i in range(6)]
        times[m]=[v['sum_query_s']*1e6/v['queries'] for v in vals]
        assert all(v['queries']==4096 and v['mode']==m and v['radius']==4 for v in vals)
        assert all(math.isclose(st.mean(xs),v,rel_tol=1e-9) for xs,v in zip(rows,times[m]))
        stats[m]={'process_mean_query_us':times[m],'median_process_mean_query_us':st.median(times[m]),
                  'process_query_p10_p50_p90_us':[[percentile(x,p) for p in [.1,.5,.9]] for x in rows],
                  'loop_cpu_us_per_query':[v['loop_cpu_s']*1e6/v['queries'] for v in vals],
                  'loop_cpu_one_core_percent':[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vals],
                  'setup_us':[v['setup_s']*1e6 for v in vals],'capture_instantiate_us':[v['capture_instantiate_s']*1e6 for v in vals],
                  'first_query_us':[v['first_query_s']*1e6 for v in vals]}
    pairs={x+'_'+y:paired_interval(times[x],times[y]) for x,y in ['CE','BD']}
    for x,y in ['CE','BD']:
        pairs[x+'_'+y]['order_split']={order:[times[x][i]/times[y][i] for i,s in enumerate(ORDERS) if (s.index(x)<s.index(y))==(order==x+y)] for order in [x+y,y+x]}
    sustained=[]
    for r in [0,4,256]:
        for i,order in enumerate(['BCDE','EDCB']):
            vals={m:read(runs/f'sustained_{r}_{i}_{m}/result.json') for m in 'BCDE'}
            assert all(v['queries']==16384 and v['mode']==m and v['radius']==r for m,v in vals.items())
            t={m:v['sum_query_s']*1e6/v['queries'] for m,v in vals.items()}
            sustained.append({'radius':r,'order':order,'query_us':t,'C_over_E':t['C']/t['E'],'B_over_D':t['B']/t['D']})
    traces={m:trace(runs/f'nsys_{m}/trace.sqlite',w) for m,w in [('C',24),('E',17)]}
    assert traces['C']['signature'][:14]==traces['E']['signature'][:14]
    assert traces['C']['signature'][21:23]==traces['E']['signature'][14:16]
    assert traces['E']['signature'][16][0].startswith('fusedResultSelect(')
    assert all(t['whole_trace_api_counts']['cudaGraphLaunch_v10000']==193 for t in traces.values())
    resources=(root/'logs/resources.txt').read_text()
    resource_line=re.search(r'Function _Z17fusedResultSelect[^\n]+:\n([^\n]+)',resources).group(1).strip()
    assert 'REG:40 STACK:0 SHARED:3232 LOCAL:0' in resource_line
    sass=(root/'logs/selector_exact.sass').read_text()
    assert not re.search(r'\b(?:LDL|STL)(?:\.|\s)',sass)
    normalization=read(root/'logs/selector_normalization.json')
    assert sha(root/'logs/selector.normalized.sass')==normalization['sha256']
    gates={'all_six_C_E_wins' :pairs['C_E']['wins']==6,'C_E_lower_bound_gt_1_05':pairs['C_E']['bootstrap_95'][0]>1.05,
           'all_sustained_no_regression_gt_5_percent':all(s['C_over_E']>1/1.05 and s['B_over_D']>1/1.05 for s in sustained)}
    return {'experiment':'gts_20260923_fused_result','state':'accepted bounded prototype' if all(gates.values()) else 'inconclusive: promotion gate not met',
            'scope':'Words N=2000, H=3, batch one, immutable tree, full stable ordered host results; normal radius 4, sustained radii 0/4/256; no larger shape, update or concurrency claim',
            'source_revision':'3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639','comparator_revision':'7938ed6',
            'hardware':{'gpu':'RTX PRO 6000 Blackwell Server Edition','arch':'sm_120','cuda':'13.1.115','driver':'590.48.01'},
            'binary_sha256':sha(root/'bin/graph_bench'),'selector_test_binary_sha256':sha(root/'bin/test_selector'),
            'generated_source_sha256':sha(root/'graph_bench.cu'),'kernel_source_sha256':sha(root/'fused_result.cuh'),
            'runner_sha256':sha(root/'run_fusion.py'),'data_sha256':o['data_sha256'],'qids_sha256':o['qids_sha256'],
            'raw_archive_sha256':sha(archive),'timing_orders':ORDERS,'results':stats,
            'ratios_of_medians':{x+'_over_'+y:st.median(times[x])/st.median(times[y]) for x,y in ['CE','BD']},
            'paired':pairs,'sustained':sustained,'gates':gates,'full_output_checks':full['full_output_checks'],
            'sanitizers':sanitizers,'standalone_cases_per_run':132,'stress_queries_per_mode':16384,
            'nsys':traces,'run_inventory':inventory,
            'static_selector':{'final_resource_line':resource_line,'ptxas_shared_bytes':2208,'stack_bytes':0,'spill_load_store_bytes':0,'static_LDL_STL':0,'raw_selected_sass_sha256':sha(root/'logs/selector_exact.sass'),'normalization':normalization},
            'negative_evidence':[{'target':'First compile via relocated nvcc launcher','effect':'Header resolution failed before GPU execution','decision':'Use the verified toolkit absolute executable; failed build log retained'},
                                 {'target':'Native A at negative radius','effect':'Prior campaign exposed zero-grid fault','decision':'Do not rerun/promote this known-invalid boundary; independent B/C/D/E zero-output checks retained'}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','oracle','archive','output']:p.add_argument(name,type=Path)
    a=p.parse_args();r=summarize(a.root,a.oracle,a.archive);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['state','ratios_of_medians','paired','gates','sustained']},indent=2))
