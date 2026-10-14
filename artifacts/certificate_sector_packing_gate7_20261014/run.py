#!/usr/bin/env python3
"""Gated CPU training, one packed representation, one exact population probe."""
import argparse
import datetime
import fcntl
from fractions import Fraction
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import traceback

import numpy as np
import native_check as native
import pack

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent/'proof_per_byte_512_gate5_20261013'
sys.path.insert(0,str(PARENT))
spec=importlib.util.spec_from_file_location('gate5_common',PARENT/'run.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
require,read,save,sha,quality,distribution=(getattr(common,n) for n in ('require','read','save','sha','quality','distribution'))


def exact_quantile(v,p):
    v=sorted(v); rank=(len(v)-1)*p; lo=int(rank);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(rank-lo)


def gate(total,s1,p90):
    if 10*total<=7*s1:
        return 'GO_PACKING_INFORMATION' if p90<=Fraction(4,5) else 'UNCLASSIFIED'
    return 'CONDITIONAL_PACKING' if 20*total<=17*s1 else 'NO_GO_PACKING'


def source_identities():
    return {p:sha(ROOT/p) for p in ('CONTRACT.json','run.py','pack.py','native_check.py','probe.cpp','prior_art/PRIOR_ART_PACKING.md','prior_art/SOURCES.json')}


def stats(c):
    record=read(PARENT/'routing/DATASET_STATS.json')
    s=np.asarray([record['mean'],record['variance']],dtype='<f4')
    require(hashlib.sha256(s.tobytes()).hexdigest()==c['training']['moment_binary_sha256'],'frozen moment bits differ')
    return s


def train(c,args,x,work):
    w=c['workload']; ids,draws=pack.train_ids(w['N'],w['query_ids'])
    save(work/'TRAIN_QUERY_IDS.json',{'query_ids':ids,'draws':draws,'seed':2026101401,'PRNG':c['training']['PRNG'],'eval_overlap':0,'duplicates':0})
    # IDs are persisted before any scores; no evaluation vectors are accessed.
    s=stats(c);top=[];recover=[];concentration=[]
    for qid in ids:
        scores=pack.coordinate_scores(np.array(x[qid],copy=True),s)
        top.append(np.argsort(-scores,kind='stable')[:128].astype('<u2'))
    top=np.asarray(top,dtype='<u2');top.tofile(work/'TRAIN_TOP128.u16')
    wm=pack.co_select(top);wm.tofile(work/'COSELECTION_MATRIX.u16')
    pi=pack.greedy(wm);require(sorted(pi.tolist())==list(range(960)),'packing is not a bijection')
    save(work/'PERMUTATION.json',{'pi':pi.tolist(),'direction':'packed physical position -> original dimID','algorithm':'P1_COSELECT_PACK8','training_ids_sha256':sha(work/'TRAIN_QUERY_IDS.json'),'training_top128_sha256':sha(work/'TRAIN_TOP128.u16'),'W_sha256':sha(work/'COSELECTION_MATRIX.u16')})
    save(work/'SECTORS.json',{'groups':pi.reshape(120,8).tolist(),'group_count':120,'dimensions_per_group':8})
    save(work/'COSELECTION_MATRIX_META.json',{'shape':[960,960],'dtype':'little-endian uint16','includes_diagonal':True,'degree':'fixed global row sum including diagonal, uint64','bytes':wm.nbytes,'sha256':sha(work/'COSELECTION_MATRIX.u16'),'total_entries_sum':int(wm.sum(dtype=np.uint64)),'diagonal_sum':int(np.trace(wm,dtype=np.uint64)),'symmetric':bool(np.array_equal(wm,wm.T))})
    # No evaluation data/output touched before this immutable packing receipt.
    save(work/'PERMUTATION_FROZEN.json',{'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'permutation_sha256':sha(work/'PERMUTATION.json'),'sectors_sha256':sha(work/'SECTORS.json'),'evaluation_queries_read':0,'evaluation_outcomes_read':0,'second_algorithm':False})
    for ids1,qid in zip(top,ids):
        scores=pack.coordinate_scores(np.array(x[qid],copy=True),s);selected=pack.sector_selection(scores,pi)[0]
        dims=pi.reshape(120,8)[selected].reshape(-1)
        recover.append(len(set(ids1.tolist())&set(dims.tolist()))/128)
        concentration.append(pack.demand_quality(ids1,pi))
    save(work/'PACKING_QUALITY.json',{'training_count':1024,'training_sector_concentration':distribution(concentration),'training_C1_recovery':distribution(recover),'training_mean_high_value_dims_per_selected_sector':8*float(np.mean(recover)),'concentration_definition':'sum_group choose(top128 dims in group,2)/choose(128,2); maximum 448/8128 for groups8','no_query_object_distance_outcomes':True})
    save(work/'RESULTS.json',{'complete':True,'stage':'training','train_queries':1024,'population_pairs':0,'GPU_starts':0,'NCU_starts':0,'packing_frozen':True})


def evaluate(c,args,x,work):
    w=c['workload'];n=w['N'];d=w['D'];cutoff=float.fromhex(w['cutoff_hex']);t=args.training
    require(t is not None and read(t/'RESULTS.json')['complete'],'training receipt missing')
    require(read(t/'REGISTRATION.json')['source_sha256']==source_identities(),'training registered sources changed')
    frozen=read(t/'PERMUTATION_FROZEN.json');pi=np.asarray(read(t/'PERMUTATION.json')['pi'],dtype='<u2')
    require(sha(t/'PERMUTATION.json')==frozen['permutation_sha256'] and sha(t/'SECTORS.json')==frozen['sectors_sha256'],'frozen packing changed')
    tids=read(t/'TRAIN_QUERY_IDS.json')['query_ids'];expected,draws=pack.train_ids(n,w['query_ids'])
    require(tids==expected and len(set(tids))==1024 and not(set(tids)&set(w['query_ids'])),'training IDs differ/overlap')
    top=np.fromfile(t/'TRAIN_TOP128.u16',dtype='<u2').reshape(1024,128);wm=pack.co_select(top)
    require(hashlib.sha256(wm.tobytes()).hexdigest()==read(t/'COSELECTION_MATRIX_META.json')['sha256'] and np.array_equal(pi,pack.greedy(wm)),'co-selection/greedy reproduction differs')
    identity=read(args.repo/'artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json');refs=identity['reference_hashes']
    require(identity['query_ids']==w['query_ids'],'oracle query IDs differ')
    for file,digest in refs.items():require(sha(args.cache/file)==digest and (args.cache/file).stat().st_size==8*n,'full-score reference differs')
    save(work/'REFERENCE_IDENTITIES.json',refs)
    p=subprocess.run(['g++',*c['execution']['compiler_flags'],str(ROOT/'probe.cpp'),'-o',str(work/'probe.so')],capture_output=True,text=True)
    save(work/'BUILD.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'flags':c['execution']['compiler_flags']})
    require(p.returncode==0,'native build failed');save(work/'BINARY_IDENTITY.json',{'bytes':(work/'probe.so').stat().st_size,'sha256':sha(work/'probe.so')})
    p=subprocess.run([sys.executable,str(ROOT/'native_check.py'),'--library',str(work/'probe.so')],capture_output=True,text=True)
    save(work/'FIXTURES.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});require(p.returncode==0,'packed fixtures failed')
    packed=work/'packed.f32';packed.touch(exist_ok=False)
    xp=np.memmap(packed,mode='w+',dtype='<f4',shape=(n,d))
    for start in range(0,n,8192):
        xp[start:start+8192]=np.ascontiguousarray(x[start:start+8192,pi])
    xp.flush();inverse=np.argsort(pi)
    for start in range(0,n,8192):
        restored=np.ascontiguousarray(xp[start:start+8192,inverse])
        require(np.array_equal(restored.view('<u4'),x[start:start+8192].view('<u4')),'complete transform bits differ')
    save(work/'TRANSFORM.json',{'validated_coordinate_bits':n*d,'mismatches':0,'rows':n,'packed_bytes':n*d*4,'packed_sha256':sha(packed),'source_sha256':sha(args.data),'raw_source_read_only':True,'candidate_single_database':True,'inverse_permutation_restores_all_original_bits':True,'packed_header_bytes':0,'CPU_payload_pointer_mod32':int(xp.ctypes.data%32),'row_stride_mod32':int(xp.strides[0]%32)})
    xp._mmap.close();x._mmap.close();packed.chmod(0o444)
    # Original database is now closed. All candidate/full audit calls use xp only.
    xp=np.memmap(packed,mode='r',dtype='<f4',shape=(n,d));s=stats(c);lib=native.load(work/'probe.so')
    queries=np.ascontiguousarray(xp[w['query_ids']]);selections=[];evaluation=[]
    for qid,qp in zip(w['query_ids'],queries):
        q=qp[inverse];scores=pack.coordinate_scores(q,s);chosen,ranked,groups=pack.sector_selection(scores,pi)
        top1=np.argsort(-scores,kind='stable')[:128].astype('<u2')
        s1=pack.sector_selection(scores,np.arange(d,dtype='<u2'))[0]
        p_dims=pi.reshape(120,8)[chosen].reshape(-1);s_dims=np.arange(d).reshape(120,8)[s1].reshape(-1)
        evaluation.append({'query_id':qid,'C1_top128':top1.tolist(),'ranked_sectors':ranked.tolist(),'scan_sectors':chosen.tolist(),'selected_original_dims':sorted(p_dims.tolist()),'sector_scores_sha256':hashlib.sha256(groups.tobytes()).hexdigest(),'C1_recovery':len(set(top1.tolist())&set(p_dims.tolist()))/128,'P1_high_value_dims_per_selected_sector':[len(set(top1.tolist())&set(g.tolist())) for g in pi.reshape(120,8)[chosen]],'S1_high_value_dims_per_selected_sector':[len(set(top1.tolist())&set(g.tolist())) for g in np.arange(d).reshape(120,8)[s1]],'packed_sector_concentration':pack.demand_quality(top1,pi),'original_sector_concentration':pack.demand_quality(top1,np.arange(d,dtype='<u2'))})
        selections.append(chosen)
    save(work/'EVALUATION_SELECTIONS.json',evaluation)
    qualifications=[]
    for qid,qp,chosen in zip(w['query_ids'],queries,selections):
        ref=np.memmap(args.cache/f'{qid}.f64',mode='r',dtype='<f8',shape=(n,))
        full=native.call(lib,xp[:4096],qp,pi);part=native.call(lib,xp[:4096],qp,pi,chosen)
        require(native.same_bits(full,ref[:4096]) and native.same_bits(full,native.golden(xp[:4096],qp,pi)) and native.same_bits(part,native.golden(xp[:4096],qp,pi,chosen)),'independent qualification bits differ')
        qualifications.append({'query_id':qid,**quality(part,ref[:4096],cutoff)});ref._mmap.close()
    save(work/'QUALIFICATION.json',{'passed':True,'pairs':32*4096,'queries':qualifications,'original_database_closed_before_candidate':True})
    save(work/'START.json',{'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'qualified_before_population':True,'permutation_sha256':frozen['permutation_sha256'],'source_sha256':source_identities()})
    rows=[];manifest={};print('Qualified; starting one Gate7 32 x 1M population',flush=True)
    for i,(qid,qp,chosen) in enumerate(zip(w['query_ids'],queries,selections)):
        tick=time.monotonic();part=native.call(lib,xp,qp,pi,chosen)
        full=native.call(lib,xp,qp,pi)
        ref=np.memmap(args.cache/f'{qid}.f64',mode='r',dtype='<f8',shape=(n,));require(native.same_bits(full,ref),'population full-score bits differ')
        row={'query_id':qid,'query_index':i,**quality(part,ref,cutoff),'full_score_bit_comparisons':n,'full_score_bit_mismatches':0}
        common.keep_array(work,qid,'P1',part,manifest);ref._mmap.close();row['operational_seconds']=time.monotonic()-tick;rows.append(row)
        save(work/'queries'/f'q{i:02}.json',row);print('PASS',i+1,'/32',qid,row['survivors'],flush=True)
    xp._mmap.close();require(sha(packed)==read(work/'TRANSFORM.json')['packed_sha256'],'packed data changed')
    s1=read(args.repo/'artifacts/sector_proof_per_byte_gate6_20261014/routing/S1_SECTOR_MOMENT.json');require([r['query_id'] for r in s1['queries']]==w['query_ids'] and s1['total_survivors']==3776388,'primary baseline differs')
    total=sum(r['survivors'] for r in rows);ratios=[Fraction(a['survivors'],b['survivors']) for a,b in zip(rows,s1['queries'])];p90=exact_quantile(ratios,Fraction(9,10));decision=gate(total,3776388,p90);ft=32*512000000+3328*total
    save(work/'QUERY_RESULTS.json',rows);save(work/'RAW_MANIFEST.json',{'files':manifest})
    save(work/'RESULTS.json',{'complete':True,'stage':'evaluation','pairs':32*n,'total_survivors':total,'mean_survivors':total/32,'ratio_to_S1':total/3776388,'p90_P1_over_S1':float(p90),'p90_exact_numerator':p90.numerator,'p90_exact_denominator':p90.denominator,'gate':decision,'conditional_source_bytes_total':ft,'conditional_source_bytes_mean':ft/32,'strong_byte_gate_pass':5*ft<=4*32474520832,'GPU_starts':0,'NCU_starts':0,'population_processes':1})
    print(read(work/'RESULTS.json'),flush=True)


def run(args):
    c=read(ROOT/'CONTRACT.json');w=c['workload'];require(c['prior_art']['verdict']=='DISTINCT_ENOUGH_TO_TEST','prior art not admitted')
    require(sys.flags.optimize==0 and os.nice(0)>=10,'non-optimized Python / nice>=10 required')
    for key,want in {'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4','OMP_DYNAMIC':'FALSE','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}.items():require(os.environ.get(key)==want,'environment differs: '+key)
    work=args.work.resolve();work.mkdir();args.created=True;(work/'raw').mkdir();(work/'queries').mkdir();frozen=source_identities()
    save(work/'REGISTRATION.json',{'stage':args.stage,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':c['base_commit'],'source_sha256':frozen,'CPU_workers':4,'nice':os.nice(0),'Python':sys.version.split()[0],'NumPy':np.__version__,'Python_optimization_level':0,'GPU_starts':0,'NCU_starts':0,'population_processes':int(args.stage=='evaluation'),'training_and_evaluation_disjoint':True})
    for p,digest in c['parent_files'].items():require(sha(args.repo/p)==digest,'parent file differs: '+p)
    require(sha(args.data)==w['data_sha256'] and args.data.stat().st_size==12+w['N']*w['D']*4,'original data identity differs')
    with args.data.open('rb') as f:require(struct.unpack('<iii',f.read(12))==(w['D'],w['N'],2),'original data header differs')
    x=np.memmap(args.data,mode='r',dtype='<f4',offset=12,shape=(w['N'],w['D']))
    if args.stage=='training':train(c,args,x,work);x._mmap.close()
    else:evaluate(c,args,x,work)
    require(source_identities()==frozen and sha(args.data)==w['data_sha256'],'source/input changed')
    for p,digest in c['parent_files'].items():require(sha(args.repo/p)==digest,'parent changed')
    save(work/'CLOSURE.json',{'complete':True,'unchanged_sources_data_parents':True,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'GPU_starts':0,'NCU_starts':0,'no_automatic_retry':True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['training','evaluation'],required=True)
    for name in ('data','repo','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--training',type=Path);p.add_argument('--cache',type=Path);args=p.parse_args()
    try:
        with (args.work.parent/'campaign.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args)
    except Exception:
        if getattr(args,'created',False):save(args.work/'FAILURE.json',{'error':traceback.format_exc(),'GPU_starts':0,'stop':'No automatic population retry'})
        raise
