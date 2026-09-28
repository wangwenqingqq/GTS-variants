#!/usr/bin/env python3
"""Audit every run, then summarize paired complete-query timings."""
import argparse,csv,hashlib,itertools,json,math,re,sqlite3,statistics as st
from pathlib import Path
from prepare import HERE,driver,scale,sha
from suite import DATASETS,STAGES,rows,verify_stage,repeats
from verify import read,clean,full,radii
def percentile(xs,p):
    xs=sorted(xs);return xs[min(len(xs)-1,math.ceil(p*len(xs))-1)]
def pair(c,e):
    logs=[math.log(x/y) for x,y in zip(c,e)]
    boots=sorted(math.exp(st.mean(x)) for x in itertools.product(logs,repeat=6))
    return {'ratio_of_medians':st.median(c)/st.median(e),'paired_geomean':math.exp(st.mean(logs)),
            'bootstrap_95':[percentile(boots,.025),percentile(boots,.975)],'wins':sum(x>y for x,y in zip(c,e)),
            'round_ratios':[x/y for x,y in zip(c,e)],'method':'exact 6^6 paired log-ratio bootstrap'}
def process(p):
    v=read(p/'result.json');sample=list(csv.DictReader((p/'result.csv').open()));us=[float(x['query_us']) for x in sample]
    mean=v['sum_query_s']*1e6/v['queries']
    assert len(us)==v['queries'] and math.isclose(st.mean(us),mean,rel_tol=1e-9)
    return {'mean_us':mean,'query_p10_p50_p90_us':[percentile(us,q) for q in [.1,.5,.9]],
            'queries':v['queries'],'setup_us':v['setup_s']*1e6,'capture_us':v['capture_instantiate_s']*1e6,
            'first_us':v['first_query_s']*1e6,'setup_first_amortized_us':(v['setup_s']+v['first_query_s']+v['sum_query_s'])*1e6/v['queries'],
            'cpu_one_core_percent':100*v['loop_cpu_s']/v['loop_wall_s']}
def profile(p):
    with sqlite3.connect(p) as db:
        rs=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,x in enumerate(rs) if x[0].startswith('initQnode('));rs=rs[first:]
        assert len(rs)%17==0;k=len(rs)//17;sig=[list(x[:-1]) for x in rs[:k]]
        assert all([list(x[:-1]) for x in rs[i:i+k]]==sig for i in range(0,len(rs),k))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
        apis=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        assert apis['cudaGraphLaunch_v10000']==17
        return {'kernels_per_query':k,'query_instances':17,'signature':sig,
                'kernel_sum_us':sum(x[-1] for x in rs)/17000,
                'selected_kernel_us':{name:sum(x[-1] for x in rs if name in x[0])/17000 for name in ['getQresultCount(','fusedResultSelect(']},
                'sqlite_sha256':sha(p)}
