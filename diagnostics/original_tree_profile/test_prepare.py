#!/usr/bin/env python3
"""Small runnable check for pinned preparation and untouched kernel bodies."""
from pathlib import Path
import sys
import tempfile
from prepare import prepare
from make_fixture import distance

source=Path(sys.argv[1]);here=Path(__file__).resolve().parent
(here/'work').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=here/'work') as tmp:
    out=Path(tmp)/'copy';manifest=prepare(source,out)
    assert len(manifest)==20
    for variant in ['GTS','GPU-Tree']:
        for p in (out/variant/'include').glob('*.cuh'):
            orig=(source/variant/'include'/p.name).read_text();actual=p.read_text()
            assert actual.count('cudaDeviceSynchronize()')==orig.count('cudaDeviceSynchronize()')
            assert actual.count('<<<')==orig.count('<<<')
        main=(out/variant/'src/main.cu').read_text()
        assert main.index('GtsDiagDump gts_diag_dump')<main.index('runtime.init')
    assert (out/'GTS/include/search_v2.cuh').read_text().count('256ULL * 1024 * 1024')==2
    assert 'srand(0)' in (out/'GPU-Tree/include/pivot.cuh').read_text()
    try: prepare(source,out)
    except FileExistsError: pass
    else: raise AssertionError('Overwrite was allowed')
assert distance(b'kitten',b'sitting')==3 and distance(b'',b'')==0
print('PASS: pinned copies, no extra synchronizations/launches, bounded workspace, fixed seed, no overwrite, CPU oracle checks')
from run import parse, validate
assert parse('GTS_DIAG,query.range,1,0.025,0.02')['query.range']['main_thread_cpu_s']==0.02
with tempfile.TemporaryDirectory(dir=here/'work') as tmp:
    cost=Path(tmp)/'cost.txt';cost.write_text('Range search radius: 4\nResult num: \n'+' '.join(['5']*32)+'\nSearch time: 0.1\n')
    expected={'range_counts':[5]*32,'knn_kth':[3]*32}
    assert validate('gts','range','',cost,expected)['pass']
    stdout='\n'.join(f'GTS_AUDIT_RESULT,range,{i},5' for i in range(32))
    assert validate('gputree','range',stdout,cost,expected)['pass']
    assert not validate('gts','knn','',cost,expected)['pass']
print('PASS: phase parsing, native and exported output validation, mismatch rejection')
