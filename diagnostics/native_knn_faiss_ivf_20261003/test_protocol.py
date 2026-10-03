#!/usr/bin/env python3
"""Small stdlib regression checks for pinned preparation and query isolation."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import analyze
import subprocess
import sys
import run_locked
from contextlib import ExitStack

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare_gts',ROOT/'prepare_gts.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)
assert prepare.once('abc','b','B')=='aBc'
try:prepare.once('bbb','b','B')
except AssertionError:pass
else:raise AssertionError('Repeated patch anchors must fail')
contract=json.loads((ROOT/'CONTRACT.json').read_text())
assert all(k<=32 for k in contract['K'])
assert contract['timing']['formal_pairs']==6
queries=json.loads((ROOT/'QUERY_SETS.json').read_text())
for dataset in ('GIST','Deep'):
    values=list(map(int,(ROOT/queries[dataset]['development_file']).read_text().split()))
    assert values[0]==128 and len(set(values[1:]))==128
    if queries[dataset]['final_status']=='frozen_after_development':
        final=list(map(int,(ROOT/queries[dataset]['final_file']).read_text().split()))
        assert final[0]==256 and len(set(final[1:]))==256
        assert not set(final[1:])&set(values[1:])
# A second descriptor to the same inode does self-contend. Deduplication is
# needed, while another lock owner must still prevent benchmark admission.
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'canonical';p.touch();alias=Path(tmp)/'alias';os.link(p,alias)
    assert (p.stat().st_dev,p.stat().st_ino)==(alias.stat().st_dev,alias.stat().st_ino)
    with p.open('r') as first,alias.open('r') as second:
        fcntl.flock(first,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:fcntl.flock(second,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise AssertionError('Lock contention must remain fail-closed')
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'new_canonical';q=Path(tmp)/'new_secondary'
    with ExitStack() as stack:
        run_locked.acquire_locks(stack,[p,q,p,q])
        assert p.exists() and q.exists()
        try:
            with ExitStack() as other:run_locked.acquire_locks(other,[p,q,p,q])
        except BlockingIOError:pass
        else:raise AssertionError('Another owner must remain blocked')
assert analyze.percentile([1,3],.5)==2
ratio=analyze.ratio_stats([10]*6,[2]*6)
assert abs(ratio['geomean_ratio']-5)<1e-12
assert ratio['process_wins_ivf']==6
assert all(abs(x-5)<1e-12 for x in ratio['bootstrap_95'])
independent=analyze.ratio_stats([10]*6,[2]*6,paired=False)
assert 'process_wins_ivf' not in independent and 'independent' in independent['method']
owned=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
try:
    run_locked.stop_owned(owned)
    assert owned.poll() is not None and unrelated.poll() is None
finally:
    run_locked.stop_owned(owned);run_locked.stop_owned(unrelated)
print('PASS protocol guards, fixed contract, unique/disjoint qids, lock aliases, paired/independent statistics')
