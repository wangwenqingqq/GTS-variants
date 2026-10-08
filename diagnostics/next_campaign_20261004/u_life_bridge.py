#!/usr/bin/env python3
"""One native range/update workspace lifetime experiment; reuse existing U10 oracle."""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import numpy as np

NAMES = ('search_num', 'result_num', 'query_node_list', 'qnode_idx', 'qnode_count',
         'qnode_count_prefix', 'init_result_id', 'init_result_dis', 'qresult_idx', 'query_lnode', 'query_qid')
SEEDS = (2026100431, 2026100432, 2026100433)


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')


def kernels(text):
    result=[]
    for m in re.finditer(r'__global__\s+void\s+\w+\s*\(',text):
        start=text.index('{',m.end());depth=1;end=start+1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        result.append(text[m.start():end])
    return result


def prepare(a):
    src=a.workflow/'native_timed/source';dst=a.dest/'native_timed/source'
    assert not dst.exists(),'do not overwrite a measured source'
    shutil.copytree(src,dst)
    shutil.copy2(Path(__file__).with_name('u_life_workspace.hpp'),dst/'include/u_life_workspace.hpp')
    f=dst/'include/update.cuh';s=f.read_text();left=s.index('void searchIndexRnnUpdate(');right=s.index('void updateIndexRnn(',left)
    body=s[left:right]
    for i,name in enumerate(NAMES):
        pattern=r'CHECK\(cudaMalloc(Managed)?\(\(void \*\*\)&'+name+r', (.*?)\)\);'
        body,count=re.subn(pattern,lambda m:f'u_life.acquire((void **)&{name}, {i}, {m[2]}, {"true" if m[1] else "false"});',body)
        assert count==1,(name,'allocation')
        old=f'cudaFree({name});';assert body.count(old)==1
        body=body.replace(old,f'u_life.release({name}, {i});')
    f.write_text(s[:left]+body+s[right:])
    f=dst/'src/main.cu';s=f.read_text().replace('#include "u10_trace.hpp"','#include "u10_trace.hpp"\n#include "u_life_workspace.hpp"')
    s=s.replace('u10_ck(cudaFree(nullptr));auto start=U10Clock::now();','u10_ck(cudaFree(nullptr));auto life_begin=U10Clock::now();auto start=life_begin;')
    s=s.replace('    u10.begin();','    u_life.setup_ms=u10_ms(life_begin);\n    u10.begin();')
    s=s.replace('    start=U10Clock::now();\n    for(void* p:', '    start=U10Clock::now();\n    u_life.finish();\n    for(void* p:')
    s=s.replace('u10.write(argv[5]);return 0;','u10.write(argv[5]);u_life.write(argv[5]);return 0;')
    f.write_text(s)
    # Permit only the targeted smaller lifecycle checks using the same adapter.
    f=dst/'include/u10_trace.hpp';s=f.read_text()
    s=s.replace('bool tree_audit=', 'int expected_queries=0, expected_events=0;\n    bool tree_audit=')
    s=s.replace('if(n!=1000 || q!=10000 || events!=12000)', 'expected_queries=q;expected_events=events;\n        if(n!=1000 || q<1 || q>10000 || events<1 || events>12000)')
    s=s.replace('queries.size()!=10000 || (observe && operations.size()!=12000)', 'queries.size()!=size_t(expected_queries) || (observe && operations.size()!=size_t(expected_events))')
    f.write_text(s)
    matched=0
    for old in src.rglob('*.cuh'):
        new=dst/old.relative_to(src)
        assert kernels(old.read_text())==kernels(new.read_text()),old.name
        matched+=len(kernels(old.read_text()))
    binary=a.dest/'native_timed/u_life_bridge'
    cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-arch=sm_120','-rdc=true','-lineinfo',
         '-Xnvlink=--ignore-host-info','-I'+str(dst/'include'),str(dst/'src/main.cu'),'-o',str(binary)]
    with (a.dest/'BUILD.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    save(a.dest/'SOURCE.json',{'baseline_source_manifest_sha256':sha(a.workflow/'native_timed/SOURCE.json'),
         'binary_sha256':sha(binary),'kernel_bodies_equal':matched,
         'sources':{str(p.relative_to(dst)):sha(p) for p in dst.rglob('*') if p.is_file()},
         'build':cmd,'workspace_names':NAMES})
    (a.dest/'native').symlink_to(a.workflow/'native',target_is_directory=True)


