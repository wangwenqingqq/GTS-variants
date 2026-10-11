"""Exact matrix certification and conservative signed projected-box arithmetic."""
import math,sys
from fractions import Fraction
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'certificate_compression_20261011'))
from certificates import round32,error_bound,RHO
if not __debug__:
    raise RuntimeError('Safety checks require Python without -O')
ETA=1e-8
COUNTS=[1,2,4,8]

def projection_error_bound(d=960):
    u=2.**-53;gamma=((4*d+8)*u)/(1-(4*d+8)*u)
    return gamma*2*math.sqrt(d)

def exact_gram_bound(p):
    rows=[[Fraction.from_float(float(x)) for x in row] for row in p]
    gram=[[sum((x*y for x,y in zip(a,b)),Fraction(0)) for b in rows] for a in rows]
    sums=[sum(map(abs,row),Fraction(0)) for row in gram]
    return max(sums),sums

def certify(p):
    p=np.asarray(p,dtype=np.float64).copy();assert p.shape==(8,960) and np.isfinite(p).all()
    for row in p:
        if row[np.argmax(np.abs(row))]<0:row *= -1
    before,_=exact_gram_bound(p)
    scale=min(1.,1/math.sqrt(float(before)))*(1.-2.**-40)
    p *= scale
    upper,sums=exact_gram_bound(p)
    assert upper<=1,'stored matrix is not contractive'
    nz=np.abs(p[p!=0]);assert len(nz)>0 and nz.min()>=2.**-100
    return p,dict(scale=scale,exact_gram_infinity_bound=str(upper),
        exact_gram_row_sums=[str(x) for x in sums],bound_display=float(upper),
        certified_contractive=True,nonzero_abs_min=float(nz.min()))

def endpoints(minimum,maximum):
    assert projection_error_bound()<ETA and error_bound()<RHO
    return (round32(np.nextafter(minimum-ETA,-np.inf),False),
            round32(np.nextafter(maximum+ETA,np.inf),True))

def prefix_bounds(low,high,query):
    qlo=np.nextafter(query-ETA,-np.inf);qhi=np.nextafter(query+ETA,np.inf)
    gaps=np.maximum(0.,np.maximum(np.nextafter(low.astype(np.float64)-qhi,-np.inf),
                                np.nextafter(qlo-high.astype(np.float64),-np.inf)))
    squares=np.maximum(0.,np.nextafter(gaps*gaps,-np.inf))
    total=np.zeros(low.shape[0],dtype=np.float64);bounds={}
    for j in range(8):
        total=np.maximum(total,np.maximum(0.,np.nextafter(total+squares[:,j],-np.inf)))
        k=j+1
        if k in COUNTS:
            root=np.nextafter(np.sqrt(total),-np.inf)
            bounds[k]=np.maximum(0.,np.nextafter(root-RHO,-np.inf))
    return bounds

def serialize(low,high,k):
    r=len(low);logical=8*k;aligned=((logical+15)//16)*16
    out=np.zeros((r,aligned),dtype=np.uint8)
    values=np.stack([low[:,:k],high[:,:k]],axis=-1).astype('<f4')
    out[:,:logical]=values.reshape(r,2*k).view(np.uint8).reshape(r,logical)
    return out.tobytes()

def decision(rows):
    pca=[r for r in rows if r['family']=='PCA']
    if any(r['level'] in (3,4) and r['k'] in (4,8) and r['oracle_gap_coverage']>=.5 and
           r['incremental_G0_pruning']>=.3 and r['aligned_bytes_per_region']<=64 for r in pca):
        return 'PROJECTION_CERTIFICATE_FEASIBLE'
    last=[r for r in pca if r['k']==8];best=max(r['oracle_gap_coverage'] for r in last)
    if best<.3:return 'LINEAR_PROJECTION_CERTIFICATE_KILLED'
    by={r['level']:r['oracle_gap_coverage'] for r in last}
    if by[5]>=.5 and max(by[3],by[4])<.2:return 'LEAF_ONLY'
    if .3<=best<.5:return 'INTERMEDIATE_NEEDS_DIRECTION_TEST'
    return 'INSUFFICIENT_EVIDENCE'
