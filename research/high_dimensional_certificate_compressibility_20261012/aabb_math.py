"""Directed FP32 region enclosures under the inherited exact-search contract."""
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from projection_capacity_diagnosis_20261012 import common as prior
KS=(32,64,128)
SIZES=prior.SIZES
ETA,MARGIN=prior.ETA,prior.MARGIN
sha,save,csv_write=prior.sha,prior.save,prior.csv_write

def identity():return json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())

def pin(path,key):
    expected=identity()[key]
    assert Path(path).stat().st_size==expected['bytes'] and sha(path)==expected['sha256'],key

def freeze_check():
    for name,digest in json.loads((HERE/'evidence/SOURCE_FREEZE.json').read_text())['files'].items():
        assert sha(HERE.parent/name)==digest,name

def build_check(build):
    receipt=json.loads((build/'BUILD_VALIDATION.json').read_text())
    assert receipt['status']=='PASS' and receipt['source_freeze_sha256']==sha(HERE/'evidence/SOURCE_FREEZE.json')
    manifest=json.loads((build/'OUTPUT_MANIFEST.json').read_text())
    for name in ['aabb_raw.npz','BUILD_VALIDATION.json']:
        path=build/name;expected=manifest[name]
        assert path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256'],name
    return receipt

def outward32(x,direction):
    x=np.asarray(x,dtype=np.float64);assert np.isfinite(x).all()
    y=x.astype('<f4');wrong=y.astype(np.float64)>x if direction<0 else y.astype(np.float64)<x
    y[wrong]=np.nextafter(y[wrong],np.float32(-np.inf if direction<0 else np.inf))
    assert np.isfinite(y).all()
    assert np.all(y.astype(np.float64)<=x) if direction<0 else np.all(y.astype(np.float64)>=x)
    return y

def endpoints(z):
    assert z.ndim==3 and np.isfinite(z).all()
    return (outward32(np.nextafter(z.min(axis=1)-ETA,-np.inf),-1),
            outward32(np.nextafter(z.max(axis=1)+ETA,np.inf),1))

def bounds(lo,hi,q):
    """Prefixes share an ordered nondecreasing directed sum and keeper margin."""
    lo,hi,q=[np.asarray(v,dtype=np.float64) for v in (lo,hi,q)]
    assert lo.shape==hi.shape and lo.ndim==2 and lo.shape[1]==128 and q.shape==(128,)
    assert all(np.isfinite(v).all() for v in (lo,hi,q)) and np.all(lo<=hi)
    qlo=np.nextafter(q-ETA,-np.inf);qhi=np.nextafter(q+ETA,np.inf)
    total=np.zeros(len(lo));result=[]
    for j in range(128):
        gap=np.maximum(0.,np.maximum(np.nextafter(lo[:,j]-qhi[j],-np.inf),np.nextafter(qlo[j]-hi[:,j],-np.inf)))
        term=np.maximum(0.,np.nextafter(gap*gap,-np.inf))
        total=np.maximum(total,np.maximum(0.,np.nextafter(total+term,-np.inf)))
        if j+1 in KS:
            norm=np.maximum(0.,np.nextafter(np.sqrt(total),-np.inf))
            result.append(np.maximum(0.,np.nextafter(norm-MARGIN,-np.inf)))
    return np.array(result)

def scalar_bounds(lo,hi,q):
    down=lambda v:math.nextafter(v,-math.inf)
    total=0.;out=[]
    for j in range(128):
        gap=max(0.,down(float(lo[j])-math.nextafter(float(q[j])+ETA,math.inf)),down(down(float(q[j])-ETA)-float(hi[j])))
        term=max(0.,down(gap*gap));total=max(total,max(0.,down(total+term)))
        if j+1 in KS:out.append(max(0.,down(max(0.,down(math.sqrt(total)))-MARGIN)))
    return np.array(out)

def fraction(n,d):return Fraction(int(n),int(d)) if d else None

def ratio(n,d):return float(fraction(n,d)) if d else None

def stage_a(rows):
    by={(r['k'],r['level']):r for r in rows};a=by[64,4];b=by[128,4];c=by[128,3]
    ge=lambda n,d,v:d>0 and fraction(n,d)>=v
    lt=lambda n,d,v:d>0 and fraction(n,d)<v
    normal=(ge(a['hard_aabb_objects'],a['hard_point_objects'],Fraction(7,10)) and ge(a['hard_aabb_objects'],a['hard_truth_objects'],Fraction(3,5)) and ge(a['canary_aabb_objects'],a['canary_point_objects'],Fraction(1,2)))
    strong=(ge(a['hard_aabb_objects'],a['hard_point_objects'],Fraction(17,20)) and ge(c['hard_aabb_objects'],c['hard_point_objects'],Fraction(7,10)))
    kill=(lt(a['hard_aabb_objects'],a['hard_point_objects'],Fraction(1,2)) and lt(b['hard_aabb_objects'],b['hard_point_objects'],Fraction(3,5)))
    assert not(normal and kill)
    decision=('AABB_COMPRESSION_STRONGLY_SUPPORTED' if normal and strong else 'HIGH_DIMENSION_CERTIFICATE_COMPRESSIBLE' if normal else 'AXIS_ALIGNED_HIGH_DIM_COMPRESSION_KILLED' if kill else 'INSUFFICIENT_EVIDENCE')
    return dict(decision=decision,normal_promotion=normal,strong_predicate=strong,kill_predicate=kill,stage_B_admitted=normal,exact_rational_thresholds=True)

def manifest(out):prior.manifest(out)