def run(a,label,case,mode,observe=True,tool=None,audit=False):
    target=a.dest/'native_timed'/label
    run_dir=a.dest/'runs'/label
    assert not run_dir.exists(),'failed/previous run retained; no automatic rerun'
    binary=a.dest/'native_timed/u_life_bridge'
    assert sha(binary)==read(a.dest/'SOURCE.json')['binary_sha256']
    env={'U10_LIFE':str(int(mode=='U_LIFE')),'U10_OBSERVE':str(int(observe)),'U10_TREE_AUDIT':str(int(audit))}
    cmd=[str(binary),str(case/'data.txt'),str(case/'events.txt'),'2',str(read(case/'expected.json')['radius']),str(target)]
    if tool:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','77',*cmd]
    reg={'label':label,'mode':mode,'observe':observe,'source_sha256':sha(a.dest/'SOURCE.json'),
         'binary_sha256':sha(binary),'data_sha256':sha(case/'data.txt'),'events_sha256':sha(case/'events.txt'),
         'expected_sha256':sha(case/'expected.json'),'command':cmd,'environment':env}
    save(a.dest/'registrations'/(label+'.json'),reg)
    subprocess.run([sys.executable,str(a.raw/'run_locked.py'),'--gpu',a.gpu,'--output',str(run_dir),
                    '--timeout-seconds','1200','--',*cmd],env={**os.environ,**env},check=True,stdout=subprocess.DEVNULL)
    assert read(run_dir/'receipt.json')['runtime_valid']
    if tool:
        text=(run_dir/'stdout.log').read_text()+(run_dir/'stderr.log').read_text()
        assert 'ERROR SUMMARY: 0 errors' in text,text[-2000:]
    if case.parent==a.dest/'native':
        sys.path.insert(0,str(a.raw));import u10_native
        u10_native.ROOT=a.dest
        result=u10_native.check_timed(a,case.name,label)
    else:result=check_small(a,case,target,run_dir,audit)
    result['mode']=mode;result['workspace']=read(str(target)+'.workspace.json')
    result['registration_sha256']=sha(a.dest/'registrations'/(label+'.json'))
    save(str(target)+'.CHECK.json',result)
    print(label,'PASS',round(result['summary']['trace_ms'],3),flush=True)
    return result


def small_cases(a):
    source=a.workflow/'native/2026100431/data.txt';data=np.loadtxt(source,skiprows=1,dtype=np.int64)
    norms=(data*data).sum(1);sq=norms[:,None]+norms[None,:]-2*(data@data.T)
    # Duplicate logical occurrence; last buffer delete; occupancy9->10;
    # deleted-base empty query; physical-row reinsertion after rebuilding.
    ops=[(2,0),(0,0),(2,0),(0,0),(1,0),(2,0),(1,999),(2,0),(1,999),(2,0)]
    ops += [(0,0)]*9+[(2,0),(0,0),(2,0),(1,0),(2,0)]
    ops += [(0,1),(2,1),(1,1008),(2,1)]
    ops += [(1,0)]*10
    ops += [(0,0)]*9+[(2,0),(0,0),(2,0)]
    ops += [(2,999)]*7
    cases=[]
    for radius in (0,10000):
        case=a.dest/'boundaries'/str(radius);case.mkdir(parents=True)
        shutil.copy2(source,case/'data.txt');base=np.arange(1000);alive=np.ones(1000,dtype=bool);buf=[];expected=[];states=[];builds=[base.tolist()]
        for step,(flag,idx) in enumerate(ops):
            before=(len(base),len(buf));rebuilt=False
            if flag==0:
                buf.append(int(base[idx]))
                if len(buf)==10:
                    base=np.r_[base[alive],buf];alive=np.ones(len(base),dtype=bool);buf=[];builds.append(base.tolist());rebuilt=True
            elif flag==1:
                live=np.flatnonzero(alive)
                if idx<len(live):alive[live[idx]]=False
                else:buf.pop(idx-len(live))
            else:
                live=np.r_[base[alive],np.array(buf,dtype=np.int64)];dist=sq[base[idx],live];ids=np.flatnonzero(dist<=radius**2)
                expected.append({'step':step,'qid':idx,'tree_size':len(base),'buffer':len(buf),'ids':ids.tolist(),
                    'distances':np.sqrt(dist[ids].astype(np.float64)).astype(np.float32).tolist()})
            states.append({'step':step,'flag':flag,'base_before':before[0],'buffer_before':before[1],
                           'base_after':len(base),'buffer_after':len(buf),'rebuilt':rebuilt})
        (case/'events.txt').write_text(str(len(ops))+'\n'+''.join(f'{f} {i}\n' for f,i in ops))
        save(case/'expected.json',{'radius':radius,'expected':expected,'states':states,'builds':builds})
        cases.append(case)
    return cases


