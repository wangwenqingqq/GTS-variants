#!/usr/bin/env python3
"""Portable checks of fixed budget, order balance and paired estimator."""
import campaign
assert campaign.bootstrap([1]*6)==dict(ratio=1.,CI95=[1.,1.])
assert len(campaign.job_list('primary'))==18
for left,right in (('A','B'),('B','C'),('A','C')):
    assert sum(order.index(left)<order.index(right) for order in campaign.ORDERS)==3
jobs=campaign.job_list('observer')
assert len(jobs)==6 and [j['observe'] for j in jobs]==[False,True,True,False,False,True]
for i in range(1,7):assert ''.join(j['mode'] for j in campaign.job_list('primary') if j['round']==i)==campaign.ORDERS[i-1]
print('PASS fixed sample budget, three/three order balance and bootstrap parity')

# Integrity failures must remain fatal even when a previous CPU quality marker exists.
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
with tempfile.TemporaryDirectory(prefix='gts_phase_b_gate_test_') as tmp:
    work=Path(tmp);guard=work/'guard';guard.mkdir();(work/'runs').mkdir();(work/'outputs').mkdir()
    jobs=campaign.job_list('observer');rows=[]
    record=dict(stage='observer',jobs=jobs,campaign_source_sha256=campaign.sha(Path(campaign.__file__)),
                contract_sha256=campaign.sha(campaign.HERE/'CONTRACT.json'),binary_sha256='test-binary-not-GPU')
    campaign.save(work/'REGISTERED.json',record)
    good_guard=dict(runtime_valid=True,exit_code=0,stop_reason=None)
    campaign.save(guard/'receipt.json',good_guard);campaign.save(guard/'checks.json',[dict(foreign=[])])
    for name in ('before.json','after.json'):campaign.save(guard/name,dict(apps=''))
    for job in jobs:
        run=work/'runs'/job['label'];run.mkdir();prefix=work/'outputs'/job['label']
        receipt=dict(label=job['label'],exit_code=0,empty_before=True,empty_after=True,binary_sha256=record['binary_sha256'])
        campaign.save(run/'receipt.json',receipt)
        campaign.save(Path(str(prefix)+'.summary.json'),dict(trace_ms=1.,results=0))
        campaign.save(Path(str(prefix)+'.region.json'),dict(setup_plus_trace_ms=2.))
        campaign.save(Path(str(prefix)+'.scope.json'),dict(warmup_total_ms=3.))
        rows.append({**job,**receipt,'trace_ms':1.,'results':0,'setup_plus_trace_ms':2.,'warmup_ms':3.})
    campaign.save(work/'RAW_ROWS.json',rows);args=SimpleNamespace(work=work,executed_driver=None)
    original=campaign.verify_completed(args)
    def rejected():
        try:campaign.verify_completed(args)
        except (AssertionError,FileNotFoundError):return
        raise AssertionError('bad receipt/row was admitted')
    campaign.save(guard/'receipt.json',{**good_guard,'runtime_valid':False});rejected()
    campaign.save(guard/'receipt.json',good_guard);campaign.save(guard/'checks.json',[dict(foreign=['foreign'])]);rejected()
    campaign.save(guard/'checks.json',[dict(foreign=[])])
    rows[0]['trace_ms']=2.;campaign.save(work/'RAW_ROWS.json',rows);rejected()
    rows[0]['trace_ms']=1.;campaign.save(work/'RAW_ROWS.json',rows)
    assert campaign.verify_completed(args)==original
print('PASS failed GPU guard, foreign activity and altered raw row are rejected offline')
import snapshots
import numpy as np
for fields,squared in (([np.nan],[1.]),([1.],[np.nan]),([np.inf],[1.])):
    f,r,finite=snapshots.field_quality(np.asarray(fields),np.asarray(squared),np.array([1.]))
    assert not finite and not (f<=5e-5 and r<=5e-5)
assert snapshots.field_quality(np.array([1.]),np.array([1.]),np.array([1.]))==(0.,0.,True)
for n in (255,4096,1000000):
    initial,rebuilt=snapshots.snapshot_rows(n,campaign.recipe().short_operations(n))
    assert len(initial[2])==len(rebuilt[2])==32 and len(rebuilt[1])==n
    assert all(initial[1][q['physical_qid']]==q['original_row'] for q in initial[2])
    assert all(rebuilt[1][q['physical_qid']]==q['original_row'] for q in rebuilt[2])
print('PASS native NaN/Inf rejection and frozen snapshot coordinate/occurrence replay')
with tempfile.TemporaryDirectory(prefix='gts_phase_b_native_payload_test_') as tmp:
    prefix=Path(tmp)/'native'
    suffixes=('.ids.i32','.dist.f32','.native_squared.f32')
    for suffix in suffixes:Path(str(prefix)+suffix).write_bytes(bytes(1024))
    assert len(snapshots.native_outputs(prefix))==3
    for suffix in suffixes:
        path=Path(str(prefix)+suffix)
        for tail in (1,2,3):
            path.write_bytes(bytes(1024+tail))
            try:snapshots.native_outputs(prefix)
            except AssertionError:pass
            else:raise AssertionError('native malformed tail admitted')
        path.write_bytes(bytes(1024))
print('PASS native complete payload rejects all 1/2/3-byte malformed tails')
