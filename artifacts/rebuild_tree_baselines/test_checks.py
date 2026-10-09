#!/usr/bin/env python3
"""Small portable rejection checks for the complete-output and profiling contracts."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cpu import quality
from profile import parent
from qualify_cpu import check_receipt, check_rows
from verify_profile import bind_parent, sha


def main():
    sq=np.arange(16,dtype=np.float64);ids=np.arange(8,dtype=np.int32);fields=np.sqrt(sq[:8]).astype(np.float32)
    assert quality(ids,fields,sq[:8],sq,'knn',2)['passed']
    assert not quality(ids,np.full(8,np.nan),sq[:8],sq,'knn',2)['passed']
    assert not quality(np.r_[ids[:7],ids[0]],fields,sq[:8],sq,'knn',2)['passed']
    assert not quality(np.r_[ids[:7],-1],fields,sq[:8],sq,'knn',2)['passed']
    assert quality(np.arange(5,dtype=np.int32),np.sqrt(sq[:5]).astype(np.float32),sq[:5],sq,'range',2)['passed']
    assert not quality(np.arange(4,dtype=np.int32),np.sqrt(sq[:4]).astype(np.float32),sq[:4],sq,'range',2)['passed']
    assert not quality(np.arange(6,dtype=np.int32),np.sqrt(sq[:6]).astype(np.float32),sq[:6],sq,'range',2)['passed']
    tied=sq.copy();tied[7:9]=7
    tied_ids=np.r_[np.arange(7),8].astype(np.int32)
    assert quality(tied_ids,np.sqrt(tied[tied_ids]).astype(np.float32),tied[tied_ids],tied,'knn',2)['passed']
    ops=parent.short_operations(1000000)[:51]
    registered=(HERE/'REBUILD_PREFIX.txt').read_text()
    assert registered=='51\n'+''.join(f'{f} {i}\n' for f,i in ops)
    assert ops[48][0]==0 and {ops[49][0],ops[50][0]}=={2,3}
    assert sum(f==0 for f,_ in ops)==sum(f==1 for f,_ in ops)==10
    contract=json.loads((HERE/'CONTRACT.json').read_text())
    assert len(contract['baseline_diagnostic']['job_order'])==6
    assert contract['profile']['maximum_new_nsys']==2 and contract['caps']['original_phase_B_primary_reruns']==0
    def rejects(fn, *args):
        try: fn(*args)
        except AssertionError: return
        raise AssertionError('malformed evidence was admitted')
    spec=dict(N=1000000,queries=[dict(physical_qid=i*2) for i in range(32)])
    rows=[dict(task='knn' if i<32 else 'range',query=i%32,qid=(i%32)*2,
               count=8,offset=8*i,ack_ms=1.) for i in range(64)]
    assert check_rows(rows,spec)==512
    altered=[dict(r) for r in rows];altered[0]['qid']=3
    rejects(check_rows,altered,spec)
    altered=[dict(r) for r in rows];altered[-1]['offset']=0
    rejects(check_rows,altered,spec)
    rejects(check_rows,rows[:-1],spec)
    receipt=dict(exit_code=0,runtime_valid=True,timed_out=False,wall_s=1.,
                 script_sha256='source',registration_sha256='registration',output_hashes={'answer':'hash'})
    check_receipt(receipt,'source','registration',{'answer':'hash'})
    rejects(check_receipt,{**receipt,'exit_code':124},'source','registration',{'answer':'hash'})
    rejects(check_receipt,receipt,'source','registration',{'answer':'changed'})
    rejects(check_receipt,receipt,'changed','registration',{'answer':'hash'})
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'outputs').mkdir();prefix='outputs/round_1_A'
        suffixes=('.queries.csv','.ids.i32','.dist.f32','.ops.csv','.warmup.queries.csv','.warmup.ids.i32','.warmup.dist.f32')
        for suffix in suffixes:(root/(prefix+suffix)).write_bytes(b'original')
        hashes={prefix+s:sha(root/(prefix+s)) for s in suffixes}
        proof=dict(passed=True,ordered_full_outputs=True,evidence_binding=dict(output_hashes=hashes))
        bind_parent(root,proof,'A')
        # Even matching corruption of fresh+parent cannot replace the admitted parent.
        (root/(prefix+'.dist.f32')).write_bytes(b'matching polluted fresh and parent')
        rejects(bind_parent,root,proof,'A')
    print('PASS complete range/ties/invalid/duplicate/nonfinite gates and exact one-rebuild prefix')


if __name__=='__main__':main()
