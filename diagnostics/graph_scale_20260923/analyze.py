#!/usr/bin/env python3
"""Recompute scale results from immutable raw evidence; fail on missing gates."""
import argparse,csv,hashlib,importlib.util,json,math,sqlite3,statistics as st,sys
from collections import Counter
from pathlib import Path
from check import check
from prepare import transform,runner
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
spec=importlib.util.spec_from_file_location('small_analysis',HERE.parent/'graph_query_20260923/analyze.py')
small=importlib.util.module_from_spec(spec);spec.loader.exec_module(small)
ORDERS=['ABC','CBA','BCA','ACB','CAB','BAC']
CASES=['n2000_k1','n20000_k1','n100000_k1','n611756_k1','n611756_k8','n611756_k32']
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
    with p.open() as f:return list(csv.DictReader(f))

def telemetry(p):
    with p.open() as f:rows=list(csv.reader(f))
    values=[[float(x) for x in row[1:]] for row in rows]
    assert values and all(len(row)==3 for row in values)
    return {'scope':'100 ms whole-process samples, including construction/setup; not query-only or SM occupancy',
            'samples':len(values),'sampled_peak_memory_mib':max(row[0] for row in values),
            'gpu_util_p10_p50_p90_percent':[small.percentile([row[1] for row in values],q) for q in [.1,.5,.9]],
            'sampled_peak_power_w':max(row[2] for row in values)}

def required(n,k):
    labels={f'{a}_{m}' for a in ['smoke','stress'] for m in 'ABC'}
    labels|={f'timing_{i}_{m}' for i in range(6) for m in 'ABC'}
    labels|={f'sustained_{i}_{m}' for i in range(2) for m in 'BC'}
    labels|={f'gate_{t}_{m}' for t in ['memcheck','synccheck','initcheck'] for m in ('ABC' if t!='initcheck' and k==1 else 'BC')}
    if k==1:labels|={f'boundary_{r}_{m}' for r in [0,256] for m in 'ABC'}
    if n==611756 and k==1:labels|={'boundary_negative_B','boundary_negative_C'}
    if n==611756 and k in [1,32]:labels|={'nsys_B','nsys_C'}
    return labels


def profile(p,k,slots):
    with sqlite3.connect(p) as db:
        rows=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        starts=[i for i,row in enumerate(rows) if row[0].startswith('initQnode(')];assert len(starts)==64+k
        chunks=[rows[a:b] for a,b in zip(starts,starts[1:]+[len(rows)])]
        sig=[row[:-1] for row in chunks[0]];assert all([row[:-1] for row in c]==sig for c in chunks)
        streams=db.execute("SELECT DISTINCT k.streamId FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName WHERE s.value LIKE 'initQnode(%'").fetchall()
        assert len(streams)==1
        # The nonblocking query stream is created after construction/audit.
        # Exclude UVM migrations (separate copy kinds), not explicit query copies.
        copies=Counter(db.execute('SELECT copyKind,bytes FROM CUPTI_ACTIVITY_KIND_MEMCPY WHERE streamId=? AND copyKind IN (1,2)',streams[0]).fetchall())
        assert copies==Counter({(1,4):len(chunks),(2,4):len(chunks),(2,slots*4):len(chunks)*2}),copies
        copy_times=db.execute('SELECT copyKind,sum(end-start) FROM CUPTI_ACTIVITY_KIND_MEMCPY WHERE streamId=? AND copyKind IN (1,2) GROUP BY copyKind',streams[0]).fetchall()
        api=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        kernel_totals={}
        for c in chunks:
            for row in c:kernel_totals[row[0]]=kernel_totals.get(row[0],0)+row[-1]/1000/len(chunks)
        assert not db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]
        return {'signature':sig,'kernels_per_query':len(sig),'kernels_per_bundle':len(sig)*k,'query_instances':len(chunks),
                'mean_kernel_us_per_query':kernel_totals,
                'explicit_query_copies':[{'kind':kind,'bytes':size,'count':count} for (kind,size),count in sorted(copies.items())],
                'explicit_query_copy_bytes_per_query':8+slots*8,
                'mean_explicit_copy_us_per_query':{str(kind):ns/1000/len(chunks) for kind,ns in copy_times},
                'whole_trace_api_counts':{n:v for n,v in api.items() if n.startswith(('cudaLaunchKernel','cudaGraphLaunch','cudaMemcpyAsync','cudaStreamSynchronize'))},
                'sqlite_sha256':sha(p)}


