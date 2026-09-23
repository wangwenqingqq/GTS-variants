#!/usr/bin/env python3
"""Fail-closed summary; each mechanism is admitted independently."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics as st
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import clean,paired_interval,percentile
sys.path.insert(0,str(HERE))
from prepare import transform,kernels
from suite import MODES,ORDERS,TOOLS,gate_labels,expected_tool
from verify_full import verify


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def trace(path,mode):
    width=13 if mode=='F' else 17
    with sqlite3.connect(path) as db:
        rows=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,r in enumerate(rows) if ('fusedTraversal<false>' in r[0] if mode=='F' else r[0].startswith('initQnode(')))
        assert first==9
        rows=rows[first:];assert len(rows)==193*width
        sig=[list(r[:-1]) for r in rows[:width]]
        assert all([list(r[:-1]) for r in rows[i:i+width]]==sig for i in range(0,len(rows),width))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
        api=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        assert api['cudaGraphLaunch_v10000']==193
        traversal=sum(r[-1] for i,r in enumerate(rows) if i%width<(1 if mode=='F' else 5))/193/1000
        return {'kernels_per_query':width,'query_instances':193,'signature':sig,'traversal_kernel_sum_us_per_query':traversal,
                'kernel_sum_us_per_query':sum(r[-1] for r in rows)/193/1000,'sqlite_sha256':sha(path)}


def summarize(root,oracle,archive):
    full=verify(root,oracle);o=read(oracle);runs=root/'runs'
    expected={r:read(root/'fixtures'/f'expected_{r}.json') for r in [-1,0,4,256]}
    required=set(full['full_output_checks'])|set(gate_labels())|{'traversal_clean'}
    required.update(f'timing_{i}_{m}' for i in range(6) for m in MODES)
    required.update(f'sustained_{r}_{i}_{m}' for r in [0,4,256] for i in range(2) for m in MODES)
    required.update('nsys_'+m for m in 'EFP')
    assert {p.name for p in runs.iterdir()}==required,'Missing or unclassified observation'
    assert len(required)==133
    assert (root/'graph_bench.cu').read_text()==transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    assert (root/'traversal_generated.cuh').read_text()==kernels((root/'source/include/search.cuh').read_text())
    assert sha(root/'test_traversal.cu')==sha(HERE/'test_traversal.cu')
    assert sha(root/'fused_result.cuh')==sha(HERE.parent/'fused_result_20260923/fused_result.cuh')
    pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
    for f,h in pins.items():
        if f.startswith('GTS/'):assert sha(root/'source'/f.removeprefix('GTS/'))==h
    declared=[f'timing_{i}_{m}' for i,s in enumerate(ORDERS) for m in s]
    declared += [f'sustained_{r}_{i}_{m}' for r in [0,4,256] for i,s in enumerate([MODES,MODES[::-1]]) for m in s]
    observed=[json.loads(s)['label'] for s in (root/'logs/timing.txt').read_text().splitlines() if s.startswith('{')]
    assert observed==declared,'Actual timing order differs'
    inventory={};sanitizers=[]
    for p in sorted(runs.iterdir()):
        r=read(p/'receipt.json');clean(r)
        assert r['label']==p.name and r['runner_sha256']==sha(root/'run_ablation.py')
        assert r['tool']==expected_tool(p.name),p.name
        mode='V' if p.name.startswith('traversal_') else p.name[-1]
        assert r['mode']==mode
        assert r['binary_sha256']==sha(root/'bin'/('test_traversal' if mode=='V' else 'graph_bench'))
        logs=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
        if mode=='V':assert r['validation']['pass'] and 'PASS traversal 352 cases' in logs
        else:
            rows=list(csv.DictReader((p/'result.csv').open()))
            assert len(rows)==r['repeats']*64 and [int(x['qid']) for x in rows]==o['queries']*r['repeats']
            assert all([int(x['count']),x['ordered_hash']]==expected[r['radius']][x['qid']] for x in rows),p.name
            v=read(p/'result.json');assert v['mode']==mode and v['queries']==len(rows) and v['radius']==r['radius']
            if not r['dump']:assert r['validation']['pass']
            if p.name.startswith(('stress_','sustained_')):assert r['repeats']==256 and r['warmup']==64 and r['tool']=='clean'
            if p.name.startswith('timing_'):assert r['repeats']==64 and r['warmup']==64 and r['radius']==4 and r['tool']=='clean'
        if r['tool'] in TOOLS:
            assert ('RACECHECK SUMMARY: 0 hazards' if r['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs
            sanitizers.append(p.name)
        inventory[p.name]={'mode':mode,'tool':r['tool'],'radius':r['radius'],'repeats':r['repeats'],'receipt_sha256':sha(p/'receipt.json'),'verdict':'pass'}
    times={};stats={}
    for m in MODES:
        vals=[read(runs/f'timing_{i}_{m}/result.json') for i in range(6)]
        rows=[[float(r['query_us']) for r in csv.DictReader((runs/f'timing_{i}_{m}/result.csv').open())] for i in range(6)]
        times[m]=[v['sum_query_s']*1e6/v['queries'] for v in vals]
        assert all(math.isclose(st.mean(xs),v,rel_tol=1e-9) for xs,v in zip(rows,times[m]))
        stats[m]={'process_mean_query_us':times[m],'median_process_mean_query_us':st.median(times[m]),
                  'process_query_p10_p50_p90_us':[[percentile(xs,p) for p in [.1,.5,.9]] for xs in rows],
                  'loop_cpu_us_per_query':[v['loop_cpu_s']*1e6/v['queries'] for v in vals],
                  'loop_cpu_one_core_percent':[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vals],
                  'setup_us':[v['setup_s']*1e6 for v in vals],'capture_instantiate_us':[v['capture_instantiate_s']*1e6 for v in vals],
                  'first_query_us':[v['first_query_s']*1e6 for v in vals]}
    pairs={}
    for a,b in ['EF','EP','DG','DQ']:
        pairs[a+b]=paired_interval(times[a],times[b])
        pairs[a+b]['order_split']={s:[times[a][i]/times[b][i] for i,o in enumerate(ORDERS) if (o.index(a)<o.index(b))==(s==a+b)] for s in [a+b,b+a]}
    sustained=[]
    for radius in [0,4,256]:
        for i,order in enumerate([MODES,MODES[::-1]]):
            vals={m:read(runs/f'sustained_{radius}_{i}_{m}/result.json') for m in MODES}
            assert all(v['radius']==radius and v['queries']==16384 for v in vals.values())
            ts={m:v['sum_query_s']*1e6/v['queries'] for m,v in vals.items()}
            sustained.append({'radius':radius,'order':order,'query_us':ts,'ratios':{a+b:ts[a]/ts[b] for a,b in ['EF','EP','DG','DQ']}})
    traces={m:trace(runs/f'nsys_{m}/trace.sqlite',m) for m in 'EFP'}
    assert traces['E']['signature'][5:]==traces['F']['signature'][1:]==traces['P']['signature'][5:]
    assert all(traces['E']['signature'][i]==traces['P']['signature'][i] for i in [0,2,4])
    assert all('dedupLevel<false>' in traces['P']['signature'][i][0] for i in [1,3])
    work=[dict(zip(['pattern','radius','child','fused','parent'],map(int,x))) for x in re.findall(r'WORK pattern=(\d+) radius=(-?\d+) child=(\d+) fused=(\d+) parent=(\d+)',(runs/'traversal_clean/stdout.log').read_text())]
    assert len(work)==16 and all(x['child']==x['fused'] and x['parent']<=x['child'] for x in work)
    resources={}
    text=(root/'logs/resources.txt').read_text()
    for name in ['findNextRnn','fusedTraversal','dedupLevel']:
        line=re.search(r'Function [^\n]*'+name+r'[^\n]*:\n([^\n]+)',text).group(1).strip()
        norm=read(root/'logs'/f'{name}.normalization.json')
        assert norm['sha256']==sha(root/'logs'/f'{name}.normalized.sass')
        sass=(root/'logs'/f'{name}.sass').read_text()
        resources[name]={'final_resource_line':line,'normalized_sass':norm,'raw_sass_sha256':sha(root/'logs'/f'{name}.sass'),
                         'static_LDL':len(re.findall(r'\bLDL(?:\.|\s)',sass)),'static_STL':len(re.findall(r'\bSTL(?:\.|\s)',sass))}
    decisions={}
    for candidate,primary,stream in [('F','EF','DG'),('P','EP','DQ')]:
        gate={'six_primary_wins':pairs[primary]['wins']==6,'primary_lower_bound_gt_1_05':pairs[primary]['bootstrap_95'][0]>1.05,
              'sustained_no_regression_gt_5_percent':all(s['ratios'][p]>1/1.05 for s in sustained for p in [primary,stream])}
        decisions[candidate]={'state':'accepted bounded prototype' if all(gate.values()) else 'not promoted: performance gate not met','gates':gate}
    return {'experiment':'gts_20260923_traversal_ablation_words2000','scope':'Words N=2000, H=3, batch one, immutable tree, full ordered host results; excludes construction; no combined F+P or cross-index claim',
            'source_revision':'3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639','comparator_revision':'6221ae9','decisions':decisions,
            'binary_sha256':sha(root/'bin/graph_bench'),'test_binary_sha256':sha(root/'bin/test_traversal'),
            'generated_driver_sha256':sha(root/'graph_bench.cu'),'generated_kernels_sha256':sha(root/'traversal_generated.cuh'),
            'runner_sha256':sha(root/'run_ablation.py'),'data_sha256':o['data_sha256'],'qids_sha256':o['qids_sha256'],'raw_archive_sha256':sha(archive),
            'timing_orders':ORDERS,'results':stats,'ratios_of_medians':{a+b:st.median(times[a])/st.median(times[b]) for a,b in ['EF','EP','DG','DQ']},
            'paired':pairs,'sustained':sustained,'nsys':traces,'resources':resources,'diagnostic_work':work,
            'full_output_checks':full['full_output_checks'],'sanitizers':sanitizers,'regression_cases_per_run':352,'stress_queries_per_mode':16384,'run_inventory':inventory}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','oracle','archive','output']:p.add_argument(name,type=Path)
    a=p.parse_args();r=summarize(a.root,a.oracle,a.archive);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['decisions','ratios_of_medians','paired','sustained','diagnostic_work']},indent=2))
