#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,re,sqlite3,statistics as st,sys
from pathlib import Path
from prepare import HERE,driver,selector,runner,test_selector
from suite import SIZES,STAGES,rows,verify_stage,repeats
from verify import sha,clean,full
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
# Avoid this file's module name colliding with the older analysis helper.
from prepare import load
helpers=load('scale_pair_helpers',HERE.parent/'graph_query_20260923/analyze.py')

def read(p):return json.loads(p.read_text())
def profile(p):
    with sqlite3.connect(p) as db:
        rs=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,r in enumerate(rs) if r[0].startswith('initQnode('));rs=rs[first:]
        assert len(rs)%17==0;k=len(rs)//17;sig=[list(x[:-1]) for x in rs[:k]]
        assert all([list(x[:-1]) for x in rs[i:i+k]]==sig for i in range(0,len(rs),k))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
        apis=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        assert apis['cudaGraphLaunch_v10000']==17
        return dict(kernels_per_query=k,queries=17,signature=sig,mean_kernel_sum_us=sum(r[-1] for r in rs)/17000,
                    selected_kernel_us={name:sum(r[-1] for r in rs if name in r[0])/17000 for name in ['getQresultCount(','fusedResultSelect(']},sqlite_sha256=sha(p))
def process(p):
    v=read(p/'result.json');samples=list(csv.DictReader((p/'result.csv').open()))
    us=[float(x['query_us']) for x in samples];mean=v['sum_query_s']*1e6/v['queries']
    assert len(us)==v['queries'] and math.isclose(st.mean(us),mean,rel_tol=1e-9)
    return dict(mean_us=mean,query_p10_p50_p90_us=[helpers.percentile(us,q) for q in [.1,.5,.9]],
                queries=v['queries'],setup_us=v['setup_s']*1e6,capture_us=v['capture_instantiate_s']*1e6,
                first_us=v['first_query_s']*1e6,setup_first_amortized_us=(v['setup_s']+v['first_query_s']+v['sum_query_s'])*1e6/v['queries'],cpu_one_core_percent=100*v['loop_cpu_s']/v['loop_wall_s'])
def pair(c,e):
    v=helpers.paired_interval(c,e);v['ratio_of_medians']=st.median(c)/st.median(e);return v
