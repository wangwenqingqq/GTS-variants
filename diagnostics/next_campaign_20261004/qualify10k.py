#!/usr/bin/env python3
"""Full small-output/tail, eager/Graph, stress and sanitizer qualification."""
import json
from pathlib import Path
import struct
import sys
import numpy as np
from campaign10k import ROOT,BASE,invoke,save,sha
from qualification import native_ivf,check_output

def cpu_reference(data,queries):
    rows=[]
    for q in queries:
        squared=np.zeros(len(data),dtype=np.float64)
        for j in range(data.shape[1]):
            delta=data[:,j].astype(np.float64)-float(data[q,j]);squared+=delta*delta
        ids=np.lexsort((np.arange(len(data)),squared))[:32]
        ties={str(k):{'strictly_closer_ids':np.flatnonzero(squared<squared[ids[k-1]]).tolist(),
                     'boundary_ids':np.flatnonzero(squared==squared[ids[k-1]]).tolist(),
                     'boundary_squared':float(squared[ids[k-1]])} for k in (8,32)}
        rows.append({'qid':int(q),'ids':ids.tolist(),'squared':squared[ids].tolist(),'ties':ties})
    return {'N':len(data),'D':data.shape[1],'Q':len(queries),'records':rows,'arithmetic':'CPU explicit subtract, multiply, add FP64; every database row'}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True);a=p.parse_args()
    fixture=ROOT/'fixtures';fixture.mkdir(exist_ok=True);(ROOT/'qualification').mkdir(exist_ok=True)
    qs=[0,1,63,*range(64,80),*range(128,138),4096,4000,3999,3998,*range(3000,3015)]
    assert len(qs)==48 and len(set(qs))==48
    qp=fixture/'small48.qid';qp.write_text('48\n'+''.join(f'{q}\n' for q in qs))
    wp=fixture/'small_warm256.qid';wp.write_text('256\n'+''.join(f'{q}\n' for q in range(256)))
    rows=[]
    for d in (96,960):
        source=native_ivf.load_data(a.p7/f'fixtures/small{d}.f32bin');ref=cpu_reference(source,qs)
        save(fixture/f'cpu48_{d}.json',ref)
        for m in ('O_FULL','O_BOUND','O_MASK'):
            for k in (8,32):
                for b in (1,32):
                    hashes=[]
                    for eager in (False,True):
                        label=f'f0_d{d}_{m}_k{k}_b{b}_{"eager" if eager else "graph"}'
                        out=ROOT/'qualification'/label
                        cmd=[ROOT/'opt_knn_bench',a.p7/f'fixtures/small{d}.f32bin',qp,a.p7/f'fixtures/small{d}.index',a.p7/'fixtures/seeds_4097.i32',m,k,b,out,wp,0]
                        receipt=invoke(a,label,cmd,env={'K10_EAGER':'1'} if eager else {})
                        quality=check_output(str(out)+'.bin',source,ref,k,exact=True)
                        digest=sha(str(out)+'.bin');hashes.append(digest)
                        rows.append({'label':label,'quality':quality,'output_sha256':digest,'receipt':receipt})
                    assert len(set(hashes))==1,'eager/Graph mismatch'
            for tool in ('stress','memcheck','synccheck'):
                label=f'f0_{tool}_d{d}_{m}_k32_b32';out=ROOT/'qualification'/label
                cmd=[ROOT/'opt_knn_bench',a.p7/f'fixtures/small{d}.f32bin',qp,a.p7/f'fixtures/small{d}.index',a.p7/'fixtures/seeds_4097.i32',m,32,32,out,wp,0]
                env={'K10_STRESS':'1'} if tool=='stress' else {}
                if tool!='stress':cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','91',*cmd]
                receipt=invoke(a,label,cmd,env=env)
                quality=check_output(str(out)+'.bin',source,ref,32,exact=True)
                if tool!='stress':assert 'ERROR SUMMARY: 0 errors' in (ROOT/'runs'/label/'stdout.log').read_text()+(ROOT/'runs'/label/'stderr.log').read_text()
                rows.append({'label':label,'quality':quality,'output_sha256':sha(str(out)+'.bin'),'receipt':receipt})
        source=native_ivf.load_data(BASE/f'synthetic_{d}.f32bin');ref=cpu_reference(source,qs)
        save(fixture/f'cpu48_original_{d}.json',ref)
        for k,b in [(k,b) for k in (8,32) for b in (1,32)]+[(32,32),(32,32)]:
            i=sum(r['label'].startswith(f'f0_original_d{d}') for r in rows)
            tool='memcheck' if i==4 else 'synccheck' if i==5 else 'plain'
            label=f'f0_original_d{d}_k{k}_b{b}_{tool}';out=ROOT/'qualification'/label
            cmd=[ROOT/'gts_bench_p7',BASE/f'synthetic_{d}.f32bin',qp,k,b,1,BASE/f'synthetic{d}.index',out,8,wp]
            if tool!='plain':cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','91',*cmd]
            receipt=invoke(a,label,cmd)
            quality=check_output(str(out)+'.bin',source,ref,k);assert quality['complete_gate_pass']
            if tool!='plain':assert 'ERROR SUMMARY: 0 errors' in (ROOT/'runs'/label/'stdout.log').read_text()+(ROOT/'runs'/label/'stderr.log').read_text()
            rows.append({'label':label,'quality':quality,'output_sha256':sha(str(out)+'.bin'),'receipt':receipt})
        save(ROOT/'F0_SMALL_PARTIAL.json',rows)
    assert len(rows)==78,len(rows)
    save(ROOT/'F0_SMALL.json',{'state':'passed','processes':len(rows),'query_count_each':48,'tail':16,'graph_eager_pairs':24,'stress_processes':6,'cycles_each':100,'sanitizer_processes':16,'rows':rows})
    print('F0 SMALL COMPLETE: 78 processes; full CPU membership/fields, 16-tail, 600 stress cycles, 16 sanitizers',flush=True)

if __name__=='__main__':main()
