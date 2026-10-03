#!/usr/bin/env python3
"""Frozen E0 only. All GPU jobs use the unchanged P7 exclusive runner."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

P7=Path('/home/data/wangxuran/tmp/gts_unified_knn_p7_20261003')
NATIVE=Path('/home/data/wangxuran/tmp/gts_native_knn_faiss_ivf_20261003')
ROOT=Path('/home/data/wangxuran/tmp/gts_search_ordering_headroom_20261003')
TMP=Path('/home/data/gts_search_ordering_tmp_20261003')
DATA=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/data/GIST/1000000/fixtures/data.f32bin')
PY='/home/data/wangxuran/tmp/gts_p6_cagra_ivf_20261002/faiss_source_venv/bin/python'
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
REF=ROOT/'oracle_GIST_pilot32.json'
WARM=NATIVE/'fixtures/GIST_dev128.qid'
QIDS=P7/'fixtures/GIST_pilot32.qid'
TREE=NATIVE/'GIST.index'
SEEDS=P7/'fixtures/seeds_1000000.i32'
sys.path.insert(0,str(P7))
from qualification import native_ivf,check_output,coverage

SCHEDULE=[
    ['O_BOUND','O_MASK','STAR_SCAN','STAR_MASK','FAISS_FLAT'],
    ['O_MASK','STAR_SCAN','STAR_MASK','FAISS_FLAT','O_BOUND'],
    ['STAR_SCAN','STAR_MASK','FAISS_FLAT','O_BOUND','O_MASK'],
    ['STAR_MASK','FAISS_FLAT','O_BOUND','O_MASK','STAR_SCAN'],
]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()

def save(p,value):Path(p).write_text(json.dumps(value,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')

def locked(label,cmd,env=None):
    target=ROOT/'runs'/label
    if label.startswith('small') and (target/'receipt.json').exists():
        receipt=json.loads((target/'receipt.json').read_text())
        assert receipt['runtime_valid'] and receipt['command'][3:]==list(map(str,cmd))
        assert receipt['binary_sha256']==sha(cmd[0])
        return receipt
    command=[PY,str(P7/'run_locked.py'),'--gpu',GPU,'--output',str(target),'--',*map(str,cmd)]
    subprocess.run(command,check=True,env={**os.environ,'TMPDIR':str(TMP),**(env or {})})
    receipt=json.loads((target/'receipt.json').read_text());assert receipt['runtime_valid']
    return receipt

def table(reference,out,warm_reference=None):
    n,d=reference['N'],reference['D'];values=np.full(n,np.nan,dtype='<f8')
    for ref in [reference]+([warm_reference] if warm_reference else []):
        assert (ref['N'],ref['D'])==(n,d)
        for r in ref['records']:
            u=r['squared'][7];assert u==r['ties']['8']['boundary_squared']
            assert np.isnan(values[r['qid']]) or values[r['qid']]==u
            values[r['qid']]=u
    with Path(out).open('wb') as f:
        np.array([n,d,8],dtype='<i4').tofile(f);values.tofile(f)

def prepare():
    expected={DATA:'f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7',
              TREE:'4fcd14b52ec49bed23a2e49c416a80cee70ce0ed3ea2a436bbb6132dbe4bfed0',
              SEEDS:'1ff926834e564b75a887714ee3a961544440b33a55b41749b8e42c36e3dd1d67',
              QIDS:'5857859ff9e0ba524e6a03733b3d94485c7f52b19919ab7e1e86296910f13941',
              WARM:'9ce0c24bede5a0b8d05facb38903160ad38ba67ca49b226cc72dec584bb544ef',
              P7/'opt_knn_bench':'1a6a63ecd452dda0b67ab6140e394a60c21b9f04280e4643f00b7749a53d0e92',
              P7/'run_locked.py':'c9dffe68de94141feb5ced016bc347524f7f94ef41611eecc9c63f550b0ee7e4',
              P7/'native_knn.py':'9ede21afaf3ec7fe468f5ccdcf052774a5885f8d8e97d9c44e6a7df56fe16cc4',
              P7/'qualification.py':'f2f87a09c215f80dfbea23e6412c0979e051e35d1aba34d18f7ff4f5e9496113',
              NATIVE/'native_ivf.py':'23abd847d013c143cee82a5abc3ec87f1fa3305934ad6a5c8c306a4352daf27b'}
    actual={str(p):sha(p) for p in expected};assert all(actual[str(p)]==v for p,v in expected.items())
    import faiss
    import faiss._swigfaiss as library
    assert faiss.__version__=='1.15.1'
    assert sha(library.__file__)=='55dd5a3f8ab134e66ac41b7509597845d41dde9763c51917fb9a56f01d2f6e01'
    pins={'source_ref':'36d58aeb93844aec3febd17d9f9caf17b88601f0','GPU_UUID':GPU,'NUMA':3,
          'files':actual,'binary_sha256':sha(ROOT/'headroom_bench'),
          'faiss_version':faiss.__version__,'faiss_library_sha256':sha(library.__file__),
          'faiss_use_cuvs':False,'faiss_useFloat16':False,
          'compile_flags':['-O3','-std=c++17','--fmad=false','-arch=sm_120'],
          'gpu':subprocess.check_output(['nvidia-smi','-i',GPU,'--query-gpu=index,uuid,name,driver_version','--format=csv,noheader'],text=True).strip(),
          'topology':subprocess.check_output(['nvidia-smi','topo','-m'],text=True),
          'nvcc':subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),
          'nsys':subprocess.check_output(['nsys','--version'],text=True),
          'clean_schedule':SCHEDULE,'clean_processes':20,'Q_T':2,'depth':4,'seed_M':4096,
          'source_changes':'only runtime cutoff materialization and post-timer diagnostic entry; original kernels unchanged',
          'preserved_previous_gate':'STOP_CURRENT_KNN_PATH'}
    for p in (ROOT/'diagnostics/search_ordering_headroom_20261003').glob('*'):
        if p.is_file():pins['files'][str(p)]=sha(p)
    for p in (ROOT/'diagnostics/unified_knn_e2e_20261003').glob('*.cuh'):pins['files'][str(p)]=sha(p)
    save(ROOT/'SOURCE_PINS.json',pins)
    locked('oracle_regenerate',[PY,NATIVE/'native_ivf.py','oracle','--data',DATA,'--qids',QIDS,'--out',REF])
    ref=json.loads(REF.read_text());prior=json.loads((P7/'oracle_GIST_pilot32.json').read_text())
    assert ref['records']==prior['records'],'regenerated oracle changed'
    warm_ref=NATIVE/'oracle_GIST_dev128.json';warm=json.loads(warm_ref.read_text())
    table(ref,ROOT/'oracle_u.f64',warm)
    for d in (96,960):
        small=json.loads((P7/f'fixtures/cpu_small{d}.json').read_text())
        table(small,ROOT/f'small{d}_u.f64')
    save(ROOT/'ORACLE_MANIFEST.json',{
        'status':'REGENERATED_AND_BITWISE_MATCHES_PINNED_REFERENCE','ref_sha256':sha(REF),
        'prior_sha256':sha(P7/'oracle_GIST_pilot32.json'),'warm_ref_sha256':sha(warm_ref),
        'diagnostic_U_table_sha256':sha(ROOT/'oracle_u.f64'),'oracle_s':ref['oracle_s'],'layout_s':ref['layout_s'],
        'independent_layout':'original-ID SoA; no tree, seeds, masks or cutoff','cpu_spotcheck':ref['cpu_spotcheck'],
        'queries':list(map(int,native_ivf.read_qids(QIDS))),'K':8,
        'per_query':[{'qid':r['qid'],'U_star':r['squared'][7],'topk_ids':r['ids'][:8],'ties':r['ties']['8']} for r in ref['records']],
        'oracle_input_to_STAR':'scalar cutoff only; no neighbor IDs','oracle_input_to_ordinary':'none; command uses dash and null pointer',
        'oracle_diagnostic_tag':'USES_ORACLE_NOT_DEPLOYABLE','excluded_from_STAR_host_ready':['offline oracle construction','static scalar table H2D'],
        'retained_in_STAR_host_ready':['query input','4096 seed distances and seed topK','cutoff materializer','tree if enabled','actual distance verification','complete final GPU topK','all K ID and distance D2H','stream synchronization']})
    print('PREPARE PASS',flush=True)

def command(mode,out,data=DATA,qids=QIDS,tree=TREE,seeds=SEEDS,warm=WARM,oracle=None,force=0,original=False):
    if mode=='FAISS_FLAT':
        return [PY,P7/'native_knn.py','--data',data,'--method',mode,'--qids',qids,'--warm',warm,
                '--reference',REF,'--k','8','--b','32','--out',out]
    cmd=[P7/'opt_knn_bench' if original else ROOT/'headroom_bench',data,qids,tree,seeds,mode,'8','32',out,warm,str(force)]
    if not original:cmd.append(oracle or ROOT/'oracle_u.f64' if mode.startswith('STAR') else '-')
    return cmd

def qualify(out,data=DATA,ref=REF):
    source=native_ivf.load_data(data);reference=json.loads(Path(ref).read_text())
    q=check_output(str(out)+'.bin',source,reference,8,exact=True)
    assert q['complete_gate_pass'] and q['finite_pass'] and q['nonnegative_pass'] and q['nondecreasing_distance_pass'],q
    save(str(out)+'.quality.json',q)
    return q

def audit_work(out,data,ref,index):
    source=native_ivf.load_data(data);n,d=source.shape
    with Path(index).open('rb') as f:f.read(16);order=np.fromfile(f,dtype='<i4',count=n)
    with Path(str(out)+'.coverage.bin').open('rb') as f:
        _,_,q,k=np.fromfile(f,dtype='<i4',count=4);u=np.fromfile(f,dtype='<f8',count=q)
        masks=np.fromfile(f,dtype='u1',count=q*n).reshape(q,n)
        scores=np.fromfile(f,dtype='<f8',count=q*n).reshape(q,n)
    reference=json.loads(Path(ref).read_text());steps=[]
    rows=list(csv.DictReader(Path(str(out)+'.work.csv').open()))
    for i,r in enumerate(reference['records']):
        sums=np.zeros(n,dtype=np.float64);active=masks[i].astype(bool);dimsteps=np.zeros(n,dtype=np.uint64)
        for j in range(d):
            delta=source[order,j].astype(np.float64)-float(source[r['qid'],j]);sums+=delta*delta
            dimsteps[active]+=1
            if j%32==31:active &= sums<=u[i]
        assert int(masks[i].sum())==int(rows[i]['candidate_pairs'])
        assert int(dimsteps.sum())==int(rows[i]['coordinate_updates'])
        assert np.array_equal(scores[i,active],sums[active])
        assert np.isinf(scores[i,~active]).all()
        steps.append(dimsteps)
    for r in csv.DictReader(Path(str(out)+'.pairs.csv').open()):
        a,b=int(r['first_query_index']),int(r['second_query_index'])
        mb=masks[b] if b>=0 else np.zeros(n,dtype='u1');sb=steps[b] if b>=0 else np.zeros(n,dtype='u8')
        assert int((masks[a]|mb).sum())==int(r['union_candidates'])
        assert int(np.maximum(steps[a],sb).sum())==int(r['shared_coordinate_steps'])
    return {'count_vs_CPU_exact':True,'query_rows':q,'union_not_intersection':True,'tail_batch':q%32}

def small():
    rows=[]
    for d in (96,960):
        data=P7/f'fixtures/small{d}.f32bin';index=P7/f'fixtures/small{d}.index';qs=P7/'fixtures/small33.qid'
        ref=P7/f'fixtures/cpu_small{d}.json'
        for mode in ('O_BOUND','O_MASK','STAR_SCAN','STAR_MASK'):
            label=f'small{d}_{mode}';out=ROOT/'evidence'/label
            receipt=locked(label,command(mode,out,data,qs,index,P7/'fixtures/seeds_4097.i32',qs,ROOT/f'small{d}_u.f64'),
                           {'P7_SMALL_AUDIT':'1','HEADROOM_COUNT':'1'})
            q=qualify(out,data,ref)
            c=coverage(str(out)+'.coverage.bin',native_ivf.load_data(data),json.loads(ref.read_text()),index)
            counter=audit_work(out,data,ref,index)
            rows.append({'label':label,'receipt':receipt,'quality':q,'coverage':c,'counter_check':counter})
            print('SMALL PASS '+label,flush=True)
    # Forced keep validates the safe invalid-bound fallback path without changing the normal bound code.
    out=ROOT/'evidence/small960_force_keep'
    receipt=locked('small960_force_keep',command('STAR_MASK',out,data,qs,index,P7/'fixtures/seeds_4097.i32',qs,ROOT/'small960_u.f64',force=1),{'P7_SMALL_AUDIT':'1'})
    rows.append({'label':out.name,'receipt':receipt,'quality':qualify(out,data,ref),
                 'coverage':coverage(str(out)+'.coverage.bin',native_ivf.load_data(data),json.loads(ref.read_text()),index)})
    # Added selector plus tail shape: one narrowly affected memory check.
    out=ROOT/'evidence/small960_memcheck'
    receipt=locked('small960_memcheck',['/usr/local/cuda/bin/compute-sanitizer','--tool','memcheck','--error-exitcode','91',
        *command('STAR_MASK',out,data,qs,index,P7/'fixtures/seeds_4097.i32',qs,ROOT/'small960_u.f64')])
    log=(ROOT/'runs/small960_memcheck/stdout.log').read_text()+(ROOT/'runs/small960_memcheck/stderr.log').read_text()
    assert 'ERROR SUMMARY: 0 errors' in log
    rows.append({'label':out.name,'receipt':receipt,'quality':qualify(out,data,ref),'memcheck_errors':0})
    save(ROOT/'QUALIFICATION.json',rows)

def clean():
    assert (ROOT/'QUALIFICATION.json').exists()
    save(ROOT/'E0_SCHEDULE.json',{'frozen_before_first_clean_process':True,'schedule':SCHEDULE,'mode_parameters_fixed':True})
    rows=[]
    for rnd,modes in enumerate(SCHEDULE,1):
        for position,mode in enumerate(modes,1):
            label=f'r{rnd}_p{position}_{mode}';out=ROOT/'evidence'/label
            receipt=locked(label,command(mode,out))
            q=qualify(out);meta=json.loads(Path(str(out)+'.json').read_text())
            row={'round':rnd,'position':position,'mode':mode,'scope':'clean_host_ready','host_ms':meta['pass_ms'],
                 'deployable':not mode.startswith('STAR'),'oracle_tag':'USES_ORACLE_NOT_DEPLOYABLE' if mode.startswith('STAR') else '',
                 'quality_pass':q['complete_gate_pass'],'tie_recall':q['recall_tie_aware'],'deterministic_recall':q['recall_deterministic'],
                 'runtime_valid':receipt['runtime_valid'],'result_sha256':sha(str(out)+'.bin'),
                 'receipt_path':str(ROOT/'runs'/label/'receipt.json')}
            rows.append(row);save(ROOT/'CLEAN.json',rows)
            with (ROOT/'latency.csv').open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerows(rows)
            print(f'CLEAN PASS {label}: {meta["pass_ms"]:.6f} ms',flush=True)

def count():
    for mode in ('O_BOUND','O_MASK','STAR_SCAN','STAR_MASK'):
        label='count_'+mode;out=ROOT/'evidence'/label
        locked(label,command(mode,out),{'HEADROOM_COUNT':'1'});qualify(out)
        print('COUNT PASS '+mode,flush=True)

def bridge():
    rows=[]
    # ABBA is separate from the twenty-process main denominator.
    for i,original in enumerate((True,False,False,True),1):
        label=f'bridge_{i}_'+('original' if original else 'materialized');out=ROOT/'evidence'/label
        receipt=locked(label,command('O_MASK',out,original=original));q=qualify(out)
        meta=json.loads(Path(str(out)+'.json').read_text())
        rows.append({'position':i,'mode':'O_MASK','cutoff_materializer':not original,
                     'host_ms':meta['pass_ms'],'quality_pass':q['complete_gate_pass'],
                     'runtime_valid':receipt['runtime_valid'],'result_sha256':sha(str(out)+'.bin')})
        print('BRIDGE PASS '+label,flush=True)
    assert len({r['result_sha256'] for r in rows})==1
    save(ROOT/'BRIDGE.json',rows)

def profile():
    for mode in ('O_BOUND','O_MASK','STAR_SCAN','STAR_MASK','FAISS_FLAT'):
        label='profile_'+mode;out=ROOT/'evidence'/label
        prefix=ROOT/'evidence'/label
        cmd=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--cuda-graph-trace=node',
             '--sample=none','--cpuctxsw=none','--capture-range=nvtx','--nvtx-capture=formal.query_pass',
             '--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0','--capture-range-end=stop','--force-overwrite=false','-o',prefix,
             *command(mode,out)]
        locked(label,cmd);qualify(out)
        subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--output',str(prefix)+'.sqlite',str(prefix)+'.nsys-rep'],check=True)
        print('PROFILE PASS '+mode,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','small','clean','count','bridge','profile'))
    a=p.parse_args();globals()[a.phase]()
