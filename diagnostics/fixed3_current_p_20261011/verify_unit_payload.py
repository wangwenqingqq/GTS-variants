#!/usr/bin/env python3
"""CPU-only post-closure oracle for every real-kernel unit output byte."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def expected():
    h=hashlib.sha256();cases=0
    for d in (128,960):
        for size in range(1,21):
            for nl in range(1,9):
                for churn in range(3):
                    n=nl*size;rng=np.random.RandomState(2026101101+d+size*100+nl)
                    # Legacy RandomState's single-seed MT19937 is std::mt19937's stream.
                    integers=(rng.randint(0,2**32,size=(n,d),dtype=np.uint32)%257).astype(np.int64)-128
                    integers[0]=0
                    if n>1:integers[1]=integers[0]
                    if n>2:integers[2]=0;integers[2,0]=256
                    # All coordinates are dyadic: each squared term and total are exact FP64.
                    squares=(integers*integers).sum(axis=1).astype(np.float64)/65536.
                    ids=np.arange(n-1,-1,-1);active=np.ones(nl,dtype=bool)
                    if churn:active[np.arange(nl)%3==churn-1]=False
                    deleted=(np.arange(n)%4==1) if churn==2 else np.zeros(n,bool)
                    for radius in (np.float32(0),np.float32(1),np.nextafter(np.float32(1),np.float32(0)),np.nextafter(np.float32(1),np.float32(2)),np.float32(1000)):
                        keep=np.repeat(active,size)&~deleted[ids]&(squares[ids]<=float(radius)**2)
                        fields=np.where(keep,np.sqrt(squares[ids]).astype('<f4'),np.float32(-987)).astype('<f4')
                        h.update(keep.astype('<i4').tobytes());h.update(fields.tobytes());cases+=1
    return h.hexdigest(),cases
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('qualify',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();h,cases=expected();paths=sorted((a.qualify/'outputs').glob('unit_*.bin'));assert len(paths)==9
    for f in paths:
        assert hashlib.sha256(f.read_bytes()).hexdigest()==h,('CPU byte oracle',f.name)
    a.out.write_text(json.dumps(dict(passed=True,cases_per_process=cases,unit_files=9,expected_sha256=h,scope='Independent CPU-only deterministic post-closure validation; no additional GPU process'),indent=2)+'\n');print('CPU UNIT PAYLOAD PASS',cases,h)
