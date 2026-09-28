#!/usr/bin/env python3
"""Fail-closed curation of the preregistered six-arm interaction experiment."""
import argparse
import csv
import json
import math
import sqlite3
import statistics as st
import sys
from pathlib import Path
from prepare import HERE, GRAPH, ORDERS, driver, kernels, layout, runner, verifier, suite, load
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import paired_interval, percentile

PAIRS=['EF','FX','FY','RX','TY','EX','EY','ER','ET','XY']
STAGES=['full','gates','stress','screen','sustained','trace']


def read(p):return json.loads(p.read_text())

def trace(path,mode):
    fused=mode in 'FXY';n=13 if fused else 17
    markers={'E':'initQnode(', 'R':'initQnode(', 'T':'initQnode(',
             'F':'fusedTraversal<false>', 'X':'fusedTraversalLayout<2>', 'Y':'fusedTraversalLayout<3>'}
    with sqlite3.connect(path) as db:
        rows=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        def name(r):return r[0].replace('<(int)','<').replace('<(bool)0>','<false>')
        first=next(i for i,r in enumerate(rows) if markers[mode] in name(r));rows=rows[first:]
        assert len(rows)==193*n,(mode,len(rows),n)
        sig=[list(r[:-1]) for r in rows[:n]]
        assert all([list(r[:-1]) for r in rows[i:i+n]]==sig for i in range(0,len(rows),n))
        assert not db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]
        api=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        assert api['cudaGraphLaunch_v10000']==193
    return dict(signature=sig,kernels_per_query=n,query_instances=193,sqlite_sha256=sha(path),
                traversal_kernel_sum_us=sum(r[-1] for i,r in enumerate(rows) if i%n<(1 if fused else 5))/193/1000,
                all_kernel_sum_us=sum(r[-1] for r in rows)/193/1000)


