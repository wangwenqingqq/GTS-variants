#!/usr/bin/env python3
"""Qualify native sectors against an independent stable-sort NumPy reference."""
import argparse
import ctypes as C
import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('test_probe',ROOT.parent/'proof_per_byte_512_gate5_20261013/test_probe.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
sys.modules['test_probe']=previous


def require(ok, message):
    if not ok: raise RuntimeError(message)


def load(path):
    lib = previous.load(path)
    lib.sector_oracle.argtypes = lib.oracle_scores.argtypes
    lib.sector_oracle.restype = C.c_int
    lib.sector_subset.argtypes = lib.subset_scores.argtypes
    lib.sector_subset.restype = C.c_int
    return lib


def inputs(x,q):
    require(x.ndim==2 and x.shape[1]%8==0 and x.dtype==q.dtype==np.dtype('<f4'), 'invalid coordinate storage')
    require(x.flags.c_contiguous and q.flags.c_contiguous and q.shape==(x.shape[1],), 'invalid coordinate shape')


def oracle(lib,x,q,k=16):
    inputs(x,q); outputs=[np.full(len(x),np.nan,dtype='<f8') for _ in range(3)]
    rc=lib.sector_oracle(x.ctypes.data,q.ctypes.data,len(x),x.shape[1],k,*(v.ctypes.data for v in outputs))
    require(rc==0,'native sector oracle rejected input: '+str(rc))
    return outputs


def subset(lib,x,q,sectors):
    inputs(x,q); sectors=np.ascontiguousarray(sectors,dtype='<u2')
    out=np.full(len(x),np.nan,dtype='<f8')
    rc=lib.sector_subset(x.ctypes.data,q.ctypes.data,len(x),x.shape[1],sectors.ctypes.data,len(sectors),out.ctypes.data)
    require(rc==0,'native sector subset rejected input: '+str(rc))
    return out


def golden(x,q,k):
    delta=x.astype(np.float64)-q.astype(np.float64); terms=delta*delta
    scores=np.zeros((len(x),x.shape[1]//8),dtype='<f8')
    for h in range(8): scores+=terms[:,h::8]
    chosen=np.argsort(-scores,axis=1,kind='stable')[:,:k]
    mask=np.zeros(scores.shape,dtype=bool);np.put_along_axis(mask,chosen,True,axis=1)
    b0,best,full=(np.zeros(len(x),dtype='<f8') for _ in range(3))
    for j in range(x.shape[1]):
        full+=terms[:,j]
        if j<8*k: b0+=terms[:,j]
        best+=np.where(mask[:,j//8],terms[:,j],0.)
    return b0,best,full


def fixtures(lib):
    require(sys.flags.optimize==0,'Python assertions must remain enabled')
    previous.fixtures(lib)
    rng=np.random.default_rng(20261014);checked=0
    for d in (8,16,128,136,960):
        k=min(16,d//8);x=rng.normal(0,.1,(53,d)).astype('<f4');q=x[0].copy()
        x[1]=q;x[2]=0.;x[3]=-0.;x[4]=np.nextafter(np.float32(0),np.float32(1))
        x[5]=np.finfo(np.float32).max;x[6]=-np.finfo(np.float32).max
        got=oracle(lib,x,q,k);want=golden(x,q,k)
        require(all(previous.same_bits(g,w) for g,w in zip(got,want)), 'sector stable-top-k/ordered bits differ')
        sectors=np.sort(rng.choice(d//8,k,replace=False)).astype('<u2')
        part=subset(lib,x,q,sectors);expected=np.zeros(len(x),dtype='<f8')
        for s in sectors:
            for h in range(8):
                j=int(s)*8+h;delta=x[:,j].astype(np.float64)-float(q[j]);expected+=delta*delta
        require(previous.same_bits(part,expected) and np.all(part<=got[2]),'sector subset differs')
        for cutoff in (0.,float(part[10]),float(got[2][11]),1e-300,1e80):
            require(not np.any((part>cutoff)&(got[2]<=cutoff)),'sector false rejection')
        checked+=len(x)
    x=np.ones((7,960),dtype='<f4');q=np.zeros(960,dtype='<f4')
    b0,best,full=oracle(lib,x,q)
    require(np.all(b0==128) and np.all(best==128) and np.all(full==960),'sector tie/equality differs')
    for target in ('data','query'):
        for v in (np.nan,np.inf,-np.inf):
            xx=x.copy();qq=q.copy()
            if target=='data':xx[0,0]=v
            else:qq[0]=v
            for call in (lambda:oracle(lib,xx,qq),lambda:subset(lib,xx,qq,np.arange(16,dtype='<u2'))):
                try:call()
                except RuntimeError:pass
                else:raise RuntimeError('nonfinite sector input admitted')
    for ids in (np.arange(15,-1,-1,dtype='<u2'),np.zeros(16,dtype='<u2'),np.full(16,120,dtype='<u2')):
        try:subset(lib,x,q,ids)
        except RuntimeError:pass
        else:raise RuntimeError('invalid sector IDs admitted')
    for k in (0,121):
        try:oracle(lib,x,q,k)
        except RuntimeError:pass
        else:raise RuntimeError('invalid sector budget admitted')
    print(f'PASS: {checked+7} additional sector rows; ordered bits, stable grouping, safety, ties, equality and guards')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True)
    fixtures(load(p.parse_args().library))
