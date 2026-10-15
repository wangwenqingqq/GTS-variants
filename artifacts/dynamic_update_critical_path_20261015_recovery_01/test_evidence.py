"""CPU-only evidence rejection tests;optional immutable real-trace mutation test."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import collections
from pathlib import Path
from unittest.mock import patch
import timeline
from curate import bind_ranges
from primary import test as scalar_test


def rejected(fn,*args):
    try:fn(*args)
    except AssertionError:return
    raise AssertionError('Invalid evidence admitted')


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path);a=p.parse_args()
    timeline.test();scalar_test();count=0
    for op,counts in timeline.EXPECTED_PHASES.items():
        timeline.check_phases(op,counts)
        for name in counts:
            missing=dict(counts);del missing[name];rejected(timeline.check_phases,op,missing)
            duplicate=dict(counts);duplicate[name]=2;rejected(timeline.check_phases,op,duplicate);count+=2
    rejected(timeline.check_phases,'Q',{'INSERT_OWNERS':1});count+=1
    valid={'cudaMemcpyAsync_v3020':1,'cudaStreamSynchronize_v3020':1}
    for names in ({'cudaMemcpyAsync_v3020':1},{**valid,'cudaStreamSynchronize_v3020':2},{**valid,'cudaLaunchKernel_v7000':1}):
        rejected(timeline.check_update_api,'I',names);count+=1
    timeline.check_update_api('D',{'cudaStreamSynchronize_v3020':1}) # legal delete-last:zero copies
    expected=dict(operator='D',copy_API_calls=1,sync_API_calls=1,H2D_activity_bytes=0,D2D_activity_bytes=3840)
    actual=dict(expected,index=0,other_copy_activity_bytes=0,kernels=0,launch_API_calls=0,other_API_calls=0)
    assert bind_ranges({'ranges':[actual]},[expected])==1
    for name in ('operator','copy_API_calls','sync_API_calls','H2D_activity_bytes','D2D_activity_bytes','kernels'):
        bad=dict(actual);bad[name]='I' if name=='operator' else actual[name]+1
        rejected(bind_ranges,{'ranges':[bad]},[expected]);count+=1
    rejected(bind_ranges,{'ranges':[]},[expected]);count+=1
    if a.trace:
        baseline=timeline.parse(a.trace);assert set(baseline['operators'])=={'I'}
        original=timeline.records
        def altered(mode):
            def read(db,table):
                rows=original(db,table)
                if table!='NVTX_EVENTS':return rows
                strings={r['id']:r['value'] for r in original(db,'StringIds')}
                selected=[r for r in rows if (strings.get(r.get('textId')) or r.get('text'))=='INSERT_OWNERS']
                assert selected
                return [r for r in rows if r is not selected[0]] if mode=='missing' else rows+[selected[0]]
            return read
        for mode in ('missing','duplicate'):
            with patch.object(timeline,'records',altered(mode)):rejected(timeline.parse,a.trace)
            count+=1
    print(f'PASS:{count} negative phase/API/per-ACK tests;real trace tested={bool(a.trace)};0 GPU starts')


if __name__=='__main__':main()
