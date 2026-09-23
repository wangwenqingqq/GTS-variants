#!/usr/bin/env python3
"""Check retained estimator and native-wait parsing using small known cases."""
from pathlib import Path
import tempfile
import analyze
p=analyze.paired([4,8,12,16,20,24],[2,4,6,8,10,12]);assert p['paired_geomean_A_over_B']==2 and p['ci95']==[2,2] and p['B_process_wins']==6
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'stdout.log';f.write_text('policy,D,8\npruning,0\nsample,0,0.1,0.09,0.095\nstage,0,stage.leaf_distance,1,0.08,0.07\nbatch,64,1,0.9,0.95\n');o,s,b,flags=analyze.observations(f);assert o[0]==[.1,.09,.095] and b==[1,.9,.95] and flags==8
 f.write_text('policy,D,4\n')
 try:analyze.observations(f);raise RuntimeError('changed wait policy accepted')
 except AssertionError:pass
print('PASS: paired estimator and unchanged wait contract')
