#!/usr/bin/env python3
"""Fail-closed audit of the million-scale C/E campaign."""
import argparse,csv,itertools,json,math,sqlite3,statistics as st
from pathlib import Path
from prepare import HERE,driver,runner,sha
from suite import DATASETS,SIZES,STAGES,rows,verify_stage
from verify import read,clean,full,qids
def percentile(xs,p):
    xs=sorted(xs);return xs[min(len(xs)-1,math.ceil(p*len(xs))-1)]
def pair(c,e):
    logs=[math.log(x/y) for x,y in zip(c,e)]
    boot=sorted(math.exp(st.mean(x)) for x in itertools.product(logs,repeat=6))
    return {'ratio_of_medians':st.median(c)/st.median(e),'paired_geomean':math.exp(st.mean(logs)),
            'bootstrap_95':[percentile(boot,.025),percentile(boot,.975)],'wins':sum(x>y for x,y in zip(c,e)),
            'round_ratios':[x/y for x,y in zip(c,e)],'method':'exact 6^6 paired log-ratio bootstrap'}
def process(p):
    v=read(p/'result.json');samples=list(csv.DictReader((p/'result.csv').open()))
    us=[float(x['query_us']) for x in samples];mean=v['sum_query_s']*1e6/v['queries']
    # CSV microseconds and JSON seconds are each rounded to three decimal
    # microseconds, so allow their combined sub-0.002 us representation error.
    assert len(us)==v['queries'] and math.isclose(st.mean(us),mean,rel_tol=1e-9,abs_tol=.002)
    return {'mean_us':mean,'query_p10_p50_p90_us':[percentile(us,q) for q in [.1,.5,.9]],'queries':v['queries'],
            'setup_us':v['setup_s']*1e6,'capture_us':v['capture_instantiate_s']*1e6,
            'first_us':v['first_query_s']*1e6,'setup_first_amortized_us':(v['setup_s']+v['first_query_s']+v['sum_query_s'])*1e6/v['queries'],
            'cpu_one_core_percent':100*v['loop_cpu_s']/v['loop_wall_s']}
def profile(p):
    with sqlite3.connect(p) as db:
        rs=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
        first=next(i for i,x in enumerate(rs) if x[0].startswith('initQnode('));rs=rs[first:]
        assert len(rs)%5==0;k=len(rs)//5;sig=[list(x[:-1]) for x in rs[:k]]
        assert all([list(x[:-1]) for x in rs[i:i+k]]==sig for i in range(0,len(rs),k))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
        apis=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
        assert apis['cudaGraphLaunch_v10000']==5
        return {'kernels_per_query':k,'query_instances':5,'signature':sig,
                'kernel_sum_us':sum(x[-1] for x in rs)/5000,
                'selected_kernel_us':{name:sum(x[-1] for x in rs if name in x[0])/5000 for name in ['getQresultCount(','fusedResultSelect(']},
                'sqlite_sha256':sha(p)}
