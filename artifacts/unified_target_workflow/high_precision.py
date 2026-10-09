#!/usr/bin/env python3
"""Boundary/nearest-neighbor cross-check using exact rationals and independently rounded steps."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import struct
import numpy as np
from validate import load, scores

if not __debug__:
    raise RuntimeError('Assertions must remain enabled')

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();data=load(a.data);r=float(np.float32(0.705625057220459));cutoff=r*r
alpha=(1-Fraction(1,2**53))**(data.shape[1]+3)
rows=[]
for qid in (0,1):
    ref=scores(data,np.arange(len(data)),data[qid])
    chosen=np.unique(np.concatenate([np.argsort(ref)[:8],np.argpartition(abs(ref-cutoff),3)[:3]]))
    for pid in chosen:
        exact=Fraction();rounded=0.
        for x,y in zip(data[pid],data[qid]):
            delta=Fraction.from_float(float(x))-Fraction.from_float(float(y));exact+=delta*delta
            rd=float(delta);square=float(Fraction.from_float(rd)**2)
            rounded=float(Fraction.from_float(rounded)+Fraction.from_float(square))
        assert struct.pack('<d',rounded)==struct.pack('<d',float(ref[pid])),'independent RN-step mismatch'
        assert Fraction.from_float(rounded)>=exact*alpha,'analytic lower factor mismatch'
        rows.append(dict(query=int(qid),physical=int(pid),reference_squared=float(ref[pid]),
                         cutoff_squared=cutoff,reference_hit=bool(ref[pid]<=cutoff),
                         exact_rational_steps_match=True,analytic_lower_factor_pass=True))
result=dict(N=len(data),D=data.shape[1],pairs=len(rows),scope='initial q0 and post-rebuild coordinate q1; nearest-K and nearest-to-range-cutoff physical pairs',
            reference_contract='exact rational subtract then RN float64, exact rational square then RN float64, exact rational running sum then RN float64',rows=rows)
a.output.write_text(json.dumps(result,indent=2)+'\n')
print('PASS exact-rational boundary/nearest RN steps',len(rows))
