#!/usr/bin/env python3
"""Small checks for immutable schedules, pairing, and late checker-path recovery."""
import tempfile,copy,json
from pathlib import Path
import numpy as np
import rtp
from rtp_results import paired

def main():
    orders=rtp.CONTRACT['orders'];assert len(set(orders))==6
    assert len(rtp.jobs('bridge'))==5 and len(rtp.jobs('primary'))==18
    for l,r in ('RP','TP','RT'):assert sum(o.index(l)<o.index(r) for o in orders)==3
    for ratio in (2.,.5,1.):
        x=paired([ratio]*6,[1.]*6,orders,'R','P')
        assert x['ratio']==ratio and x['CI95']==[ratio,ratio]
        assert x['confirmed_speedup']==(ratio>1)
    # Favorable overall time cannot rescue a losing order stratum.
    values=[1.5 if o.index('T')<o.index('P') else .9 for o in orders]
    x=paired(values,[1.]*6,orders,'T','P');assert not x['confirmed_speedup']
    for malformed in ([1]*5,[0]*6,[float('nan')]*6):
        try:paired(malformed,[1.]*6,orders,'R','P')
        except AssertionError:pass
        else:raise AssertionError('invalid timing admitted')
    def rejects(fn):
        try:fn()
        except AssertionError:return
        raise AssertionError('malformed evidence admitted')
    summary=dict(observe=True,results=1,trace_ms=10.,final_drain_ms=1.,cpu_user_s=1.,stages=[dict(inclusive_host_ms=2.,calls=1)])
    ops=[dict(ack_ms=6.,rebuild_ms=2.)];queries=[dict(count=1)]
    rtp.timing_gate(summary,dict(setup_ms=1.),dict(warmup_total_ms=1.),ops,queries)
    for key,value in (('observe',False),('results',2),('trace_ms',float('nan')),('cpu_user_s',-1.)):
        bad={**summary,key:value};rejects(lambda:rtp.timing_gate(bad,{}, {},ops,queries))
    for value in (-1.,float('nan'),float('inf')):
        rejects(lambda:rtp.timing_gate(summary,{}, {},[dict(ack_ms=value,rebuild_ms=0.)],queries))
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);(root/'guards'/'first').mkdir(parents=True);(root/'outputs').mkdir()
        (root/'guards/first/receipt.json').write_text(json.dumps(dict(runtime_valid=True,exit_code=0,stop_reason=None)))
        (root/'first.command.json').write_text('{}');(root/'outputs/first.ids.i32').write_bytes(b'')
        record=dict(jobs=[dict(label='first')],numa_node=1,gpu='test',script_sha256='original',registered_unix=1)
        current={**record,'script_sha256':'corrected','registered_unix':2};rtp.check_resume(record,current,root)
        rejects(lambda:rtp.check_resume(record,{**current,'numa_node':2},root))
        (root/'guards/second').mkdir();rejects(lambda:rtp.check_resume(record,current,root))
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'receipt.json' ;p.write_text('{"passed":true}')
        assert rtp.read(p)==rtp.read(str(p))==dict(passed=True)
    print('PASS six balanced permutations, paired scope, order-stratum gate and Path/string receipts')
if __name__=='__main__':main()