def main(root,out):
    prereg=read(root/'preregistration.json');assert prereg==read(HERE/'PREREGISTRATION.json')
    for name,h in prereg['generated_sha256'].items():assert sha(root/name)==h,name
    assert (root/'graph_bench.cu').read_text()==driver() and (root/'run.py').read_text()==runner()
    for name,h in read(root/'source_pins.json').items():assert sha(root/'source'/name.removeprefix('GTS/'))==h
    pre=read(root/'logs/preflight.json');assert pre['preregistered_files_match'] and pre['all_fixture_hashes_match']
    assert sha(root/'bin/graph_bench')==pre['binary_sha256']
    for name,h in pre['static_sha256'].items():assert sha(root/'static'/name)==h
    admission=read(root/'logs/admission.json');gpu=admission['state']['gpu'].split(',')[1].strip()
    assert not admission['state']['apps'].strip() and gpu in pre['hardware']
    assert read(root/'logs/COMPLETE.json')['runs']==sum(len(rows(s,root)) for s in STAGES)==192
    for stage in STAGES:
        verify_stage(root,stage)
        expected=[read(root/'data'/r[0]/str(r[1])/'runs'/r[2]/'receipt.json') for r in rows(stage,root)]
        actual=[json.loads(line) for line in (root/'logs'/f'{stage}.txt').read_text().splitlines() if line.startswith('{')]
        assert actual==expected,stage
    outv={'experiment':prereg['experiment'],'state':'complete bounded large-scale L2 result-fusion comparison',
          'scope':'N65536/1000000, normal radius fixed from previous N2000 fixture, batch1 Graph C/E, complete hot host-ready query',
          'hardware':{'gpu_index':admission['gpu_index'],'gpu_name':pre['hardware'].split(', ')[2],'driver':pre['hardware'].split(', ')[3],
                      'compute_cap':pre['hardware'].split(', ')[4],'cuda':'13.1.115','cpu':'shared/unpinned','clocks':'unchanged/uncontrolled'},
          'binary_sha256':pre['binary_sha256'],'static_sha256':pre['static_sha256'],'selector_resource':pre['selector_resources'],
          'runs':192,'orders':['CE','EC']*3,'data':{},'ledger':{}}
    gaps=[];no_checks=0
    for d in DATASETS:
        outv['data'][d]={}
        for n in SIZES:
            path=root/'data'/d/str(n);fixture=read(path/'fixtures/oracle.json')
            assert sha(path/'fixtures/oracle.json')==prereg['fixture_meta_sha256'][d][str(n)]
            valid=full(path,d,n);expected={r[2]:r for stage in STAGES for r in rows(stage,root) if r[0]==d and r[1]==n}
            assert {p.name for p in (path/'runs').iterdir()}==set(expected)
            gold=read(path/'fixtures'/f"expected_{fixture['radii']['normal']:g}.json")
            for label,r in expected.items():
                p=path/'runs'/label;x=read(p/'receipt.json');clean(x)
                assert x['input_sha256']['data.f32bin']==fixture['sha256']['data.f32bin']
                assert x['input_sha256'][x['qfile']]==fixture['sha256'][x['qfile']]
                for phase in ['before','after']:
                    snap=read(p/f'{phase}.json');assert not snap['apps'].strip() and gpu in snap['gpu']
                checks=read(p/'checks.json');assert all(not c['foreign'] for c in checks)
                times=[0]+[c['elapsed_s'] for c in checks]+[x['wall_s']];gaps.extend(b-a for a,b in zip(times,times[1:]));no_checks+=not bool(checks)
                samples=list(csv.DictReader((p/'result.csv').open()));qs=qids(path/'fixtures'/x['qfile'])
                assert [int(v['qid']) for v in samples]==qs*x['repeats']
                expected_gold=read(path/'fixtures'/f"expected_{x['radius']:g}.json")
                assert all([int(v['count']),v['ordered_hash']]==expected_gold[v['qid']] for v in samples),(d,n,label)
                process(p)
                outv['ledger'][f'{d}/{n}/{label}']={'receipt_sha256':sha(p/'receipt.json'),'samples_sha256':sha(p/'result.csv')}
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
            summary=read(path/'runs/full_normal_C/result.json');work={m:list(csv.DictReader((path/'runs'/f'full_normal_{m}/result.work.csv').open())) for m in 'CE'}
            assert work['C']==work['E'] and len(work['C'])==8
            hits=[int(x['count']) for x in csv.DictReader((path/'runs/full_normal_C/result.csv').open())]
            candidates=[int(x['candidates']) for x in work['C']]
            entry={'dataset':d,'n':n,'dimension':fixture['dimension'],'normal_radius':fixture['radii']['normal'],
                   'data_sha256':fixture['sha256']['data.f32bin'],'oracle_sha256':fixture['sha256']['oracle.npy'],
                   'query_source_ids_sha256':sha(path/'fixtures/query_source_ids.json'),
                   'tree':{k:summary[k] for k in ['tree_height','nodes','slots','used_nodes','leaves']},
                   'full_verification':valid,'work':{'hit_median':st.median(hits),'candidate_median':st.median(candidates),
                                                      'hits':hits,'candidates':candidates,'d2h_bytes':4+summary['slots']*8},
                   'primary':primary,'paired':paired,'sustained':sustained,'nsys':traces}
            outv['data'][d][str(n)]=entry
    outv['safety']={'max_sample_gap_s':max(gaps),'median_sample_gap_s':st.median(gaps),'runs_without_inprocess_checks':no_checks}
    out.write_text(json.dumps(outv,indent=2)+'\n')
    for d,by in outv['data'].items():
        for n,v in by.items():print(d,n,{m:st.median(x['mean_us'] for x in v['primary'][m]) for m in 'CE'},v['paired'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.root.resolve(),a.output)
