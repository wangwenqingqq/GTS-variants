"""Frozen CPU diagnostic, directed matrix proof and nested distance envelopes."""
import csv
import hashlib
import json
import math
import os
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
KS = (8,16,32,64,128,256,512,960)
SIZES = {3:1000,4:100,5:10}
ETA = 1e-8
RHO = 1e-4
# One common margin, not a growing k-specific subtraction: preserves nesting.
COORDINATE_NORM_ERROR = math.nextafter(2*math.nextafter(math.sqrt(960),math.inf)*ETA,math.inf)
MARGIN = math.nextafter(COORDINATE_NORM_ERROR+RHO,math.inf)
if not __debug__:
    raise RuntimeError('Run without -O: fail-closed assertions are required')

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')

def csv_write(p,rows):
    assert rows
    with Path(p).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def freeze_check():
    s=json.loads((HERE/'evidence/SOURCE_FREEZE.json').read_text())
    for name,pin in s['files'].items():assert sha(HERE.parent/name)==pin,name

def cpu_guard():
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert len(os.sched_getaffinity(0))==1
    assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])

def arithmetic_proof():
    # Subtraction/products/prefix additions/sqrt are covered in one common bound.
    gamma=lambda n:Fraction(n,2**53-n)
    root=math.nextafter(math.sqrt(960),math.inf)
    dot=gamma(2*960+8)*Fraction.from_float(math.nextafter(2*root,math.inf))
    assert dot<Fraction.from_float(ETA)
    b=math.nextafter(2*root+COORDINATE_NORM_ERROR+1e-12,math.inf)
    assert gamma(2*960+8)*Fraction.from_float(b)**2<Fraction.from_float(3e-5-1e-12)**2
    sys.path.insert(0,str(HERE.parent/'certificate_compression_20261011'))
    from certificates import error_bound
    assert error_bound()<5e-5 and 3e-5+5e-5<RHO
    return dict(dot_error_rational_upper=str(dot),dot_error_below_ETA=True,
        projected_distance_arithmetic_bound=3e-5,original_distance_arithmetic_bound=5e-5,
        sum_below_RHO=True,coordinate_norm_error=COORDINATE_NORM_ERROR,common_margin=MARGIN,
        assumptions='IEEE FP64 BLAS accumulation (any order/FMA), finite [0,2] FP32 inputs; full stored basis contractive; nonnegative sequential squared prefixes')

def inputs():return json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())

def pin(p,key):
    expected=inputs()[key];assert Path(p).stat().st_size==expected['bytes'] and sha(p)==expected['sha256'],key

def manifest(out):
    save(out/'OUTPUT_MANIFEST.json',{p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()})

def gram_interval(p):
    """Signed dot intervals; never sum absolute outer products."""
    p=np.asarray(p,dtype=np.float64);assert np.isfinite(p).all()
    lo=np.zeros((len(p),len(p)));hi=lo.copy()
    for d in range(p.shape[1]):
        term=p[:,d,None]*p[None,:,d]
        lo=np.nextafter(lo+np.nextafter(term,-np.inf),-np.inf)
        hi=np.nextafter(hi+np.nextafter(term,np.inf),np.inf)
    return lo,hi

def row_sum_up(a):
    total=np.zeros(len(a))
    for j in range(a.shape[1]):total=np.nextafter(total+a[:,j],np.inf)
    return total

def matrix_proof(p):
    lo,hi=gram_interval(p);absolute=np.maximum(np.abs(lo),np.abs(hi))
    upper=float(row_sum_up(absolute).max())
    identity=np.eye(len(p));delta=np.maximum(np.abs(np.nextafter(lo-identity,-np.inf)),np.abs(np.nextafter(hi-identity,np.inf)))
    defect=float(row_sum_up(delta).max())
    return dict(gram_infinity_upper=upper,gram_identity_defect_infinity_upper=defect,
        full_singular_value_lower=math.nextafter(math.sqrt(max(0.,math.nextafter(1-defect,-math.inf))),-math.inf),
        certified_contractive=upper<=1,certificate='signed outer products, separate FP64 mul/add with nextafter after every operation; Gershgorin row sums'),lo,hi

def envelope(d):
    low=np.maximum(0.,np.nextafter(d-MARGIN,-np.inf));high=np.nextafter(d+MARGIN,np.inf)
    return low,high

def prefix_distances(z,q):
    delta=np.subtract(z,q);squared=np.multiply(delta,delta)
    # numpy cumsum is a sequential nonnegative prefix, not a BLAS dot product.
    sums=np.cumsum(squared,axis=1,dtype=np.float64)
    return np.sqrt(sums[:,np.array(KS)-1])

def ordered_project(x,p):
    out=np.zeros((len(x),len(p)))
    for d in range(x.shape[1]):
        term=x[:,d].astype(np.float64)[:,None]*p[None,:,d];out=out+term
    return out

def original_scores(x,q):
    out=np.zeros(len(x))
    for d in range(960):
        diff=x[:,d].astype(np.float64)-float(q[d]);term=diff*diff;out=out+term
    return out

def ratio(n,d):return Fraction(int(n),int(d))

def level_decision(rows):
    by={r['k']:r for r in rows};threshold=next((k for k in KS if ratio(by[k]['hard_safe_objects'],by[k]['hard_truth_objects'])>=Fraction(7,10)),None)
    d1=any(ratio(by[k]['hard_safe_objects'],by[k]['hard_truth_objects'])>=Fraction(7,10) and
        min(ratio(n,d) for n,d in zip(by[k]['hard_safe_counts'],by[k]['hard_truth_counts']))>=Fraction(2,5) for k in KS if k<=64)
    d2=threshold in (128,256) and ratio(by[64]['hard_possible_objects'],by[64]['hard_truth_objects'])<Fraction(7,10)
    d3=ratio(by[256]['hard_possible_objects'],by[256]['hard_truth_objects'])<Fraction(3,5) or ratio(by[256]['hard_possible_counts'][0],by[256]['hard_truth_counts'][0])<Fraction(3,10)
    d4=ratio(by[512]['hard_possible_objects'],by[512]['hard_truth_objects'])<Fraction(7,10)
    predicates=dict(CAPACITY_LIMITED=d1,PCA_DIRECTION_LIMITED=d3,MODERATE_CAPACITY_REQUIREMENT=d2,HIGH_DIMENSION_INTRINSIC=d4)
    return dict(decision=next((n for n,v in predicates.items() if v),'INSUFFICIENT_EVIDENCE'),predicates=predicates,
        overlapping_predicates=[n for n,v in predicates.items() if v],K70_hard_first_tested_guaranteed=threshold)
