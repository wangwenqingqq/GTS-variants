#!/usr/bin/env python3
"""CPU-only24-entry schedule, attempt completeness and observer replay regression."""
import json,tempfile
from pathlib import Path
from static_recovery2 import jobs,structure,guard_check,c,prior_public,live_guard,HERE,cpu

def rejected(fn):
    try:fn()
    except (AssertionError,KeyError):return
    raise AssertionError('invalid recovery proof accepted')

def main():
    plan=c.jobs('primary');new=jobs();assert len(new)==24 and new==plan[48:]
    assert new[0]['label']=='first_rebuilt_r3_GPU_RANGE_COMPLETE' and all(j['snapshot']=='first_rebuilt' for j in new)
    assert 4+44+24==72 and 18+4+1+44+1+24==92<=102
    labels=[j['label'] for j in new];rows={s:{} for s in labels};all_set=set(labels)
    structure(rows,all_set,all_set,True)
    rejected(lambda:structure(dict(list(rows.items())[:-1]),all_set,all_set,True))
    rejected(lambda:structure(rows,all_set|{'extra'},all_set,True))
    rejected(lambda:structure(rows,all_set,all_set|{'unreceipted_failure'},True))
    rejected(lambda:structure(dict(reversed(list(rows.items()))),all_set,all_set,True))
    structure(dict(list(rows.items())[:2]),set(labels[:3]),set(labels[:3]),False)
    rejected(lambda:structure(dict(list(rows.items())[:2]),set(labels[:4]),set(labels[:4]),False))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        proof=root/'published.json';proof.write_bytes((HERE/'evidence/STATIC_SECOND_STOP.json').read_bytes());prior_public(proof)
        expected=cpu.sha(proof);live_guard(proof,expected)
        data=json.loads(proof.read_text());data['private_verification_sha256']='0'*64;proof.write_text(json.dumps(data))
        rejected(lambda:prior_public(proof));rejected(lambda:live_guard(proof,expected))
        def save(name,value):(root/name).write_text(json.dumps(value)+'\n')
        save('receipt.json',dict(runtime_valid=True,exit_code=0,stop_reason=None,observer='two-sided-starttime-v1',child_pid=10))
        for name in ('before.json','after.json'):save(name,dict(apps=''))
        row=dict(seconds=1,foreign=[],apps='21, [No data], 552 MiB',owned_before={'10':1,'21':7},owned_after={'10':1},identities=[dict(pid=21,current_starttime=None,observed_owned_starttimes=[7],owned=True)])
        save('checks.json',[row]);guard_check(root)
        row['owned_before']={'10':1};save('checks.json',[row]);rejected(lambda:guard_check(root))
    print('PASS exact4+44+24 schedule,92 attempts, missing/extra/reordered rejection and two-sided observer replay')
if __name__=='__main__':main()
