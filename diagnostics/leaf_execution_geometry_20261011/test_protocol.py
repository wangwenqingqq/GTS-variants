#!/usr/bin/env python3
"""CPU guard: observation-only patch, source pins, and structural packing arithmetic."""
import argparse,re,tempfile,json,struct
from pathlib import Path
from prepare import prepare,sha
from analyze import pack,ROW,analyze
p=argparse.ArgumentParser();p.add_argument('source',type=Path);a=p.parse_args()
assert ROW.size==40
assert pack([10]*6,2)==3 and pack([10]*6,3)==2 and pack([10]*6,32)==2
assert pack([20,20,10],3)==2 and pack([1]*33,32)==2
assert pack([10]*7,3)==3 and pack([],3)==0
local=Path(__file__).resolve().parent/'local';local.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=local) as tmp:
    out=Path(tmp)/'generated';pins=prepare(a.source,out)
    old=(out/'shared/adapted/include/search_v2.cuh').read_text()
    new=(out/'count/include/search_v2.cuh').read_text()
    assert re.sub(r'\n// LG_BEGIN\n.*?\n// LG_END','',new,flags=re.S)==old
    assert new.count('// LG_BEGIN')==6
    for path,digest in pins['files'].items():assert sha(out/path)==digest
with tempfile.TemporaryDirectory(dir=local) as tmp:
    root=Path(tmp);index=root/'index';geometry=root/'geometry';result=root/'result';oracle=root/'oracle'
    nodes=[(0,0.,4,0,0),(0,0.,2,0,1),(2,1.,2,2,1)]
    index.write_bytes(struct.pack('<4i',4,96,3,3)+struct.pack('<4i',0,1,2,3)+b''.join(struct.pack('<ifiii',*x) for x in nodes)+bytes(12))
    record=[(0.,0.,0.,0,0,0,0,0,0,0),(0.,2.,2.,1,1,1,3,2,3,0),(1.,2.,2.,1,1,1,3,3,0,1)]
    header=struct.pack('<4i',0x4c474531,4,96,3)+struct.pack('<iQQ',0,2,192)
    geometry.write_bytes(header+b''.join(ROW.pack(*x) for x in record))
    result.write_bytes(struct.pack('<5if',4,96,1,1,0,0.))
    oracle.write_text(json.dumps({'records':[{'qid':0,'ties':{'1':{'strictly_closer_ids':[],'boundary_ids':[0]}}}]}))
    x=analyze(index,geometry,result,oracle)
    assert x['totals']['distance_objects']==3 and x['totals']['no_returned_topk_leaves']==1
    assert x['totals']['online_existing_bound_prunable']==0 and x['totals']['retrospective_lower_above_final_kth']==1
    record[1]=(*record[1][:6],1,*record[1][7:])
    geometry.write_bytes(header+b''.join(ROW.pack(*x) for x in record))
    try:analyze(index,geometry,result,oracle)
    except AssertionError:pass
    else:raise AssertionError('corrupted mask admitted')
print('PASS removable sidecar, unchanged search, pins, packing, parser and corrupt-mask rejection')
