#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'native_knn_faiss_ivf_20261003'
if not BASE.is_dir():BASE=ROOT.parent/'gts_native_knn_faiss_ivf_20261003'
sys.path.insert(0,str(BASE))
import native_ivf
from verify_outputs import quality

def check_output(path,data,reference,k,exact=False):
    n,d,rk,ids,dist=native_ivf.read_gts(path)
    assert (n,d)==data.shape and rk==k
    q=quality(ids,dist,reference,data,k,allow_missing=True)
    q['minimum_query_recall']=min(q['per_query_recall'])
    q['finite_pass']=bool(np.isfinite(dist).all())
    q['output_contract_pass']=q['missing_neighbor_slots']==0 and q['finite_pass'] and q['distance_tolerance_pass']
    q['complete_gate_pass']=q['output_contract_pass'] and q['minimum_query_recall']==1
    q['deterministic_gate_pass']=q['complete_gate_pass'] and q['recall_deterministic']==1
    if exact:assert q['deterministic_gate_pass'],q
    return q

def coverage(path,data,reference,index):
    with Path(index).open('rb') as f:f.read(16);order=np.fromfile(f,dtype='<i4',count=len(data))
    with Path(path).open('rb') as f:
        n,d,q,k=np.fromfile(f,dtype='<i4',count=4);assert (n,d,q)==(len(data),data.shape[1],reference['Q'])
        cutoff=np.fromfile(f,dtype='<f8',count=q)
        masks=np.fromfile(f,dtype='u1',count=q*n).reshape(q,n)
        scores=np.fromfile(f,dtype='<f8',count=q*n).reshape(q,n)
        assert not f.read(1)
    eligible_count=0;masked_count=0
    for row,r in enumerate(reference['records']):
        truth=np.zeros(n,dtype=np.float64)
        for j in range(d):
            delta=data[order,j].astype(np.float64)-float(data[r['qid'],j]);truth+=delta*delta
        eligible=truth<=cutoff[row]
        assert np.all(masks[row,eligible]==1),'tree excluded a seed-cutoff eligible object'
        assert np.array_equal(scores[row,eligible],truth[eligible]),'early exit excluded/changed an eligible pair'
        eligible_count+=int(eligible.sum());masked_count+=int((masks[row]==0).sum())
    return {'all_seed_cutoff_eligible_pairs_checked':eligible_count,'eligible_pairs_wrongly_excluded':0,
            'tree_excluded_pairs':masked_count,'total_pairs':int(n*q),'separate_post_timer_replay':True}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sanitizer',action='store_true');a=parser.parse_args()
    outputs=ROOT/'small_runs';outputs.mkdir(exist_ok=True);rows=[]
    for d in (96,960):
        data=native_ivf.load_data(ROOT/f'fixtures/small{d}.f32bin')
        reference=json.loads((ROOT/f'fixtures/cpu_small{d}.json').read_text())
        for mode in ('O_FULL','O_BOUND','O_MASK'):
            shapes=[(32,32)] if a.sanitizer else [(k,b) for k in (8,32) for b in (1,32)]
            for k,b in shapes:
                tools=('memcheck','synccheck') if a.sanitizer else ('plain',)
                for tool in tools:
                    label=f'{tool}_d{d}_{mode}_k{k}_b{b}';out=outputs/label
                    cmd=[str(ROOT/'opt_knn_bench'),str(ROOT/f'fixtures/small{d}.f32bin'),str(ROOT/'fixtures/small33.qid'),
                         str(ROOT/f'fixtures/small{d}.index'),str(ROOT/'fixtures/seeds_4097.i32'),mode,str(k),str(b),str(out),str(ROOT/'fixtures/small33.qid'),'0']
                    if tool!='plain':cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','91',*cmd]
                    with (outputs/(label+'.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,env={**os.environ,'P7_SMALL_AUDIT':'1'} if not a.sanitizer else None)
                    q=check_output(str(out)+'.bin',data,reference,k,True)
                    if not a.sanitizer:q['coverage']=coverage(str(out)+'.coverage.bin',data,reference,ROOT/f'fixtures/small{d}.index')
                    if tool!='plain':assert 'ERROR SUMMARY: 0 errors' in (outputs/(label+'.log')).read_text()
                    rows.append({'label':label,'quality':q,'metadata':json.loads(Path(str(out)+'.json').read_text())})
                    print('PASS '+label,flush=True)
        if not a.sanitizer:
            for k in (8,32):
                out=outputs/f'all_d{d}_k{k}'
                subprocess.run([str(ROOT/'opt_knn_bench'),str(ROOT/f'fixtures/small{d}.f32bin'),str(ROOT/'fixtures/small33.qid'),
                    str(ROOT/f'fixtures/small{d}.index'),str(ROOT/'fixtures/seeds_4097.i32'),'O_MASK',str(k),'32',str(out),str(ROOT/'fixtures/small33.qid'),'1'],check=True,env={**os.environ,'P7_SMALL_AUDIT':'1'})
                q=check_output(str(out)+'.bin',data,reference,k,True)
                q['coverage']=coverage(str(out)+'.coverage.bin',data,reference,ROOT/f'fixtures/small{d}.index')
                rows.append({'label':out.name,'quality':q,'metadata':json.loads(Path(str(out)+'.json').read_text())})
    (ROOT/('SANITIZER.json' if a.sanitizer else 'QUALIFICATION.json')).write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
