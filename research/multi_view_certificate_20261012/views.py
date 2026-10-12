"""Frozen view layouts and dimension-generic conservative bounds."""
import hashlib, json, math, sys
from fractions import Fraction
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
sys.path.insert(0, str(HERE.parent / 'certified_navigation_20261010'))
from projection_math import exact_gram_bound, endpoints, ETA, RHO, projection_error_bound, error_bound
from audit import sha, save

def certify(p):
    p = np.asarray(p, dtype=np.float64).copy()
    assert p.ndim == 2 and p.shape[1] == 960 and np.isfinite(p).all()
    for row in p:
        if row[np.argmax(np.abs(row))] < 0: row *= -1
    before, _ = exact_gram_bound(p)
    scale = min(1., 1 / math.sqrt(float(before))) * (1. - 2.**-40)
    p *= scale
    upper, sums = exact_gram_bound(p)
    assert upper <= 1 and np.abs(p[p != 0]).min() >= 2.**-100
    return p, dict(scale=scale, exact_gram_infinity_bound=str(upper),
                   exact_gram_row_sums=[str(s) for s in sums], certified_contractive=True)

def bounds(lo, hi, q):
    assert lo.shape == hi.shape and lo.shape[1] == len(q) and len(q) in (1, 2, 4, 8)
    qlo = np.nextafter(q - ETA, -np.inf); qhi = np.nextafter(q + ETA, np.inf)
    gap = np.maximum(0., np.maximum(np.nextafter(lo.astype('f8') - qhi, -np.inf),
                                    np.nextafter(qlo - hi.astype('f8'), -np.inf)))
    sq = np.maximum(0., np.nextafter(gap * gap, -np.inf)); total = np.zeros(len(lo))
    for j in range(len(q)):
        total = np.maximum(total, np.maximum(0., np.nextafter(total + sq[:, j], -np.inf)))
    return np.maximum(0., np.nextafter(np.nextafter(np.sqrt(total), -np.inf) - RHO, -np.inf))

def scalar_bound(lo, hi, q):
    total = 0.
    for a, b, x in zip(lo, hi, q):
        gap = max(0., math.nextafter(float(a) - math.nextafter(float(x) + ETA, math.inf), -math.inf),
                  math.nextafter(math.nextafter(float(x) - ETA, -math.inf) - float(b), -math.inf))
        square = max(0., math.nextafter(gap * gap, -math.inf))
        total = max(total, max(0., math.nextafter(total + square, -math.inf)))
    return max(0., math.nextafter(math.nextafter(math.sqrt(total), -math.inf) - RHO, -math.inf))

def configurations():
    physical = [{'config':'PCA8','family':'SINGLE','layout':'1x8','groups':[list(range(8))]}]
    for v, k in [(2,4),(4,2),(8,1)]:
        physical.append(dict(config=f'BLOCKS_{v}x{k}', family='BLOCKS', layout=f'{v}x{k}',
                             groups=[list(range(i*k, (i+1)*k)) for i in range(v)]))
    for v,k in [(2,4),(4,2)]:
        physical.append(dict(config=f'INTERLEAVED_{v}x{k}', family='INTERLEAVED', layout=f'{v}x{k}',
                             groups=[list(range(i,8,v)) for i in range(v)]))
    for v,k in [(2,4),(4,2),(8,1)]:
        physical.append(dict(config=f'SPREAD32_{v}x{k}', family='SPREAD32', layout=f'{v}x{k}',
                             groups=[[8+j for j in range(i,8,v)] for i in range(v)]))
    start=16
    for v,k in [(2,4),(4,2),(8,1)]:
        physical.append(dict(config=f'RANDOM_{v}x{k}', family='RANDOM', layout=f'{v}x{k}',
                             groups=[list(range(start+i*k,start+(i+1)*k)) for i in range(v)]))
        start += 8
    aliases=[dict(config=f'D1_{v}x{k}',target=f'BLOCKS_{v}x{k}') for v,k in [(2,4),(4,2),(8,1)]]
    aliases.append(dict(config='INTERLEAVED_8x1',target='BLOCKS_8x1'))
    assert len(physical)==12 and len(aliases)==4 and start==40
    return physical, aliases

def ratios(row):
    return Fraction(row['hard_pruned_objects'], row['hard_truth_prunable_objects']), Fraction(row['pruned_objects'], row['truth_prunable_objects']), min(Fraction(n,d) for n,d in zip(row['hard_query_pruned'], row['hard_query_truth_prunable']))

def decision(rows):
    base={r['level']:ratios(r) for r in rows if r['config']=='PCA8'}
    multi=[r for r in rows if r['config']!='PCA8']; signal=[]; strong=[]; average=[]; leaf=[]
    for r in multi:
        h,a,w=ratios(r); bh,ba,bw=base[r['level']]; gain=h-bh
        if r['level'] in (3,4):
            if h>=Fraction(55,100) and gain>=Fraction(15,100) and w>=Fraction(25,100): signal.append(r['config']+':L'+str(r['level']))
            if h>=Fraction(65,100) and w>=Fraction(40,100) and a>=Fraction(60,100): strong.append(r['config']+':L'+str(r['level']))
            if gain>=Fraction(10,100) and w-bw<Fraction(5,100): average.append(r['config']+':L'+str(r['level']))
    for r in (r for r in multi if r['level']==5):
        if ratios(r)[0]-base[5][0]>=Fraction(1,10) and all(ratios(t)[0]-base[t['level']][0]<Fraction(1,10) for t in multi if t['config']==r['config'] and t['level'] in (3,4)): leaf.append(r['config'])
    killed=all(ratios(r)[0]-base[r['level']][0]<Fraction(1,20) for r in multi)
    verdict=('MULTI_VIEW_CERTIFICATE_SUPPORTED' if strong else 'MULTI_VIEW_SIGNAL' if signal else 'MULTI_VIEW_LINEAR_CERTIFICATE_KILLED' if killed else 'AVERAGE_ONLY' if average else 'LEAF_ONLY_MULTI_VIEW' if leaf else 'INSUFFICIENT_EVIDENCE')
    return dict(decision=verdict,strong_cells=strong,promotion_cells=signal,K1_all_cells_gain_below_5pp=killed,average_only_cells=average,leaf_only_configs=leaf)
