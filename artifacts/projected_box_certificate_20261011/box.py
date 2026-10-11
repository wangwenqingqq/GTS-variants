#!/usr/bin/env python3
"""One PCA-4 projected box with interval and represented-Gram safety bounds."""
import ctypes
import json
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
BALL=HERE.parent/'block_local_ball_20261011'
sys.path.insert(0,str(BALL))
import ball
from ball import sha,save,outside_repo,raw,stats,validate_partition
if not __debug__:raise RuntimeError('Assertions required')


def library(path):
    lib=ctypes.CDLL(str(Path(path).resolve()))
    lib.projections.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_int64,ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.c_int]
    lib.projections.restype=ctypes.c_int;return lib


def project(lib,x,u,scalar=False):
    assert x.dtype==np.float32 and x.ndim==2 and x.flags.c_contiguous and 0<x.shape[1]<=4096 and len(x)>0
    assert u.shape==(x.shape[1],4) and u.dtype==np.float64 and u.flags.c_contiguous and np.isfinite(u).all() and np.max(np.abs(u))<=1
    z=np.empty((len(x),4));m=np.empty(len(x))
    rc=lib.projections(x.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(x),x.shape[1],u.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),z.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),m.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),int(scalar))
    assert rc==0 and np.isfinite(z).all() and np.isfinite(m).all() and np.all(m>=0),'invalid projection input/rounding'
    return z,m


def up(x):return np.nextafter(x,np.inf)
def down(x):return np.nextafter(x,-np.inf)


def projection_interval(z,m,u):
    d=len(u);assert 0<d<=4096 and z.shape==(len(m),4) and u.shape==(d,4)
    assert np.isfinite(z).all() and np.isfinite(m).all() and np.all(m>=0) and np.isfinite(u).all() and np.max(np.abs(u))<=1
    e=(4*d+16)*2.**-52
    b=up(up(m[:,None]*np.max(np.abs(u),axis=0)[None,:])*d)
    eta=up((2*d+1)*np.nextafter(0.,1.))
    err=up(up(e*b)+eta)
    return down(z-err),up(z+err)


def fraction_upper(v):
    x=float(v)
    if Fraction.from_float(x)<v:x=float(up(x))
    assert Fraction.from_float(x)>=v and np.isfinite(x)
    return x


def gram_proof(u):
    assert u.dtype==np.float64 and u.ndim==2 and u.shape[1]==4 and 0<len(u)<=4096 and np.isfinite(u).all() and np.max(np.abs(u))<=1
    f=[[Fraction.from_float(float(v)) for v in row] for row in u]
    g=[[sum((row[j]*row[k] for row in f),Fraction(0)) for k in range(4)] for j in range(4)]
    bound=max(sum(abs(v) for v in row) for row in g);assert bound>0
    deviation=max(sum(abs(v-(1 if j==k else 0)) for k,v in enumerate(row)) for j,row in enumerate(g))
    return dict(gram_exact=[[str(v) for v in row] for row in g],operator_norm_squared_exact_row_sum=str(bound),operator_norm_squared_upper=fraction_upper(bound),gram_infinity_deviation_upper=fraction_upper(deviation))


def lower2(ql,qh,lo,hi):
    assert ql.shape==qh.shape==(4,) and lo.ndim==2 and lo.shape==hi.shape and lo.shape[1]==4
    assert all(np.isfinite(a).all() for a in (ql,qh,lo,hi)) and np.all(ql<=qh) and np.all(lo<=hi)
    delta=np.maximum(0,np.maximum(down(lo-qh),down(ql-hi)))
    squares=np.maximum(0,down(delta*delta));result=np.zeros(len(lo))
    for j in range(4):result=np.maximum(0,down(result+squares[:,j]))
    return result


def threshold(radius,d,a2):
    assert np.isfinite(radius) and radius>=0 and float(np.float32(radius))==radius and np.isfinite(a2) and a2>0 and 0<d<=4096
    e=(4*d+16)*2.**-52
    return float(up(a2*up((radius*radius)/(1-e))))


def keep(ql,qh,lo,hi,radius,d,a2):return lower2(ql,qh,lo,hi)<=threshold(radius,d,a2)


