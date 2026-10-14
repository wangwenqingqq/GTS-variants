"""Independent original-order golden arithmetic and adversarial packed fixtures."""
import argparse
import importlib.util
import ctypes as C
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gate5_tests',ROOT.parent/'proof_per_byte_512_gate5_20261013/test_probe.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
same_bits=previous.same_bits


def require(ok,message):
    if not ok:raise RuntimeError(message)


def load(path):
    lib=previous.load(path);pointer=C.c_void_p
    lib.packed_subset.argtypes=[pointer,pointer,C.c_size_t,C.c_int,pointer,pointer,C.c_int,pointer]
    lib.packed_subset.restype=C.c_int
    lib.packed_full_audit.argtypes=[pointer,pointer,C.c_size_t,C.c_int,pointer,pointer]
    lib.packed_full_audit.restype=C.c_int
    return lib


def call(lib,x,q,pi,sectors=None):
    require(x.ndim==2 and x.dtype==q.dtype==np.dtype('<f4') and x.flags.c_contiguous and q.flags.c_contiguous,'invalid packed storage')
    require(q.shape==(x.shape[1],) and pi.shape==q.shape and pi.dtype==np.dtype('<u2') and pi.flags.c_contiguous,'invalid permutation/query shape')
    out=np.full(len(x),np.nan,dtype='<f8');base=[x.ctypes.data,q.ctypes.data,len(x),x.shape[1],pi.ctypes.data]
    if sectors is None:rc=lib.packed_full_audit(*base,out.ctypes.data)
    else:
        sectors=np.ascontiguousarray(sectors,dtype='<u2');require(sectors.ndim==1,'invalid sector array')
        rc=lib.packed_subset(*base,sectors.ctypes.data,len(sectors),out.ctypes.data)
    require(rc==0,'packed native rejected input: '+str(rc));return out


def golden(x,q,pi,sectors=None):
    inverse=np.argsort(pi);mask=np.ones(x.shape[1],dtype=bool)
    if sectors is not None:
        mask[:]=False;mask[pi.reshape(-1,8)[sectors].reshape(-1)]=True
    out=np.zeros(len(x),dtype='<f8')
    for j in np.flatnonzero(mask):
        p=int(inverse[j]);delta=x[:,p].astype(np.float64)-float(q[p]);out+=delta*delta
    return out


def fixtures(lib):
    require(sys.flags.optimize==0,'Python assertions must remain enabled')
    previous.fixtures(lib);rng=np.random.default_rng(20261014);checked=0
    for d in (8,16,128,136,960):
        x=rng.normal(0,.1,(53,d)).astype('<f4');q=x[0].copy();x[1]=q;x[2]=0.;x[3]=-0.
        x[4]=np.nextafter(np.float32(0),np.float32(1));x[5]=np.finfo(np.float32).max;x[6]=-np.finfo(np.float32).max
        pi=rng.permutation(d).astype('<u2');xp=np.ascontiguousarray(x[:,pi]);qp=q[pi].copy()
        ids=np.sort(rng.choice(d//8,min(16,d//8),replace=False)).astype('<u2')
        full=call(lib,xp,qp,pi);part=call(lib,xp,qp,pi,ids)
        require(same_bits(full,golden(xp,qp,pi)) and same_bits(part,golden(xp,qp,pi,ids)),'packed ordered bits differ')
        original=np.zeros(len(x),dtype='<f8')
        for j in range(d):delta=x[:,j].astype(np.float64)-float(q[j]);original+=delta*delta
        require(same_bits(full,original) and np.all(part<=full),'permutation parity or safe subset failed')
        for cut in (0.,float(part[10]),float(full[11]),1e-300,1e80):require(not np.any((part>cut)&(full<=cut)),'false rejection')
        checked+=len(x)
    x=np.array([[2.**27,1,1,1,0,0,0,0]],dtype='<f4');q=np.zeros(8,dtype='<f4');pi=np.arange(7,-1,-1,dtype='<u2')
    xp=np.ascontiguousarray(x[:,pi]);qp=q[pi].copy();full=call(lib,xp,qp,pi)
    require(full[0]==2.**54 and golden(xp,qp,np.arange(8,dtype='<u2'))[0]==2.**54+4,'order-sensitivity fixture lost')
    x=np.ones((7,960),dtype='<f4');q=np.zeros(960,dtype='<f4');pi=np.arange(959,-1,-1,dtype='<u2');ids=np.arange(16,dtype='<u2')
    require(np.all(call(lib,x,q,pi,ids)==128) and np.all(call(lib,x,q,pi)==960),'tie/equality fixture differs')
    bads=[(np.zeros(960,dtype='<u2'),ids),(pi,np.zeros(16,dtype='<u2')),(pi,np.arange(15,-1,-1,dtype='<u2')),(pi,np.full(16,120,dtype='<u2')),(pi,np.array([],dtype='<u2'))]
    for p,s in bads:
        try:call(lib,x,q,p,s)
        except RuntimeError:pass
        else:raise RuntimeError('invalid metadata admitted')
    for value in (np.nan,np.inf,-np.inf):
        for target in ('x','q'):
            xx=x.copy();qq=q.copy()
            if target=='x':xx[0,0]=value
            else:qq[0]=value
            for s in (None,ids):
                try:call(lib,xx,qq,pi,s)
                except RuntimeError:pass
                else:raise RuntimeError('nonfinite packed input admitted')
    print(f'PASS {checked+8} additional packed rows; original bits, subset bounds, guards and order counterexample')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);fixtures(load(p.parse_args().library))
