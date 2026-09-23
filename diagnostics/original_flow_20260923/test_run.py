#!/usr/bin/env python3
"""CPU-only regression checks for repeated-query validation and drift rejection."""
from pathlib import Path
import tempfile
from run import validate

with tempfile.TemporaryDirectory() as tmp:
    cost=Path(tmp)/'cost.txt'
    target={'range_counts':list(range(32)),'knn_kth':[4]*32}
    cost.write_text('Result num: \n'+' '.join(map(str,target['range_counts']*128))+'\n')
    assert validate(cost,target,'update',128)['pass']
    assert not validate(cost,target,'update',1)['pass']
    cost.write_text('Result radius: \n'+' '.join(['4']*32)+'\n')
    assert validate(cost,target,'knn',1)['pass']
    cost.write_text('Result num: \n')
    assert not validate(cost,target,'range',1)['pass']
print('PASS: repeated native results, count mismatch and missing-result rejection; no GPU calls')
from analyze import union,length,quantiles,admitted
assert union([(0,3),(2,4),(7,9),(9,10),(4,4)])==[(0,4),(7,10)]
assert length([(0,3),(2,4)])==4
assert quantiles([1,2,3])['median']==2
print('PASS: overlapping GPU intervals are not double-counted; gap and quantile primitives')
accepted={'exit_code':0,'stop_reason':None,'validation':{'pass':True},'post_gpu_clear':True}
assert admitted(accepted)
for rejected in ({'exit_code':1},{'stop_reason':'monitor stop'},
                 {'validation':{'pass':False}},{'post_gpu_clear':False},
                 {'runtime_errors':['CUDA error']}):
    assert not admitted(accepted | rejected)
print('PASS: failed, stopped, invalid and unsafe receipts excluded from summaries')
from analyze_async import overlap,category
assert overlap([(0,4),(2,6),(8,10)],[(1,3),(5,9)])==4
assert overlap([],[(1,3)])==0
assert overlap([(0,2)],[(2,4)])==0
assert category('cudaDeviceSynchronize_v3020')=='synchronize'
assert category('cudaMallocManaged_v6000')=='allocation_free'
print('PASS: gap/API intersections merge overlaps and preserve touching boundaries')

# Optional release check against the separately supplied original sources/data.
import hashlib
import json
import sys
from prepare import prepare
if len(sys.argv)==3:
    with tempfile.TemporaryDirectory() as tmp:
        source,fixtures=map(Path,sys.argv[1:]);out=Path(tmp)/'copy'
        prepare(source,fixtures,out)
        pins=json.loads((out/'source_pins.json').read_text())
        assert len(pins)==8
        for name,digest in pins.items():
            assert hashlib.sha256((out/'source'/name.removeprefix('GTS/')).read_bytes()).hexdigest()==digest
        assert len((out/'fixtures/words_2000_long.qid').read_text().splitlines())==4097
        evidence=json.loads((Path(__file__).parent/'EVIDENCE.json').read_text())
        expected={name:digest for r in evidence['receipts'] for name,digest in r['input_sha256'].items()}
        assert all(hashlib.sha256((out/'fixtures'/name).read_bytes()).hexdigest()==digest for name,digest in expected.items())
        try:prepare(source,fixtures,out)
        except FileExistsError:pass
        else:raise AssertionError('Existing output overwritten')
    print('PASS: exact original source copy, repeated queries, existing output preserved')