def layout_bytes(mode,d):
    if mode in 'ADEFG':return 0
    return 888+4*(11*d if mode in 'RBXJ' else ((d+7)//8)*104)


def pair(a,b,orders,left,right):
    v=paired_interval(a,b)
    v['method']='Exact percentile bootstrap of four round-paired process log ratios; 4^4 resamples'
    v['ratio_of_medians']=st.median(a)/st.median(b)
    v['order_split']={s:[a[i]/b[i] for i,o in enumerate(orders) if (o.index(left)<o.index(right))==(s==left+right)] for s in [left+right,right+left]}
    return v


def dataset(root,common,plan,require,prereg):
    o=read(root/'fixtures/oracle.json');assert o['dataset']==root.name
    for n,h in prereg['fixture_sha256'][o['dataset']].items():assert sha(root/'fixtures'/n)==h,(o['dataset'],n)
    full=verify(root);require(root,common,'trace')
    expected={r[0]:r for s in STAGES for r in plan(s,o['radii'])}
    assert {p.name for p in (root/'runs').iterdir()}==set(expected)
    gold={r:read(root/'fixtures'/f'expected_{r:g}.json') for r in o['radii'].values()}
    inv={};gaps=[];no_checks=0
    admission=read(common/'logs/admission.json');gpu=admission['state'].split(', ')[1]
    for label,mode,radius,reps,warmup,tool,dump in expected.values():
        p=root/'runs'/label;x=read(p/'receipt.json');clean(x)
        assert tuple(x[k] for k in ['label','mode','radius','repeats','warmup','tool','dump'])==(label,mode,radius,reps,warmup,tool,dump)
        assert x['binary_sha256']==sha(common/'bin/graph_bench') and x['runner_sha256']==sha(common/'run_layout.py')
        assert x['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
        for phase in ['before','after']:
            v=read(p/(phase+'.json'));assert not v['apps'].strip() and gpu in v['gpu']
        checks=read(p/'checks.json');assert all(not c['foreign'] for c in checks)
        ts=[0]+[c['elapsed_s'] for c in checks]+[x['wall_s']];gaps.extend(b-a for a,b in zip(ts,ts[1:]));no_checks+=not bool(checks)
        rows=list(csv.DictReader((p/'result.csv').open()));assert [int(r['qid']) for r in rows]==o['queries']*reps
        assert all([int(r['count']),r['ordered_hash']]==gold[radius][r['qid']] for r in rows)
        summary=check_summary(read(p/'result.json'),x,rows);assert summary['layout_bytes']==layout_bytes(mode,o['dimension'])
        if not label.startswith('full_'):assert x['validation']['pass']
        if tool in ['memcheck','synccheck','initcheck','racecheck']:
            log=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
            if mode=='F':assert 'PASS combo 80 flag cases' in log
        inv[label]=dict(mode=mode,tool=tool,radius=radius,queries=len(rows),receipt_sha256=sha(p/'receipt.json'),samples_sha256=sha(p/'result.csv'))
    stats={};times={}
    for m in GRAPH:
        vs=[read(root/'runs'/f'screen_{i}_{m}/result.json') for i in range(4)]
        xs=[[float(r['query_us']) for r in csv.DictReader((root/'runs'/f'screen_{i}_{m}/result.csv').open())] for i in range(4)]
        times[m]=[v['sum_query_s']*1e6/v['queries'] for v in vs]
        assert all(math.isclose(st.mean(a),b,rel_tol=1e-9) for a,b in zip(xs,times[m]))
        stats[m]=dict(process_mean_query_us=times[m],median_process_mean_query_us=st.median(times[m]),p10_p50_p90_query_us=[[percentile(a,p) for p in [.1,.5,.9]] for a in xs],layout_bytes=layout_bytes(m,o['dimension']),layout_setup_us=[v['layout_setup_s']*1e6 for v in vs],first_query_us=[v['first_query_s']*1e6 for v in vs],setup_us=[v['setup_s']*1e6 for v in vs],cpu_one_core_percent=[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vs],setup_first_plus_512_queries_us_per_query=[(v['layout_setup_s']+v['setup_s']+v['first_query_s']+v['sum_query_s'])*1e6/512 for v in vs])
    pairs={a+b:pair(times[a],times[b],ORDERS,a,b) for a,b in PAIRS}
    interactions={}
    for l,m in [('R','X'),('T','Y')]:
        v=paired_interval([times['F'][i]/times[m][i] for i in range(4)],[times['E'][i]/times[l][i] for i in range(4)])
        v['method']='Exact 4^4 round-level paired log interaction bootstrap'
        v['meaning']=f'(F/{m})/(E/{l}); >1 means layout is relatively more favorable with traversal fusion'
        interactions[l]=v
    sustained=[]
    for i,order in enumerate(ORDERS[:2]):
        ts={m:(lambda v:v['sum_query_s']*1e6/v['queries'])(read(root/'runs'/f'sustained_{i}_{m}/result.json')) for m in GRAPH}
        sustained.append(dict(order=order,query_us=ts,ratios={a+b:ts[a]/ts[b] for a,b in PAIRS}))
    decisions={}
    for m in 'XY':
        gates={b:dict(four_wins=pairs[b+m]['wins']==4,lower_95_gt_1_03=pairs[b+m]['bootstrap_95'][0]>1.03,sustained_no_gt_5pct_regression=all(s['ratios'][b+m]>=1/1.05 for s in sustained)) for b in 'EF'}
        decisions[m]=dict(followup_warranted=all(all(g.values()) for g in gates.values()),gates=gates,production_promoted=False)
    traces={m:trace(root/'runs'/('nsys_'+m)/'trace.sqlite',m) for m in GRAPH}
    for m in GRAPH:
        assert traces[m]['signature'][1 if m in 'FXY' else 5:]==traces['E']['signature'][5:]
        assert any('fusedResultSelect(' in r[0] for r in traces[m]['signature'])
    for m,marker in [('E','findNextRnn('),('R','findNextLayout<2>'),('T','findNextLayout<3>')]:
        assert all(marker in traces[m]['signature'][i][0].replace('<(int)','<') for i in [1,3])
        assert all(traces[m]['signature'][i]==traces['E']['signature'][i] for i in [0,2,4])
    return dict(fixture={k:v for k,v in o.items() if k not in ['distances','queries','source_relative']},full_verified=full,inventory=inv,statistics=stats,paired=pairs,interaction=interactions,sustained=sustained,decisions=decisions,nsys=traces,safety=dict(process_check_gap_median_s=st.median(gaps),process_check_gap_max_s=max(gaps),runs_without_inprocess_checks=no_checks))


def main(root,out):
    global sha,clean,verify,check_summary
    v=load('combo_verify',root/'verify_full.py');sha,clean,verify,check_summary=v.sha,v.clean,v.verify,v.check_summary
    sys.path.insert(0,str(root));s=load('combo_suite',root/'suite.py')
    prereg=read(root/'preregistration.json')
    checkpoint=read(HERE/'CHECKPOINT.json')
    for field in ['experiment','base_commit','previous_layout_commit','fixture_sha256','generated_sha256']:
        assert prereg[field]==checkpoint[field],field
    for n,h in prereg['generated_sha256'].items():assert sha(root/n)==h,n
    assert (root/'graph_bench.cu').read_text()==driver((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    assert (root/'traversal_layout_generated.cuh').read_text()==kernels((root/'source/include/search.cuh').read_text())
    assert (root/'run_layout.py').read_text()==runner((HERE.parent/'graph_query_20260923/run.py').read_text())
    assert (root/'verify_full.py').read_text()==verifier() and (root/'suite.py').read_text()==suite()
    for name in ['CONTRACT.md','audit_combo.cuh']:assert sha(root/name)==sha(HERE/name)
    pins={n:h for n,h in read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256'].items() if n.startswith('GTS/')}
    assert read(root/'source_pins.json')==pins
    for n,h in pins.items():assert sha(root/'source'/n.removeprefix('GTS/'))==h
    static=read(HERE/'STATIC_EVIDENCE.json');assert sha(root/'bin/graph_bench')==static['binary_sha256']
    assert sha(root/'static/sass.txt')==static['sass_dump_sha256']
    assert sha(root/'static/resources.txt')==static['resource_dump_sha256']
    assert 'V13.1.115' in (root/'logs/toolkit.txt').read_text()
    a=read(root/'logs/admission.json');fields=a['state'].split(', ')
    amendment=read(root/'amendment.json')
    assert sha(root/'amendment.json')==a['amendment_sha256']
    assert fields[:2]==[str(amendment['gpu_index']),amendment['gpu_uuid']]
    assert amendment['binary_sha256']==static['binary_sha256']
    assert fields[3]=='590.48.01' and fields[4]=='12.0' and fields[5]=='600.00 W'
    for stage in STAGES:
        observed=[json.loads(x) for x in (root/'logs'/(stage+'.txt')).read_text().splitlines() if x.startswith('{')]
        expected=[read(root/'data'/ds/'runs'/r[0]/'receipt.json') for ds in ['GIST','Deep','Tloc'] for r in s.plan(stage,read(root/'data'/ds/'fixtures/oracle.json')['radii'])]
        assert observed==expected,stage
    result=dict(experiment='gts_20260924_traversal_layout_l2_2000',state='bounded interaction screen; no production promotion',scope='Complete hot batch-one query including transfers/host readiness; construction/setup/capture/hashing excluded; result fusion and Graph common to every performance arm.',base_commit=prereg['base_commit'],binary_sha256=sha(root/'bin/graph_bench'),runner_sha256=sha(root/'run_layout.py'),contract_sha256=sha(HERE/'CONTRACT.md'),amendment_sha256=sha(root/'amendment.json'),orders=ORDERS,hardware=dict(gpu_index=int(fields[0]),gpu_name=fields[2],driver=fields[3],arch='sm_120',power_limit=fields[5],cuda='13.1.115',clock_policy=a['clock_policy'],cpu=a['cpu']),datasets={ds:dataset(root/'data'/ds,root,s.plan,s.require,prereg) for ds in ['GIST','Deep','Tloc']})
    for ds,r in result['datasets'].items():
        for m in GRAPH:
            sig=r['nsys'][m]['signature'];selected=sig[0 if m in 'FXY' else 1]
            reg=int(static[m]['resources'].split('REG:')[1].split()[0]);assert selected[7]==reg
    out.write_text(json.dumps(result,indent=2)+'\n')
    for ds,r in result['datasets'].items():print(ds,json.dumps(dict(medians={m:v['median_process_mean_query_us'] for m,v in r['statistics'].items()},paired=r['paired'],interaction=r['interaction'],decisions=r['decisions'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();main(a.root.resolve(),a.out)
