#!/usr/bin/env python3
"""Cheap adversarial checks for output identity and node-slot geometry."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import numpy as np
import verify


def rejected(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('mutation was accepted')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for mode in ('B0','B1'):
            folder=root/'audit'/('sample_'+mode)/'build0';folder.mkdir(parents=True)
            def write(name,x): (folder/name).write_bytes(np.asarray(x).tobytes())
            (folder/'META.json').write_text(json.dumps(dict(n=20,d=128,nn=111,mode=mode)))
            geometry=dict(slots=1,start=0,upper=20,tiles=1,grid=1,threads=512)
            (folder/'level0.GEOMETRY.json').write_text(json.dumps(geometry))
            (folder/'level0.DISTANCE_DIAGNOSTIC.json').write_text(json.dumps(dict(launch_through_existing_fence_ms=1)))
            dtype=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('leaf','<i4')])
            nodes=np.zeros(111,dtype=dtype);nodes[0]=(0,0.,20,0,1)
            write('level0.input.nodes',nodes);write('level0.after_split.nodes',nodes)
            empty=np.ones(111,dtype='<i4');empty[0]=0
            for key in ('input.empty','after_split.empty','refit.empty'):write('level0.'+key if not key.startswith('refit') else key,empty)
            for key in ('input.split','after_split.split','distance.pids'):write('level0.'+key,np.zeros(111,dtype='<i4'))
            for key in ('refit.lo','refit.hi'):write(key,np.zeros(111,dtype='<f8'))
            write('level0.input.order',np.arange(20,dtype='<i4'));write('level0.distance.keys',np.zeros(20,dtype='<f8'))
            write('level0.sorted.keys',np.zeros(20,dtype='<f8'));write('level0.sorted.order',np.arange(20,dtype='<i4'))
        assert verify.layer_identity(root,'sample',[20])['all_defined_state_bitwise_identical']
        other=root/'audit/sample_B1/build0';p=other/'level0.distance.keys';original=p.read_bytes()
        p.write_bytes(b'\x01'+original[1:]);rejected(lambda:verify.layer_identity(root,'sample',[20]));p.write_bytes(original)
        p=other/'level0.GEOMETRY.json';original=p.read_text();wrong=json.loads(original);wrong['grid']=2
        p.write_text(json.dumps(wrong));rejected(lambda:verify.layer_identity(root,'sample',[20]));p.write_text(original)
        names=[root/'audit'/('sample_'+mode)/'build0/refit.hi' for mode in ('B0','B1')]
        backup=[p.read_bytes() for p in names]
        for p in names:p.unlink()
        rejected(lambda:verify.layer_identity(root,'sample',[20]))
        for p,value in zip(names,backup):p.write_bytes(value)
        for mode in ('B0','B1'):
            prefix=root/mode
            Path(str(prefix)+'.queries.csv').write_text('step,qid,tree_size,buffer,count,offset\n0,0,20,0,1,0\n')
            Path(str(prefix)+'.ops.csv').write_text('step,flag,base_before,buffer_before,base_after,buffer_after\n0,2,20,0,20,0\n')
            for s,value in (('.ids.i32',np.zeros(1,dtype='<i4').tobytes()),('.dist.f32',np.zeros(1,dtype='<f4').tobytes())):
                Path(str(prefix)+s).write_bytes(value);Path(str(prefix)+'.warmup'+s).write_bytes(value)
            Path(str(prefix)+'.warmup.queries.csv').write_text('complete warmup identity')
        assert verify.same_answers(root/'B0',root/'B1',1)['complete_ordered_byte_identity']
        p=root/'B1.ids.i32';p.write_bytes(p.read_bytes()+b'\x00');rejected(lambda:verify.same_answers(root/'B0',root/'B1',1))
    contract=verify.CONTRACT
    rejected(lambda:verify.bind_admission(SimpleNamespace(admission=None),{'admission_sha256':'0'*64}))
    with tempfile.TemporaryDirectory() as tmp:
        proof=Path(tmp)/'QUALIFICATION.json';proof.write_text('{"passed":true}')
        rejected(lambda:verify.bind_admission(SimpleNamespace(admission=proof),{'admission_sha256':'0'*64}))
    jobs=verify.campaign.jobs('primary')
    assert len(jobs)==12 and [r['mode'] for r in jobs]==[m for order in contract['primary']['orders'] for m in (('B0','B1') if order=='B0B1' else ('B1','B0'))]
    print('PASS complete payload/tail-byte, geometry/key mutation rejection and exact balanced12-job order')


if __name__=='__main__':main()
