#!/usr/bin/env python3
"""Approved pre-timing calibration revision; do not overwrite original preparations."""
import argparse,os,time
from pathlib import Path
import numpy as np
from prepare import HERE,read,sha,save,scores_library,sources

def main(a):
    w=a.work;c=read(HERE/'CONTRACT.json');p=read(w/'PREPARED.json');reg=read(w/'REGISTERED.json');assert p['passed'];assert c['calibration_revision']['human_authorized']
    assert c['calibration_revision']['original_contract_sha256']==reg['contract_sha256']==sha(a.original_contract)
    qids=c['calibration_qids'];assert not set(qids)&set(reg['qids']) and len(set(qids))==8
    assert qids==np.random.default_rng(c['calibration_seed']).choice(1000000,size=8,replace=False).tolist()
    out=w/'calibration_r1';out.mkdir(exist_ok=False);save(out/'REGISTERED.json',dict(before_execution=True,source_hashes=sources(),prepared_sha256=sha(w/'PREPARED.json'),contract_sha256=sha(HERE/'CONTRACT.json'),qids=qids,seed=c['calibration_seed'],no_GPU_timing_executed=True,registered_unix=time.time()))
    score=scores_library(w/'build/cpu_oracle.so');x=np.memmap(reg['data'],dtype='<f4',offset=12,shape=(1000000,960));target=p['calibration']['960']['mid']['target_hits'];calibration={};files={}
    for d in (960,128,256,512):
        xx=np.ascontiguousarray(x[:,:d]);v=np.stack([score(xx,xx[q]) for q in qids]);v.tofile(out/f'D{d}.f64');files[f'D{d}.f64']=sha(out/f'D{d}.f64');flat=v.reshape(-1)
        targets={'low':10,'high':target*10} if d==960 else {'mid':target};rows={}
        for name,t in targets.items():
            k=int(np.floor(8*t))-1;z=np.partition(flat,k)[k];radius=np.float32(np.sqrt(z));rows[name]=dict(radius=float(radius),radius_bits=hex(int(radius.view(np.uint32))),target_hits=t,calibration_mean_hits=float(np.count_nonzero(v<=float(radius)**2)/8))
        if d==960:rows['mid']=p['calibration']['960']['mid']
        calibration[str(d)]=rows;print('CALIBRATED',d,rows,flush=True)
    monotonic=calibration['960']['low']['radius']<calibration['960']['mid']['radius']<calibration['960']['high']['radius']
    save(a.output,dict(passed=True,prepared_sha256=sha(w/'PREPARED.json'),contract_sha256=sha(HERE/'CONTRACT.json'),revision_registration_sha256=sha(out/'REGISTERED.json'),calibration=calibration,calibration_qids=qids,calibration_files=files,low_mid_high_radius_order=monotonic,scope='Approved seeded held-out calibration, never measured-query radius retuning; attained measured counts must be disclosed'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original-contract',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