def check_small(a,case,target,run_dir,audit):
    ref=read(case/'expected.json');ids=np.fromfile(str(target)+'.ids.i32',dtype='<i4');fields=np.fromfile(str(target)+'.dist.f32',dtype='<f4')
    with open(str(target)+'.queries.csv') as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(ref['expected'])
    offset=0
    for r,e in zip(rows,ref['expected']):
        assert all(int(r[k])==e[k] for k in ('step','qid','tree_size','buffer'))
        n=int(r['count']);assert int(r['offset'])==offset and n==len(e['ids'])
        got=ids[offset:offset+n];assert collections.Counter(map(int,got))==collections.Counter(e['ids'])
        want=dict(zip(e['ids'],e['distances']))
        assert all(v.tobytes()==np.float32(want[int(i)]).tobytes() for i,v in zip(got,fields[offset:offset+n]))
        offset+=n
    assert offset==len(ids)==len(fields)
    with open(str(target)+'.ops.csv') as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(ref['states'])
    for r,e in zip(rows,ref['states']):
        assert all(int(r[k])==e[k] for k in e if k!='rebuilt')
        assert (float(r['rebuild_ms'])>0)==e['rebuilt']
    checks=0
    if audit:
        sys.path.insert(0,str(a.u0));import u0
        trees=[json.loads(l[8:]) for l in (run_dir/'stdout.log').read_text().splitlines() if l.startswith('U0_TREE ')]
        assert len(trees)==len(ref['builds'])
        data=np.loadtxt(case/'data.txt',skiprows=1,dtype=np.int64).tolist()
        checks=sum(u0.tree_audit(t,[data[i] for i in b]) for t,b in zip(trees,ref['builds']))
    return {'state':'correctness_passed','summary':read(str(target)+'.summary.json'),'ancestor_member_checks':checks,
            'outputs':{s:sha(str(target)+s) for s in ('.ids.i32','.dist.f32','.queries.csv')},
            'quality':'independent integer multiset oracle; full live-rank IDs and exact FP32; all states checked'}


def equal_output(x,y):return all(x['outputs'][s]==y['outputs'][s] for s in ('.ids.i32','.dist.f32','.queries.csv'))


def paired(ratios,seed=20261003,resamples=20000):
    rng=np.random.default_rng(seed);logs=np.log(ratios);draws=logs[rng.integers(0,len(logs),(resamples,len(logs)))].mean(1)
    lo,hi=np.quantile(np.exp(draws),[.025,.975])
    return {'geomean':float(np.exp(logs.mean())),'CI95':[float(lo),float(hi)],
            'wins':sum(v>1 for v in ratios),'raw_ratios':ratios,
            'base_first_geomean':math.exp(sum(math.log(v) for v in ratios[::2])/3),
            'life_first_geomean':math.exp(sum(math.log(v) for v in ratios[1::2])/3)}


