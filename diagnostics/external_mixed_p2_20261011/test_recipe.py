#!/usr/bin/env python3
"""CPU-only budget/order and Host-ready timer boundary regression checks."""
from pathlib import Path
from prepare import read
from run import jobs

def service_timer(s,m):
    trace=float(s['trace_ms']);release=float(s['final_drain_ms' if m=='P2' else 'release_ms'])
    assert 0<=release<trace
    return trace-release
if __name__=='__main__':
    c=read(Path(__file__).parent/'CONTRACT.json')
    assert len(jobs(c,'qualification'))==12 and len(jobs(c,'primary'))==12 and len(jobs(c,'diagnostic'))==2
    assert c['primary']['orders']==[['P2','E'],['E','P2']]*3
    assert len({x['label'] for x in jobs(c,'qualification')})==12
    assert sum(x['method']=='P2' for x in jobs(c,'primary'))==6
    assert [x['case'] for x in jobs(c,'qualification')].count('empty')==2
    assert service_timer({'trace_ms':10,'final_drain_ms':2},'P2')==8
    assert service_timer({'trace_ms':10,'release_ms':2},'E')==8
    try:service_timer({'trace_ms':1,'release_ms':2},'E')
    except AssertionError:pass
    else:raise AssertionError('Invalid subtraction admitted')
    print('PASS: 12+12+2 budget, paired order, empty edges, adjacent wall timer')