def main(root,out):
    prereg=read(root/'preregistration.json');assert prereg==read(HERE/'PREREGISTRATION.json')
    for name,h in prereg['generated_sha256'].items():assert sha(root/name)==h,name
    for name,value in [('graph_bench.cu',driver()),('fused_result.cuh',selector()),('test_selector.cu',test_selector()),('run.py',runner())]:assert (root/name).read_text()==value,name
    for name in ['suite.py','verify.py','CONTRACT.md']:assert sha(root/name)==sha(HERE/name)
    pins={k:v for k,v in read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256'].items() if k.startswith('GTS/')}
    assert read(root/'source_pins.json')==pins
    for name,h in pins.items():assert sha(root/'source'/name.removeprefix('GTS/'))==h
    pre=read(root/'logs/preflight.json')
    for name,h in pre['binary_sha256'].items():assert sha(root/'bin'/name)==h
    assert pre['binary_sha256']['graph_bench_anchor']==read(HERE.parent/'fused_result_20260923/EVIDENCE.json')['binary_sha256']
    for name,h in pre['static_sha256'].items():assert sha(root/'static'/name)==h
    selected=re.findall(r' Function (\S*fusedResultSelect\S*):\n  ([^\n]+)',(root/'static/resources.txt').read_text())
    assert len(selected)==1
    selector_registers=int(re.search(r'REG:(\d+)',selected[0][1]).group(1))
    admission=read(root/'logs/admission.json');gpu=admission['state']['gpu'].split(',')[1].strip()
    assert not admission['state']['apps'].strip() and pre['hardware'].split(', ')[1]==gpu
    assert 'V13.1.115' in (root/'logs/toolkit.txt').read_text()
    assert read(root/'logs/COMPLETE.json')['runs']==sum(len(rows(s)) for s in STAGES)==307
    for stage in STAGES:
        verify_stage(root,stage)
        expected=[read(root/'data'/str(r[0])/'runs'/r[1]/'receipt.json') for r in rows(stage)]
        actual=[json.loads(line) for line in (root/'logs'/f'{stage}.txt').read_text().splitlines() if line.startswith('{')]
        assert actual==expected,stage
    data={};ledger={};gaps=[];no_checks=0
    for n in SIZES:
        d=root/'data'/str(n);fixture=read(d/'fixtures/oracle.json');assert sha(d/'fixtures/oracle.json')==prereg['fixture_meta_sha256'][str(n)]
        valid=full(d);expected={r[1]:r for stage in STAGES for r in rows(stage) if r[0]==n}
        assert {p.name for p in (d/'runs').iterdir()}==set(expected)
        for label,r in expected.items():
            p=d/'runs'/label;x=read(p/'receipt.json');clean(x)
            assert x['input_sha256']=={name:sha(d/'fixtures'/name) for name in ['data.txt',x['qfile']]}
            for phase in ['before','after']:
                snap=read(p/f'{phase}.json');assert not snap['apps'].strip() and gpu in snap['gpu']
            checks=read(p/'checks.json');assert all(not c['foreign'] for c in checks)
            times=[0]+[c['elapsed_s'] for c in checks]+[x['wall_s']];gaps.extend(b-a for a,b in zip(times,times[1:]));no_checks+=not bool(checks)
            if x['mode']!='T':
                samples=list(csv.DictReader((p/'result.csv').open()));qs=list(map(int,(d/'fixtures'/x['qfile']).read_text().split()));assert qs.pop(0)==len(qs)
                assert [int(v['qid']) for v in samples]==qs*x['repeats']
                gold=read(d/'fixtures'/f"expected_{x['radius']:g}.json")
                assert all([int(v['count']),v['ordered_hash']]==gold[v['qid']] for v in samples)
                process(p)
            ledger[f'{n}/{label}']=dict(receipt_sha256=sha(p/'receipt.json'),samples_sha256=sha(p/'result.csv') if (p/'result.csv').exists() else None)
        stats={m:[process(d/'runs'/f'timing_{i}_{m}') for i in range(6)] for m in 'CE'}
        paired=pair([x['mean_us'] for x in stats['C']],[x['mean_us'] for x in stats['E']])
        sustained=[{m:process(d/'runs'/f'sustained_{i}_{m}') for m in 'CE'} for i in range(2)]
        for v in sustained:v['C_over_E']=v['C']['mean_us']/v['E']['mean_us']
        traces={m:profile(d/'runs'/f'nsys_{m}/trace.sqlite') for m in 'CE'}
        sig={m:traces[m]['signature'] for m in 'CE'};leaf=next(i for i,x in enumerate(sig['C']) if 'leafProcessRnnUpdate(' in x[0])+1
        assert sig['C'][:leaf]==sig['E'][:leaf]
        assert 'fusedResultSelect(' in sig['E'][-1][0] and not any('fusedResultSelect(' in x[0] for x in sig['C'])
        assert sig['E'][-1][4:8]==[512,1,1,selector_registers]
        assert 'getQresultCount(' in ' '.join(x[0] for x in sig['C']) and not any('getQresultCount(' in x[0] for x in sig['E'])
        deletion=sig['E'][leaf:-1];assert sig['C'][-len(deletion)-1:-1]==deletion and 'projectBounded(' in sig['C'][-1][0]
        summary=read(d/'runs/full_4_C/result.json');work={m:list(csv.DictReader((d/'runs'/f'full_4_{m}/result.work.csv').open())) for m in 'CE'}
        assert work['C']==work['E'] and len(work['C'])==64
        cap=prereg['capacities'][str(n)]
        assert (summary['tree_height'],summary['nodes'],summary['slots'])==(cap['height'],cap['nodes'],cap['slots'])
        hits=[int(x['count']) for x in csv.DictReader((d/'runs/full_4_C/result.csv').open())]
        candidates=[int(x['candidates']) for x in work['C']]
        assert fixture['query_source_ids']==read(root/'data/2000/fixtures/oracle.json')['query_source_ids']
        v=dict(n=n,tree={k:summary[k] for k in ['tree_height','nodes','slots','used_nodes','leaves']},full_verification=valid,fixture_sha256=fixture['sha256'],query_source_ids_sha256=hashlib.sha256(json.dumps(fixture['query_source_ids']).encode()).hexdigest(),primary=stats,paired=paired,sustained=sustained,nsys=traces,work=dict(candidates=candidates,hits=hits,candidate_median=st.median(candidates),hit_median=st.median(hits),h2d_bytes=4,d2h_bytes=4+summary['slots']*8))
        if n==2000:
            anchor={m:[process(d/'runs'/f'anchor_timing_{i}_{m}') for i in range(6)] for m in 'CE'}
            v['legacy_anchor']=dict(primary=anchor,paired=pair([x['mean_us'] for x in anchor['C']],[x['mean_us'] for x in anchor['E']]))
        data[str(n)]=v
    fields=pre['hardware'].split(', ')
    result=dict(experiment=prereg['experiment'],state='complete bounded scale experiment; no production promotion',scope='Words radius4 batch1; full hot host-ready query; Graph both arms; original result-fusion algorithm with runtime capacity; no traversal fusion/layout',hardware=dict(gpu_index=int(fields[0]),gpu_name=fields[2],driver=fields[3],compute_cap=fields[4],power_limit=fields[5],cuda='13.1.115',cpu='shared/unpinned',clock_policy='unchanged/uncontrolled'),binary_sha256=pre['binary_sha256'],static_sha256=pre['static_sha256'],selector_resources=selected[0][1],orders=['CE','EC']*3,queries_per_process={n:64*repeats(n) for n in SIZES},runs=307,ledger=ledger,data=data,safety=dict(max_sample_gap_s=max(gaps),median_sample_gap_s=st.median(gaps),runs_without_inprocess_checks=no_checks),contract_sha256=sha(HERE/'CONTRACT.md'))
    out.write_text(json.dumps(result,indent=2)+'\n')
    for n,v in data.items():print(n,{m:st.median(x['mean_us'] for x in v['primary'][m]) for m in 'CE'},v['paired'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.root.resolve(),a.output)