def campaign(a):
    (a.dest/'registrations').mkdir(exist_ok=True)
    registration={'seeds':SEEDS,'first_seed':SEEDS[0],'pairs':6,'orders':'BASE,LIFE / LIFE,BASE alternating',
                  'controller_sha256':sha(__file__),'runner_sha256':sha(a.raw/'run_locked.py'),
                  'oracle_adapter_sha256':sha(a.raw/'u10_native.py'),
                  'source_sha256':sha(a.dest/'SOURCE.json'),'binary_sha256':read(a.dest/'SOURCE.json')['binary_sha256'],
                  'observer':'six fresh on/off pairs per mode/seed; exact output hashes, original one-sided upper95<=1.03; no reruns',
                  'estimator':'paired geometric BASE/LIFE, NumPy seed20261003/20000 resamples, two-sided95 CI; order split',
                  'expansion':'full-trace lower95>1.03 and >=5/6 wins, setup+trace same gate; no material maintenance regression',
                  'material_maintenance_regression':'insert/delete p99 LIFE/BASE median across six pairs >1.03',
                  'max_perf_processes':36,'setup':'context excluded; lazy workspace growth in trace; final release inside trace',
                  'inputs':{str(s):{'events_sha256':sha(a.dest/'native'/str(s)/'events.txt'),
                                   'expected_sha256':sha(a.dest/'native'/str(s)/'expected.json')} for s in SEEDS}}
    save(a.dest/'REGISTERED.json',registration)
    boundaries=[]
    for case in small_cases(a):
        pair=[run(a,'boundary_'+case.name+'_'+m,case,m,audit=True) for m in ('U_BASE','U_LIFE')]
        assert equal_output(*pair);boundaries+=pair
    case=a.dest/'boundaries/0'
    for tool in ('memcheck','synccheck'):boundaries.append(run(a,'boundary_'+tool,case,'U_LIFE',tool=tool))
    save(a.dest/'BOUNDARIES.json',boundaries)
    results=[]
    for seed in SEEDS:
        case=a.dest/'native'/str(seed);qualification=[];admitted=True
        for mode in ('U_BASE','U_LIFE'):
            controls=[];ratios=[];same=True
            for r in range(1,7):
                pair={}
                for on in ([True,False] if r%2 else [False,True]):
                    x=run(a,f'cost_{seed}_{mode}_r{r}_{"on" if on else "off"}',case,mode,on)
                    pair[on]=x;controls.append(x)
                    save(a.dest/f'COST_ROWS_{seed}_{mode}.json',controls)
                same &= equal_output(pair[True],pair[False]);ratios.append(pair[True]['summary']['trace_ms']/pair[False]['summary']['trace_ms'])
            # Reuse the original U10 cost bootstrap, without importing a GPU backend.
            rng=random.Random(2026100441);logs=list(map(math.log,ratios))
            means=sorted(math.exp(sum(rng.choice(logs) for _ in logs)/len(logs)) for _ in range(10000))
            q={'mode':mode,'raw_ratios':ratios,'upper95':means[9750],'output_equal':same,'admitted':same and means[9750]<=1.03}
            qualification.append(q);admitted &= q['admitted'];print('OBSERVER',seed,q,flush=True)
        save(a.dest/f'COST_QUALIFICATION_{seed}.json',qualification)
        if not admitted:
            save(a.dest/'COMPLETE.json',{'state':'observer_rejected','seed':seed,'results':results});return
        rows=[];pairs=[]
        for r in range(1,7):
            pair={}
            for mode in (('U_BASE','U_LIFE') if r%2 else ('U_LIFE','U_BASE')):
                pair[mode]=run(a,f'perf_{seed}_r{r}_{mode}',case,mode);rows.append(pair[mode])
                save(a.dest/f'PERF_ROWS_{seed}.json',rows)
            assert equal_output(pair['U_BASE'],pair['U_LIFE']);pairs.append(pair)
        report={'seed':seed,'pairs':6,'observer':qualification}
        for key in ('trace_ms','setup_plus_trace_ms'):
            report[key]=paired([p['U_BASE']['summary']['trace_ms']/p['U_LIFE']['summary']['trace_ms'] if key=='trace_ms' else
                                p['U_BASE']['workspace'][key]/p['U_LIFE']['workspace'][key] for p in pairs])
        report['maintenance_p99_ratios']={name:float(np.median([p['U_LIFE']['summary']['latency_ms'][name]['p99']/p['U_BASE']['summary']['latency_ms'][name]['p99'] for p in pairs])) for name in ('insert','delete')}
        report['expand']=all(report[key]['CI95'][0]>1.03 and report[key]['wins']>=5 for key in ('trace_ms','setup_plus_trace_ms')) and max(report['maintenance_p99_ratios'].values())<=1.03
        results.append(report);save(a.dest/'RESULTS.json',results);print('PERF',json.dumps(report),flush=True)
        if not report['expand']:break
    save(a.dest/'COMPLETE.json',{'state':'completed','results':results,'perf_processes':12*len(results),
                               'retain':len(results)==3 and all(r['expand'] for r in results)})


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','campaign'])
    for name in ('raw','workflow','dest','u0'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gpu',required=True);a=p.parse_args()
    a.dest.mkdir(parents=True,exist_ok=True)
    {'prepare':prepare,'campaign':campaign}[a.phase](a)


if __name__=='__main__':main()