def analyze(root,archive):
    result={};inventory={};binary=sha(root/'bin/graph_bench');full_runs=0;san_runs=0
    interruption=read(root/'interruption.json') if (root/'interruption.json').exists() else None
    if interruption:
        assert interruption['reason']=='foreign GPU activity' and interruption['case']=='n611756_k32' and interruption['label']=='timing_1_C'
        assert interruption['failed_receipt_sha256']==sha(root/'cases/n611756_k32/runs/timing_1_C/receipt.json')
    generated=transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    assert (root/'graph_bench.cu').read_text()==generated,'Published generator differs from measured CUDA source'
    assert (root/'run_scale.py').read_text()==runner((HERE.parent/'graph_query_20260923/run.py').read_text())
    assert (root/'oracle.cpp').read_bytes()==(HERE/'oracle.cpp').read_bytes()
    pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
    for n,h in pins.items():
        if n.startswith('GTS/'):assert sha(root/'source'/n.removeprefix('GTS/'))==h
    for case in CASES:
        p=root/'cases'/case;n=int(case.split('_')[0][1:]);k=int(case.split('_k')[1])
        partial=bool(interruption and k==32)
        for phase in ['smoke','gates']+([] if partial else ['timing']):
            assert read(p/(phase+'_complete.json'))['complete']
        expected=required(n,k)
        if interruption:
            expected-={'nsys_B','nsys_C'}
            if partial:
                expected={x for x in expected if not x.startswith(('timing_','sustained_'))}|{'timing_0_A','timing_0_B','timing_0_C','timing_1_C'}
                assert not (p/'timing_complete.json').exists()
        observed={d.name for d in (p/'runs').iterdir()}
        assert observed==expected,(case,'missing/extra run')
        manifest=read(p/'fixtures/manifest.json');assert manifest['n']==n and len(set(manifest['qids']))==64
        for f,h in manifest['file_sha256'].items():assert sha(p/'fixtures'/f)==h
        oracle_record=read(root/f'logs/oracle_retry_{n}.json');assert oracle_record['oracle_sha256']==sha(p/'fixtures/oracle.bin')
        assert oracle_record['binary_sha256']==sha(root/'bin/oracle')
        reference,gold=check(p,'smoke_A',4,write=False);assert gold==read(p/'fixtures/expected_4.json')
        boundary_ref={}
        for d in sorted((p/'runs').iterdir()):
            r=read(d/'receipt.json');assert r['binary_sha256']==binary and r['bundle']==k and r['mode']==d.name[-1]
            assert r['runner_sha256']==sha(root/'run_scale.py')
            for f,h in r['input_sha256'].items():assert sha(p/'fixtures'/f)==h
            if partial and d.name=='timing_1_C':
                assert r['exit_code']==-15 and r['stop_reason']=='foreign GPU activity' and not r['post_gpu_clear']
                assert any(c['foreign'] for c in read(d/'checks.json')) and not (d/'result.csv').exists()
                inventory[case+'/'+d.name]={'receipt_sha256':sha(d/'receipt.json'),'verdict':'rejected: foreign activity; no completed timing sample'}
                continue
            small.clean(r)
            qsname=next(f for f in r['input_sha256'] if f.endswith('.qid'))
            qs=list(map(int,(p/'fixtures'/qsname).read_text().split()))[1:]
            rows=csvrows(d/'result.csv');assert [int(row['qid']) for row in rows]==qs*r['repeats']
            if r['radius']==4:assert all([int(row['count']),row['ordered_hash']]==gold[row['qid']] for row in rows)
            if (d/'result.results').exists():
                ext=read(d/'external_check.json');assert ext['pass'] and ext['oracle_sha256']==oracle_record['oracle_sha256']
                if r['radius']!=4:
                    ref=boundary_ref.get(r['radius']);v,_=check(p,d.name,r['radius'],ref,write=False);boundary_ref[r['radius']]=v
                else:
                    v,_=check(p,d.name,4,write=False);assert all(pairs==reference[q] for q,pairs in v.items())
                full_runs+=1
            if r['tool'] in ['memcheck','synccheck','initcheck']:
                assert 'ERROR SUMMARY: 0 errors' in (d/'stdout.log').read_text()+(d/'stderr.log').read_text();san_runs+=1
            if d.name.startswith(('stress_','sustained_')):
                assert r['repeats']==16 and r['warmup']==64 and r['tool']=='clean' and r['validation']['pass'] and len(rows)==1024
            inventory[case+'/'+d.name]={'receipt_sha256':sha(d/'receipt.json'),'samples_sha256':sha(d/'result.csv'),'queries':len(rows),'tool':r['tool']}
        shape=read(p/'runs/smoke_C/result.shape.json');assert shape['n']==n and shape['bundle']==k
        if partial:
            result[case]={'shape':shape,'fixture_hashes':manifest['file_sha256'],'cpu_oracle_sha256':oracle_record['oracle_sha256'],
                          'status':'unvalidated performance: interrupted during second round; correctness/sanitizer/stress passed',
                          'missing_runs':sorted(required(n,k)-observed),'graph_speedup_gate_pass':False,'nsys':None}
            continue
        modes={};times={}
        for m in 'ABC':
            vals=[read(p/f'runs/timing_{i}_{m}/result.json') for i in range(6)]
            receipts=[read(p/f'runs/timing_{i}_{m}/receipt.json') for i in range(6)]
            assert all(v['queries']==256 and v['radius']==4 and v['n']==n and v['bundle']==k and v['mode']==m for v in vals)
            assert all(r['tool']=='clean' and r['warmup']==64 and r['validation']['pass'] for r in receipts)
            times[m]=[v['sum_query_s']*1e6/v['queries'] for v in vals]
            samples=[[float(r['query_us']) for r in csvrows(p/f'runs/timing_{i}_{m}/result.csv')] for i in range(6)]
            assert all(math.isclose(st.mean(s),t,rel_tol=1e-9) for s,t in zip(samples,times[m]))
            modes[m]={'process_mean_amortized_query_us':times[m],'median_mean_amortized_query_us':st.median(times[m]),
                      'median_mean_bundle_ms':st.median(times[m])*k/1000,
                      'process_p10_p50_p90_amortized_us':[[small.percentile(s,q) for q in [.1,.5,.9]] for s in samples],
                      'loop_cpu_us_per_query':[v['loop_cpu_s']*1e6/v['queries'] for v in vals],
                      'loop_cpu_one_core_percent':[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vals],
                      'whole_process_telemetry':[telemetry(p/f'runs/timing_{i}_{m}/gpu.csv') for i in range(6)],
                      'setup_us':[v['setup_s']*1e6 for v in vals],'capture_instantiate_us':[v['capture_instantiate_s']*1e6 for v in vals],
                      'first_bundle_us':[v['first_bundle_s']*1e6 for v in vals],'build_s':[v['build_s'] for v in vals]}
        paired=small.paired_interval(times['B'],times['C']);sustained=[]
        for i in range(2):
            v={m:read(p/f'runs/sustained_{i}_{m}/result.json') for m in 'BC'}
            t={m:x['sum_query_s']*1e6/x['queries'] for m,x in v.items()}
            sustained.append({'order':['BC','CB'][i],'amortized_query_us':t,'B_over_C':t['B']/t['C']})
        accepted=paired['wins']==6 and paired['bootstrap_95'][0]>1.05 and all(s['B_over_C']>=1/1.05 for s in sustained)
        prof=None
        if n==611756 and k in [1,32] and not interruption:
            assert read(p/'profile_complete.json')['complete']
            prof={m:profile(p/f'runs/nsys_{m}/trace.sqlite',k,shape['slots']) for m in 'BC'}
            assert prof['B']['signature']==prof['C']['signature']
            assert prof['B']['explicit_query_copies']==prof['C']['explicit_query_copies']
        result[case]={'shape':shape,'fixture_hashes':manifest['file_sha256'],'cpu_oracle_sha256':oracle_record['oracle_sha256'],
                      'status':'timing and sustained complete; NSYS pending' if n==611756 and k==1 and interruption else 'required shape gates complete',
                      'missing_runs':sorted(required(n,k)-observed),
                      'results':modes,'B_over_C_median_ratio':st.median(times['B'])/st.median(times['C']),
                      'A_over_B_median_ratio':st.median(times['A'])/st.median(times['B']),
                      'paired_rounds':[{'order':order,'B_over_C':times['B'][i]/times['C'][i]} for i,order in enumerate(ORDERS)],
                      'paired_B_over_C':paired,'sustained':sustained,'graph_speedup_gate_pass':accepted and not (n==611756 and k==1 and interruption),'nsys':prof}
    return {'experiment':'gts_20260923_graph_scale_words','scope':'Configured native functions versus scaled fixed stream and same-enqueue Graph; serial K-query bundles; full ordered host output, radius4',
            'hardware':{'gpu':'RTX PRO 6000 Blackwell Server Edition','physical_device':0,'driver':'590.48.01','cuda':'13.1.115','arch':'sm_120','settings_changed':False},
            'source_revision':'3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639','original_source_hashes_verified':True,
            'binary_sha256':binary,'source_sha256':sha(root/'graph_bench.cu'),'raw_archive_sha256':sha(archive),
            'orders':ORDERS,'queries_per_primary_process':256,'warmup_queries':64,'full_output_runs':full_runs,'sanitizer_runs':san_runs,
            'completion_status':'interrupted; five complete timing shapes, K32 incomplete, NSYS uncollected' if interruption else 'complete',
            'interruption':interruption,'planned_runs':sum(len(required(int(c.split('_')[0][1:]),int(c.split('_k')[1]))) for c in CASES),'observed_runs':len(inventory),
            'cases':result,'run_inventory':inventory,
            'claim_boundary':'No query-parallel batching, no graph algorithm novelty, no fusion, no update or service certification; NSYS times are diagnostic only'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('archive',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    r=analyze(a.root,a.archive);a.out.write_text(json.dumps(r,indent=2)+'\n')
    for n,v in r['cases'].items():
        print(n,{m:round(x['median_mean_amortized_query_us'],3) for m,x in v.get('results',{}).items()},v.get('B_over_C_median_ratio'),v['graph_speedup_gate_pass'])