def main(root,out):
    prereg=read(root/'preregistration.json');assert prereg==read(HERE/'PREREGISTRATION.json')
    for name,h in prereg['generated_sha256'].items():assert sha(root/name)==h,name
    assert (root/'graph_bench.cu').read_text()==driver()
    assert (root/'run.py').read_text()==scale.runner()
    pins=read(root/'source_pins.json')
    for name,h in pins.items():assert sha(root/'source'/name.removeprefix('GTS/'))==h
    for d,files in prereg['fixture_sha256'].items():
        for name,h in files.items():assert sha(root/'data'/d/'fixtures'/name)==h,(d,name)
    pre=read(root/'logs/preflight.json');assert pre['all_preregistered_hashes_match']
    for name,h in pre['binary_sha256'].items():assert sha(root/'bin'/name)==h
    for name,h in pre['static_sha256'].items():assert sha(root/'static'/name)==h
    assert pre['binary_sha256']['graph_bench_anchor']==prereg['legacy_binary_sha256']
    assert 'REG:' in pre['selector_resource'] and 'STACK:0' in pre['selector_resource'] and 'LOCAL:0' in pre['selector_resource']
    admission=read(root/'logs/admission.json');gpu=admission['state']['gpu'].split(',')[1].strip()
    assert not admission['state']['apps'].strip() and gpu in pre['hardware']
    assert read(root/'logs/COMPLETE.json')['runs']==sum(len(rows(s,root)) for s in STAGES)==162
    for stage in STAGES:
        verify_stage(root,stage)
        expected=[read(root/'data'/r[0]/'runs'/r[1]/'receipt.json') for r in rows(stage,root)]
        actual=[json.loads(line) for line in (root/'logs'/f'{stage}.txt').read_text().splitlines() if line.startswith('{')]
        assert actual==expected,stage
    result={'experiment':prereg['experiment'],'state':'complete bounded four-dataset result-fusion comparison',
            'scope':'N2000 batch1 Graph C/E, original traversal and layout, complete hot host-ready query, no setup/tree',
            'hardware':{'gpu_index':5,'gpu_name':pre['hardware'].split(', ')[2],'driver':pre['hardware'].split(', ')[3],
                        'compute_cap':pre['hardware'].split(', ')[4],'cuda':'13.1.115','cpu':'shared/unpinned','clocks':'unchanged/uncontrolled'},
            'binary_sha256':pre['binary_sha256'],'static_sha256':pre['static_sha256'],'selector_resource':pre['selector_resource'],
            'runs':162,'orders':['CE','EC']*3,'data':{},'ledger':{}}
    gaps=[];no_checks=0
    for d in DATASETS:
        path=root/'data'/d;fixture=read(path/'fixtures/oracle.json');valid=full(path,d)
        expected={r[1]:r for stage in STAGES for r in rows(stage,root) if r[0]==d}
        assert {p.name for p in (path/'runs').iterdir()}==set(expected)
        gold_files={f'{r:g}':read(path/'fixtures'/f'expected_{r:g}.json') for r in radii(fixture,d).values()}
        for label,r in expected.items():
            p=path/'runs'/label;x=read(p/'receipt.json');clean(x)
            assert x['input_sha256']=={n:sha(path/'fixtures'/n) for n in ['data.txt',x['qfile']]}
            for phase in ['before','after']:
                snap=read(p/f'{phase}.json');assert not snap['apps'].strip() and gpu in snap['gpu']
            checks=read(p/'checks.json');assert all(not c['foreign'] for c in checks)
            times=[0]+[c['elapsed_s'] for c in checks]+[x['wall_s']];gaps.extend(b-a for a,b in zip(times,times[1:]));no_checks+=not bool(checks)
            samples=list(csv.DictReader((p/'result.csv').open()));qs=list(map(int,(path/'fixtures'/x['qfile']).read_text().split()));assert qs.pop(0)==len(qs)
            assert [int(v['qid']) for v in samples]==qs*x['repeats']
            gold=gold_files[f"{x['radius']:g}"]
            assert all([int(v['count']),v['ordered_hash']]==gold[v['qid']] for v in samples),(d,label)
            process(p)
            result['ledger'][f'{d}/{label}']={'receipt_sha256':sha(p/'receipt.json'),'samples_sha256':sha(p/'result.csv')}
        primary={m:[process(path/'runs'/f'timing_{i}_{m}') for i in range(6)] for m in 'CE'}
        paired=pair([x['mean_us'] for x in primary['C']],[x['mean_us'] for x in primary['E']])
        sustained=[{m:process(path/'runs'/f'sustained_{i}_{m}') for m in 'CE'} for i in range(2)]
        for v in sustained:v['C_over_E']=v['C']['mean_us']/v['E']['mean_us']
        traces={m:profile(path/'runs'/f'nsys_{m}/trace.sqlite') for m in 'CE'}
        sig={m:traces[m]['signature'] for m in 'CE'};leaf=next(i for i,x in enumerate(sig['C']) if 'leafProcessRnnUpdate(' in x[0])+1
        assert sig['C'][:leaf]==sig['E'][:leaf]
        assert 'fusedResultSelect(' in sig['E'][-1][0] and 'projectBounded(' in sig['C'][-1][0]
        assert 'getQresultCount(' in ' '.join(x[0] for x in sig['C']) and not any('getQresultCount(' in x[0] for x in sig['E'])
        deletion=sig['E'][leaf:-1];assert sig['C'][-len(deletion)-1:-1]==deletion
        assert traces['C']['kernels_per_query']==24 and traces['E']['kernels_per_query']==17
        hits=[int(v['count']) for v in csv.DictReader((path/'runs/full_normal_C/result.csv').open())]
        record={'dataset':d,'n':2000,'dimension':None if d=='Words' else fixture['dimension'],
                'metric':'byte edit distance' if d=='Words' else 'float32 L2','normal_radius':radii(fixture,d)['normal'],
                'query_ids_sha256':sha(path/'fixtures/queries.qid'),'data_sha256':sha(path/'fixtures/data.txt'),
                'oracle_sha256':sha(path/'fixtures/oracle.json'),'full_verification':valid,
                'hit_median':st.median(hits),'hit_min':min(hits),'hit_max':max(hits),
                'primary':primary,'paired':paired,'sustained':sustained,'nsys':traces,'host_output_bytes':4+2220*8}
        if d=='Words':
            anchor={m:[process(path/'runs'/f'anchor_timing_{i}_{m}') for i in range(6)] for m in 'CE'}
            record['legacy_anchor']={'primary':anchor,'paired':pair([x['mean_us'] for x in anchor['C']],[x['mean_us'] for x in anchor['E']])}
        result['data'][d]=record
    result['safety']={'max_sample_gap_s':max(gaps),'median_sample_gap_s':st.median(gaps),'runs_without_inprocess_checks':no_checks}
    out.write_text(json.dumps(result,indent=2)+'\n')
    for d,v in result['data'].items():print(d,{m:st.median(x['mean_us'] for x in v['primary'][m]) for m in 'CE'},v['paired'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.root.resolve(),a.output)
