#!/usr/bin/env python3
"""Reject incomplete sanitizer sets, negative fields, stale schedule and truncation."""
import csv,json,tempfile
from pathlib import Path
import numpy as np
from range_targets import prior_structure,validate_payload

def rejected(f):
    try:f()
    except AssertionError:return
    raise AssertionError('invalid fixture was admitted')

def check():
    from verify import target_structure,diagnostic_structure
    diagnostics={'native_trace','reuse_trace','bounded_regression','memcheck'}
    diagnostic_structure(diagnostics,diagnostics)
    rejected(lambda:diagnostic_structure(diagnostics|{'racecheck'},diagnostics))
    rejected(lambda:diagnostic_structure(diagnostics,diagnostics|{'extra'}))
    rejected(lambda:diagnostic_structure(diagnostics-{'memcheck'},diagnostics))
    target_rows=[dict(label=l,guard_exit=0,quality_passed=True) for l in ('initial','first_rebuilt')]
    full={'initial','first_rebuilt'};target_structure(target_rows,full,full,True)
    rejected(lambda:target_structure([target_rows[0],target_rows[0]],full,full,True))
    rejected(lambda:target_structure(target_rows[:1],full,full,True))
    rejected(lambda:target_structure(target_rows,full|{'extra'},full,True))
    rejected(lambda:target_structure(target_rows,full,full|{'extra'},True))
    target_structure(target_rows[:1],full,full,False)
    labels=['tree_adapt_1','tree_adapt_memcheck','tree_adapt_racecheck','tree_adapt_synccheck']
    reg={'jobs':[dict(label=l,tool=t) for l,t in zip(labels,[None,'memcheck','racecheck','synccheck'])]}
    rows=[dict(label=l,guard_exit=0,quality_passed=True) for l in labels];prior_structure(reg,rows)
    rejected(lambda:prior_structure({'jobs':reg['jobs'][:3]},rows[:3]))
    wrong=json.loads(json.dumps(reg));wrong['jobs'][3]['tool']='memcheck';rejected(lambda:prior_structure(wrong,rows))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);prefix=root/'out';np.array([0,.25,4.],dtype='<f8').tofile(root/'0.f64')
        np.array([0,1],dtype='<i4').tofile(str(prefix)+'.ids.i32')
        fields=np.array([0,.5],dtype='<f4');fields.tofile(str(prefix)+'.dist.f32')
        row=dict(task='range',query=0,qid=0,count=2,offset=0,ack_ms=1,selected_trees=1)
        def write(r):
            with Path(str(prefix)+'.queries.csv').open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(r));w.writeheader();w.writerow(r)
        write(row);assert validate_payload(prefix,[0],root,3)['quality_passed']
        (-fields).tofile(str(prefix)+'.dist.f32');rejected(lambda:validate_payload(prefix,[0],root,3))
        fields.tofile(str(prefix)+'.dist.f32');write(dict(row,qid=1));rejected(lambda:validate_payload(prefix,[0],root,3))
        write(row);fields[:1].tofile(str(prefix)+'.dist.f32');rejected(lambda:validate_payload(prefix,[0],root,3))
    print('PASS exact sanitizer identities, positive payload, negative fields, wrong qid and truncated output')
if __name__=='__main__':check()