def select_directions(cov):
    assert cov.ndim==2 and cov.shape[0]==cov.shape[1] and np.isfinite(cov).all() and np.array_equal(cov,cov.T)
    values,vectors=np.linalg.eigh(cov);order=np.argsort(-values,kind='stable');values=values[order];u=vectors[:,order[:4]].copy()
    tol=1e-10*max(1.,float(values[0]));assert np.all(values[:4]-values[1:5]>tol),'PCA top-four degeneracy'
    signs=[]
    for j in range(4):
        i=int(np.argmax(np.abs(u[:,j])));signs.append(i)
        if u[i,j]<0:u[:,j]*=-1
    u=np.ascontiguousarray(u)
    residual=float(np.max(np.linalg.norm(cov@u-u*values[:4],axis=0))/max(1.,np.linalg.norm(cov,ord='fro')))
    assert residual<=1e-10 and np.isfinite(values).all()
    g=gram_proof(u);assert g['gram_infinity_deviation_upper']<=1e-10
    return values,u,dict(sign_coordinates=signs,eigen_residual_relative_fro=residual,**g)


METRICS=['global4_surviving_blocks','local_ball_surviving_blocks','projected_box_surviving_blocks','oracle_required_blocks','global4_survival_fraction','local_ball_survival_fraction','projected_box_survival_fraction','oracle_fraction','projected_box_false_prune','projected_box_oracle_gap','true_hits','surviving_objects','global4_surviving_objects','local_ball_surviving_objects','query_projection_ops','numeric_maxabs_reductions','summary_endpoint_reads','direction_coordinate_bytes','modeled_total_fullD_equivalent_work','modeled_dot_only_plus_verification','modeled_total_coordinate_bytes']


def summarize(rows):
    return [dict(snapshot=n,queries=32,statistics={k:stats([r[k] for r in rows if r['snapshot']==n]) for k in METRICS}) for n in ('initial','first_rebuilt')]


def decision(summary):
    assert len(summary)==2 and {s['snapshot'] for s in summary}=={'initial','first_rebuilt'}
    ss=[s['statistics'] for s in summary];assert all(s['projected_box_false_prune']['max']==0 for s in ss)
    m=[s['projected_box_survival_fraction']['mean'] for s in ss];tail=[s['projected_box_survival_fraction']['p90'] for s in ss]
    g=[s['global4_survival_fraction']['mean'] for s in ss];gain=[a-b for a,b in zip(g,m)]
    go=max(m)<=.5 and max(tail)<=.7 and min(gain)>=.15
    no=any(v>.65 and improvement<.1 for v,improvement in zip(m,gain))
    cond=not go and not no and max(m)>.5 and max(m)<=.65 and min(gain)>=.15
    return dict(decision='GO_ANISO' if go else 'NO_GO_PROJECTED_BOX' if no else 'CONDITIONAL_ANISO',reason='joint_mean_tail_gain_pass' if go else 'same_snapshot_high_survival_small_gain' if no else 'specified_conditional_band' if cond else 'uncovered_interval',strong_GO=go and max(m)<=.35,K8_admissible=cond,GPU_admitted_this_round=False,snapshots=[s['snapshot'] for s in summary],projected_mean=m,projected_p90=tail,global4_mean=g,improvement_percentage_points=[100*x for x in gain],scope='Only initial-fitted PCA4, fixed S1/P2 and these original 64 queries; not all anisotropy/projection families')


def sources():
    files=[HERE/x for x in ('CONTRACT.json','NUMERICS.md','project.cpp','box.py','experiment.py','test_box.py')]
    return {**ball.sources(),**{str(p.relative_to(HERE.parent)):sha(p) for p in files}}


def bind(a):
    c=json.loads((HERE/'CONTRACT.json').read_text());_,prior,inputs,files=ball.bind(a)
    for name,key in [('PROOF.json','local_ball_proof_sha256'),('VERIFY.json','local_ball_verify_sha256'),('SUMMARY_COMPARISON.json','local_ball_result_sha256')]:
        p=a.ball/name;assert sha(p)==c[key],('ball identity',name);files[p]=sha(p)
    bp=json.loads((a.ball/'PROOF.json').read_text());bv=json.loads((a.ball/'VERIFY.json').read_text())
    assert bp['passed'] and bv['passed'] and bv['proof_sha256']==sha(a.ball/'PROOF.json')
    assert bp['raw_files']['SUMMARY_COMPARISON.json']==sha(a.ball/'SUMMARY_COMPARISON.json')
    return c,prior,inputs,files
