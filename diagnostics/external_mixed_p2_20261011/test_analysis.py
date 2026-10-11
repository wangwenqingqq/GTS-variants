#!/usr/bin/env python3
"""CPU-only published evidence consistency and lower-is-better ratio regression."""
from pathlib import Path
import math
from prepare import read
from analyze import ratio
r=Path(__file__).parent;c=read(r/'CONTRACT.json');j=read(r/'evidence/SUMMARY.json')
for a,b,w,d in ((2.,1.,0,'P2_slower'),(1.,2.,6,'P2_faster'),(1.,1.,0,'inconclusive')):
    got=ratio([a]*6,[b]*6,c);assert got['paired_geometric_ratio']==a/b and got['P2_process_wins']==w and got['decision']==d
values={m:[x['service_ms'] for x in j['rows'] if x['method']==m] for m in ('P2','E')}
assert ratio(values['P2'],values['E'],c)==j['primary_ratio']
assert [x['method'] for x in j['rows']]==[m for order in c['primary']['orders'] for m in order]
assert len({(x['round'],x['method']) for x in j['rows']})==12
for row in j['rows']:
    assert math.isclose(row['service_ms']+row['final_state_release_ms'],row['trace_plus_release_ms'],rel_tol=1e-12)
    assert math.isclose(sum(row['flag'+str(f)+'_ack_ms'] for f in range(4))+row['between_ACK_residual_ms'],row['service_ms'],rel_tol=1e-12)
assert len({x['logical_final_set_sha256'] for m in ('P2','E') for x in j['payloads'][m]})==1
lc=read(r/'evidence/LOCAL_CLOSURE.json');assert lc['passed'] and len(lc['rows'])==26 and lc['qualified_payload_files']==156
assert {x['label'] for x in lc['rows'] if x['phase']=='qualification'}==set(c['qualification']['order'])
assert all(x['main_final_live']==1 for x in lc['rows'] if x['case']=='empty')
p=read(r/'evidence/PROFILE.json')
for m in ('P2','E'):
    assert len(p[m]['client_D2H']['per_query'])==256
    for a,b in [('bytes','client_D2H_bytes'),('device_ms','client_D2H_device_ms'),('API_inclusive_ms','client_D2H_API_inclusive_ms')]:
        assert math.isclose(p[m]['client_D2H'][a],sum(x[b] for x in p[m]['client_D2H']['per_query']),rel_tol=1e-12)
print('PASS: ratio direction/statistics, all12 samples, accounting, final state, empty qualification, output ledger')
