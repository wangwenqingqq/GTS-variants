#!/usr/bin/env python3
"""One gated sector oracle and one moment-sector probe; counts, never GPU timing."""
import argparse
import datetime
import fcntl
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
import native_check as native

ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent/'proof_per_byte_512_gate5_20261013'
spec=importlib.util.spec_from_file_location('gate5_common',PREVIOUS/'run.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
require,read,save,sha,quality,distribution=(getattr(common,n) for n in ('require','read','save','sha','quality','distribution'))


def gate_a(o,b):
    if 2*o<=b:return 'STRONG_SECTOR_HEADROOM'
    return 'WEAK_SECTOR_HEADROOM' if 5*o<=4*b else 'NO_SECTOR_HEADROOM'


def exact_quantile(values,p):
    v=sorted(values);rank=(len(v)-1)*p;lo=int(rank);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(rank-lo)


def gate_b(total,baseline,p90):
    if 5*total<=4*baseline:
        return 'GO_SECTOR_PROOF_PER_BYTE' if p90<=Fraction(1,2) else 'UNCLASSIFIED'
    return 'CONDITIONAL_SECTOR_PROOF' if total<=baseline else 'NO_GO_SECTOR_PROOF'


def selection(q,stats):
    score=(q.astype(np.float64)-stats[0].astype(np.float64))**2+stats[1].astype(np.float64)
    groups=np.zeros(120,dtype='<f8')
    for h in range(8):groups+=score[h::8]
    require(np.isfinite(groups).all(),'invalid sector moment scores')
    ranked=np.argsort(-groups,kind='stable')[:16].astype('<u2');ordered=np.sort(ranked)
    return ordered,{'ranked_sectors':ranked.tolist(),'scan_sectors':ordered.tolist(),
                    'sector_scores_sha256':hashlib.sha256(groups.tobytes()).hexdigest(),
                    '16th_score':float(groups[ranked[-1]]),'cutoff_score_ties':int((groups==groups[ranked[-1]]).sum())}


def run(args):
    c=read(ROOT/'CONTRACT.json');w=c['workload'];n=w['N'];d=w['D'];cutoff=float.fromhex(w['cutoff_hex'])
    require(sys.flags.optimize==0,'non-optimized Python required')
    for key,want in {'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4','OMP_DYNAMIC':'FALSE','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items():
        require(os.environ.get(key)==want,'environment differs: '+key)
    require(os.nice(0)>=10,'nice>=10 required')
    work=args.work.resolve();work.mkdir();(work/'raw').mkdir();(work/'queries').mkdir();args.created=True
    frozen={name:sha(ROOT/name) for name in ('CONTRACT.json','probe.cpp','run.py','native_check.py')}
    identity=read(args.repo/'artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json')
    refs=identity['reference_hashes'];require(identity['query_ids']==w['query_ids'],'query IDs differ')
    if args.stage=='B':
        require(args.stage_a is not None,'A receipt required')
        a=read(args.stage_a/'RESULTS.json');require(a['complete'] and a['gate']=='STRONG_SECTOR_HEADROOM' and a['numerical_boundary_pairs']==0,'S1 not admitted')
        require(read(args.stage_a/'REGISTRATION.json')['source_sha256']==frozen,'A registered sources differ')
    save(work/'REGISTRATION.json',{'stage':args.stage,'base_commit':c['base_commit'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'contract_sha256':frozen['CONTRACT.json'],'source_sha256':frozen,'reference_hashes':refs,'data_sha256':w['data_sha256'],
         'query_ids':w['query_ids'],'CPU_workers':4,'nice':os.nice(0),'Python_optimization_level':0,'population_processes_this_stage':1,'GPU_starts':0,'NCU_starts':0})
    start=time.monotonic()
    for name,digest in c['parent_files'].items():require(sha(args.repo/name)==digest,'parent differs: '+name)
    require(sha(args.data)==w['data_sha256'] and args.data.stat().st_size==12+n*d*4,'database differs')
    import struct
    with args.data.open('rb') as f:require(struct.unpack('<iii',f.read(12))==(d,n,2),'database header differs')
    for name,digest in refs.items():
        p=args.cache/name;require(p.stat().st_size==8*n and sha(p)==digest,'frozen full-score file differs: '+name)
    save(work/'INPUT_CHECK.json',{'all_hashes_match':True,'parent_files':c['parent_files'],'data_sha256':w['data_sha256'],'reference_hashes':refs})
    if args.stage=='A':
        binary=work/'probe.so';p=subprocess.run(['g++',*c['execution']['compiler_flags'],str(ROOT/'probe.cpp'),'-o',str(binary)],capture_output=True,text=True)
        save(work/'BUILD_LOG.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});require(p.returncode==0,'native build failed')
        save(work/'BUILD.json',{'returncode':0,'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
             'flags':c['execution']['compiler_flags'],'binary_sha256':sha(binary),'binary_bytes':binary.stat().st_size})
    else:
        binary=args.stage_a/'probe.so';require(sha(binary)==read(args.stage_a/'BUILD.json')['binary_sha256'],'A binary differs')
        save(work/'BUILD.json',{'reused_Gate6A_binary':True,'binary_sha256':sha(binary)})
    p=subprocess.run([sys.executable,str(ROOT/'native_check.py'),'--library',str(binary)],capture_output=True,text=True)
    save(work/'FIXTURES.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});require(p.returncode==0,'native fixtures failed')
    lib=native.load(binary);x=np.memmap(args.data,mode='r',dtype='<f4',offset=12,shape=(n,d))
    save(work/'GEOMETRY.json',{'row_bytes':d*4,'row_stride_mod32':int(x.strides[0]%32),'CPU_payload_pointer_mod32':int(x.ctypes.data%32),
         'device_aligned_payload_base_required':32,'device_allocation_tested':False,'sector_payload_only_not_measured_GPU_traffic':True})
    queries=np.array(x[w['query_ids']],dtype='<f4',order='C',copy=True)
    if args.stage=='B':
        stats_record=read(PREVIOUS/'routing/DATASET_STATS.json')
        stats=np.asarray([stats_record['mean'],stats_record['variance']],dtype='<f4')
        require(stats.nbytes==7680 and hashlib.sha256(stats.tobytes()).hexdigest()==c['routing']['moment_binary_sha256'],'frozen moments differ')
        require(np.isfinite(stats).all() and (stats[1]>=0).all(),'invalid moments')
        selections=[selection(q,stats) for q in queries]
        save(work/'SECTOR_SELECTIONS.json',[{'query_id':qid,**s[1]} for qid,s in zip(w['query_ids'],selections)])
        save(work/'DATASET_STATS_IDENTITY.json',{'reestimated':False,'metadata_bytes':7680,'binary_sha256':c['routing']['moment_binary_sha256'],
             'source_json_sha256':sha(PREVIOUS/'routing/DATASET_STATS.json'),'query_sector_ID_bytes':32})
    qualification=[]
    for idx,(qid,q) in enumerate(zip(w['query_ids'],queries)):
        ref=np.memmap(args.cache/f'{qid}.f64',mode='r',dtype='<f8',shape=(n,))
        if args.stage=='A':
            outs=native.oracle(lib,x[:4096],q);wants=native.golden(x[:4096],q,16)
            require(all(native.previous.same_bits(g,w) for g,w in zip(outs,wants)),'independent sector oracle bits differ')
            require(native.previous.same_bits(outs[2],ref[:4096]),'qualified full-score bits differ')
            row={'B0':quality(outs[0],ref[:4096],cutoff),'O2':quality(outs[1],ref[:4096],cutoff)}
        else:
            ids=selections[idx][0];part=native.subset(lib,x[:4096],q,ids);want=np.zeros(4096,dtype='<f8')
            for s in ids:
                for h in range(8):
                    j=int(s)*8+h;delta=x[:4096,j].astype(np.float64)-float(q[j]);want+=delta*delta
            require(native.previous.same_bits(part,want),'independent S1 ordered bits differ')
            row={'S1':quality(part,ref[:4096],cutoff)}
        qualification.append({'query_id':qid,**row});ref._mmap.close()
    save(work/'QUALIFICATION.json',{'passed':True,'pairs':131072,'queries':qualification})
    save(work/'START.json',{'qualified_before_population':True,'source_sha256':frozen,'query_bytes_sha256':hashlib.sha256(queries.tobytes()).hexdigest()})
    rows=[];manifest={};boundary=0;u=2.**-53;guard=2*960*u/(1-960*u)
    print('Qualified; starting Gate6'+args.stage+' 32 x 1M',flush=True)
    for idx,(qid,q) in enumerate(zip(w['query_ids'],queries)):
        tick=time.monotonic()
        if args.stage=='A':b0,o2,full=native.oracle(lib,x,q)
        else:part=native.subset(lib,x,q,selections[idx][0])
        ref=np.memmap(args.cache/f'{qid}.f64',mode='r',dtype='<f8',shape=(n,))
        if args.stage=='A':
            require(native.previous.same_bits(full,ref),'full-population full-score bits differ')
            row={'B0':quality(b0,ref,cutoff),'O2':quality(o2,ref,cutoff)}
            expect=c['baseline']['expected_queries'][idx];require(row['B0']['survivors']==expect['survivors'] and row['B0']['hits']==expect['hits'],'B0 parent parity failed')
            near=int((np.abs(o2-cutoff)<=guard*np.maximum(o2,cutoff)).sum());boundary+=near
            row.update(oracle_numerical_boundary_pairs=near,full_distance_bit_mismatches=0)
            arrays=[('B0',b0),('O2',o2)]
        else:row={'S1':quality(part,ref,cutoff)};arrays=[('S1',part)]
        for name,v in arrays:common.keep_array(work,qid,name,v,manifest)
        ref._mmap.close();row.update(query_id=qid,query_index=idx,operational_seconds=time.monotonic()-tick)
        rows.append(row);save(work/'queries'/f'q{idx:02}.json',row)
        print('PASS',idx+1,'/',32,qid,{k:v['survivors'] for k,v in row.items() if k in ('B0','O2','S1')},flush=True)
    x._mmap.close()
    require(frozen=={n:sha(ROOT/n) for n in frozen} and sha(args.data)==w['data_sha256'],'input/source changed')
    for name,digest in c['parent_files'].items():require(sha(args.repo/name)==digest,'parent changed: '+name)
    for name,digest in refs.items():require(sha(args.cache/name)==digest,'reference changed: '+name)
    save(work/'QUERY_RESULTS.json',rows);save(work/'RAW_MANIFEST.json',{'files':manifest})
    btotal=c['baseline']['expected_total_survivors']
    if args.stage=='A':
        total=sum(r['O2']['survivors'] for r in rows);gate='UNCLASSIFIED' if boundary else gate_a(total,btotal)
        totals={'B0_total_survivors':sum(r['B0']['survivors'] for r in rows),'O2_total_survivors':total,'ratio':total/btotal,'numerical_boundary_pairs':boundary,'gate':gate}
    else:
        total=sum(r['S1']['survivors'] for r in rows);ratios=[Fraction(r['S1']['survivors'],b['survivors']) for r,b in zip(rows,c['baseline']['expected_queries'])]
        p90=exact_quantile(ratios,Fraction(9,10));bytes_total=32*512000000+3328*total
        gate=gate_b(bytes_total,c['byte_model']['strong_baseline_total_bytes_all32'],p90)
        totals={'S1_total_survivors':total,'ratio_to_B0':total/btotal,'per_query_ratio_distribution':distribution(list(map(float,ratios))),
                'p90_exact_numerator':p90.numerator,'p90_exact_denominator':p90.denominator,'fallback_total_bytes':bytes_total,'fallback_mean_bytes':bytes_total/32,'gate':gate}
    save(work/'RESULTS.json',{'complete':True,'stage':args.stage,'pairs':32*n,'CPU_workers':4,'GPU_starts':0,'NCU_starts':0,
         'operational_seconds':time.monotonic()-start,**totals})
    save(work/'CLOSURE.json',{'all_input_source_parent_reference_hashes_unchanged':True,'query_count':32,'population_processes':1,
         'CPU_workers':4,'Python':sys.version.split()[0],'NumPy':np.__version__,'Python_optimization_level':0,'GPU_starts':0,'NCU_starts':0,
         'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps(totals,sort_keys=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['A','B'],required=True)
    for name in ('data','cache','repo','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage-a',type=Path);args=p.parse_args()
    try:
        with (args.work.parent/'campaign.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args)
    except Exception:
        if getattr(args,'created',False):save(args.work/'FAILURE.json',{'error':traceback.format_exc(),'GPU_starts':0,'stop':'No automatic retry'})
        raise
