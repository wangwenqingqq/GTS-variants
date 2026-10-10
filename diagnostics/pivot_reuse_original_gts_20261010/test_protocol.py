#!/usr/bin/env python3
"""Small CPU regression: exact baseline, unchanged bound/math, fail-closed pins."""
import argparse
import json
from pathlib import Path
import tempfile
import shutil
from prepare import prepare,kernel
from audit_index import audit,warp_screen
from run import runtime_errors
from locked import snapshot
from analyze import paired
from boundary import add_ties
import subprocess
from unittest.mock import patch

def main(source,index):
    local=Path(__file__).resolve().parent/'local';local.mkdir(exist_ok=True)
    orders=[['G0','G1'],['G1','G0'],['G1','G0'],['G0','G1'],['G1','G0'],['G0','G1']]
    assert paired([2.]*6,[1.]*6,orders)['decision']=='confirmed_win'
    assert paired([1.]*6,[2.]*6,orders)['decision']=='confirmed_regression'
    assert paired([1.]*6,[1.]*6,orders)['decision']=='inconclusive'
    for distances in ([float(i) for i in range(40)],[0.]*9+list(map(float,range(1,32))),[0.]*40,[0.]*30+[1.]*10):
        record={'ids':list(range(32)),'squared':distances[:32],
                'ties':{'32':{'boundary_ids':[i for i,d in enumerate(distances) if d==distances[31]]}}}
        reference=add_ties({'records':[record]},[1,2,7,8,9,31,32])
        for k in (1,2,7,8,9,31,32):
            tie=reference['records'][0]['ties'][str(k)]
            assert tie['strictly_closer_ids']==[i for i,d in enumerate(distances) if d<distances[k-1]]
            assert tie['boundary_ids']==[i for i,d in enumerate(distances) if d==distances[k-1]]
    assert not runtime_errors('========= ERROR SUMMARY: 0 errors\nRACECHECK SUMMARY: 0 hazards\nPASS')
    assert runtime_errors('getDisPQ error: invalid argument') and runtime_errors('FAIL: bad cache')
    with patch('locked.subprocess.check_output',side_effect=subprocess.TimeoutExpired('nvidia-smi',10)):
        try:snapshot('GPU-test')
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('unbounded telemetry admitted')
    with tempfile.TemporaryDirectory(dir=local) as name:
        root=Path(name);out=root/'generated';pins=prepare(source,out)
        original=(out/'shared/adapted/include/search_v2.cuh').read_text()
        assert (out/'G0/include/search_v2.cuh').read_text()==original
        reused=(out/'G1/include/search_v2.cuh').read_text()
        for func in ('nodeProcessKnn','updateDisK','labelCNode','mergeResKnn'):
            assert kernel(original,func)[2]==kernel(reused,func)[2],func
        for accumulator in ('dis_q','result'):
            pattern=f'{accumulator} += pow('
            assert original.count(pattern)==reused.count(pattern)
        assert 'pr_begin();' in reused and 'pr_end();' in reused
        assert 'if(qnum!=1)' in reused
        assert 'batch==1' in (out/'bench.cu').read_text() and 'batch==32' not in (out/'bench.cu').read_text()
        assert 'if(pr_valid[slot])' in reused and 'if(hit)' in reused
        assert 'pr_bridge' not in (out/'G0/include/search_v2.cuh').read_text()
        assert 'pr_bridge' in (out/'G1_count/include/search_v2.cuh').read_text()
        changed=root/'source';shutil.copytree(out/'shared/original',changed)
        p=changed/'include/tree.cuh';p.write_text(p.read_text()+'\n// drift\n')
        try:prepare(changed,root/'must_fail')
        except AssertionError:pass
        else:raise AssertionError('source drift admitted')
    x=audit(index)
    assert x['N']==1000000 and x['D']==960 and x['evaluated_pivot_groups_if_all_live']==11100
    assert x['unique_evaluated_objects']==11099 and all(r['same_level_aliases']==0 for r in x['levels'])
    screen=warp_screen(index)
    assert screen['leaf_sizes']=={10:100000} and screen['max_evaluated_pivots_in_one_leaf']==2
    assert screen['leaves_with_at_most_one_nonpivot']==0
    print('PASS exact G0, unchanged G1 decisions/math, source-drift rejection, fixed index partition/alias screen')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('index',type=Path)
    a=p.parse_args();main(a.source,a.index)
