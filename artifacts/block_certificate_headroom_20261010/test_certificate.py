#!/usr/bin/env python3
"""Portable correctness tests; compile the same helper before running."""
import argparse, tempfile, unittest,subprocess,os,shutil,sys
from pathlib import Path
from decimal import Decimal,localcontext
import numpy as np
from run import admitted_D,interval,radius_upper,rejected,blocks,raw,load_library,distance,layouts,NODE
import build

class CertificateTest(unittest.TestCase):
    def test_decimal_envelope_and_reference(self):
        rng=np.random.Generator(np.random.PCG64(41));cases=[]
        for d in (1,32,960,4096):
            x=rng.normal(size=(3,d)).astype(np.float32);x[1]=x[0];x[2]=np.nextafter(x[0],np.float32(np.inf));cases.append(x)
        a=np.array([0,np.nextafter(np.float32(0),np.float32(1)),np.finfo(np.float32).max,-np.finfo(np.float32).max,1,-1],dtype=np.float32);cases.append(np.stack([a,-a,np.nextafter(a,np.float32(0))]))
        for x in cases:
            scores=distance(LIB,x,0);lo,hi=interval(scores,x.shape[1])
            with localcontext() as ctx:
                ctx.prec=220
                for i,row in enumerate(x):
                    S=sum((Decimal.from_float(float(v))-Decimal.from_float(float(w)))**2 for v,w in zip(row,x[0]));norm=S.sqrt()
                    self.assertLessEqual(Decimal.from_float(float(lo[i])),norm)
                    self.assertGreaterEqual(Decimal.from_float(float(hi[i])),norm)
                    s=0.
                    for v,w in zip(row,x[0]):delta=float(v)-float(w);s+=delta*delta
                    self.assertEqual(scores[i].view(np.uint64),np.float64(s).view(np.uint64))
    def test_boundary_duplicates_and_safety(self):
        x=np.array([[0],[.5],[1],[1],[np.nextafter(np.float32(1),np.float32(2))],[2]],dtype=np.float32)
        score=distance(LIB,x,0);lo,hi=interval(score,1);r=radius_upper(1.,1)
        reject=rejected(lo,hi,lo[0],hi[0],r);self.assertFalse(reject[2]);self.assertFalse(reject[3]);self.assertTrue(reject[5]);self.assertEqual(int((score<=1).sum()),4)
        self.assertEqual(blocks(score<=1,np.array([0,1,2,3,4,5]),2).tolist(),[True,True,False])
        for q in range(len(x)):
            qs=distance(LIB,x,q);ql,qh=interval(score[[q]],1)
            keep=~rejected(lo,hi,ql[0],qh[0],r);self.assertTrue(np.all(keep[qs<=1]))
    def test_malformed_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'raw';p.write_bytes(b'\0'*17)
            with self.assertRaises(AssertionError):raw(p,'<f8',(2,))
        for values in ([np.nan],[np.inf],[-1.]):
            with self.assertRaises(AssertionError):interval(np.array(values),960)
        with self.assertRaises(AssertionError):distance(LIB,np.array([[np.nan],[0]],dtype=np.float32),0)
    def test_standalone_executed_copy_import(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            for name in ('run.py','test_certificate.py'):shutil.copyfile(Path(__file__).parent/name,folder/name)
            baseline=Path(build.__file__).resolve().parent
            subprocess.run([sys.executable,'-c','import run; import test_certificate'],cwd=folder,env={**os.environ,'PYTHONPATH':str(baseline)},check=True)
    def test_joint_admission(self):
        cs=[dict(snapshot=s,layout='L1',strategy='S0',pivot_count=4,block_size=256,statistics={'surviving_block_fraction':{'mean':.65}}) for s in ('initial','first_rebuilt')]
        os=[dict(snapshot=s,layout='L1',block_size=256,statistics={'oracle_fraction':{'mean':.5}}) for s in ('initial','first_rebuilt')]
        self.assertEqual(admitted_D(cs,os),[])
        for row in os:row['statistics']['oracle_fraction']['mean']=.2
        self.assertEqual(admitted_D(cs,os),[['L1','S0',4]])
        cs[0]['statistics']['surviving_block_fraction']['mean']=.78
        self.assertEqual(admitted_D(cs,os),[])
    def test_dfs_and_distinct_occurrences(self):
        nodes=np.zeros(1111,dtype=NODE);empty=np.ones(1111,dtype=np.int32)
        # One live path terminating in two depth-3 leaves; duplicate coordinates are still four row IDs.
        for i,size,lid,leaf in [(0,4,0,0),(1,4,0,0),(11,4,0,0),(111,2,0,1),(112,2,2,1)]:
            nodes[i]['size']=size;nodes[i]['lid']=lid;nodes[i]['leaf']=leaf;empty[i]=0
        order=np.array([2,0,3,1],dtype=np.int32);ls=layouts(nodes,empty,order)
        self.assertEqual(ls['L1'].tolist(),[0,2,1,3]);self.assertEqual(ls['L3'].tolist(),order.tolist())
        with self.assertRaises(AssertionError):layouts(nodes,empty,np.array([2,2,3,1],dtype=np.int32))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);a,remaining=p.parse_known_args();LIB=load_library(a.library);unittest.main(argv=['test_certificate.py',*remaining])
