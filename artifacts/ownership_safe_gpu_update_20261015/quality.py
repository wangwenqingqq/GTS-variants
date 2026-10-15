"""Full inherited query/ownership oracle plus actual execution and capacity proofs."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import json,math
from pathlib import Path
from common import HERE,BASE,load,sha,module
from logical_quality import table
import postcheck

def check(prefix,job,w,reg):
    prefix=Path(prefix);stem=str(prefix)
    if job['kind']=='shape':
        meta=load(stem+'.meta.json');assert meta['passed'] and meta['every_capacity_bit_compared'] and meta['N']==4096 and meta['B']==512
        rows=table(stem+'.shape.csv');assert len(rows)==64
        assert [(int(r['D']),int(r['iteration'])) for r in rows]==[(d,i) for d in (128,960) for i in range(32)]
        assert all(math.isfinite(float(r['ACK_ms'])) and float(r['ACK_ms'])>0 for r in rows)
        assert all(0<=int(r['compiled_rows'])<=int(r['native_moves'])<=512 for r in rows)
        if job['update']!='FINAL':assert all(int(r['compiled_rows'])==0 for r in rows)
        return dict(passed=True,kind='shape',metadata=meta,samples=rows,raw_outputs=outputs(prefix))
    if job['update'] in ('CURRENT','S1'):
        legacy=module('immutable_attribution_quality',BASE/'quality.py');out=legacy.check(prefix,job,w,reg)
        out['raw_outputs']=outputs(prefix);return out
    out=module('inherited_logical_quality',HERE/'logical_quality.py').check(prefix,job,w,reg)
    capacity=load(stem+'.capacity.json');assert capacity['passed'] and capacity['includes_retired_rows'] and capacity['all_allocated_vector_bytes_compared']==job['N']*3840
    rows=table(stem+'.physical.csv');native=table(stem+'.ops.csv');native=[r for r in native if int(r['kind'])<2]
    assert len(rows)==len(native)
    for row,old in zip(rows,native):
        r={k:int(v) for k,v in row.items()};assert r['kind']==int(old['kind']) and r['rows']==int(old['rows']) and r['syncs']==1
        if r['kind']==1:assert r['H2D_vector_bytes']==r['rows']*3840 and r['copy_APIs']==1 and r['D2D_bytes']==r['launches']==r['H2D_plan_bytes']==0
        elif job['update']=='NATIVE' or r['rows']==1:
            assert r['copy_APIs']==r['reference_moves'] and r['D2D_bytes']==r['reference_moves']*3840 and r['launches']==r['H2D_plan_bytes']==0
        elif job['update']=='WAVES':
            assert r['copy_APIs']==r['levels'] and r['D2D_bytes']==r['reference_moves']*3840 and r['launches']==r['H2D_plan_bytes']==0
        else:
            assert r['compiled_rows']<=r['reference_moves']
            assert r['copy_APIs']==int(r['compiled_rows']>0) and r['launches']==int(r['compiled_rows']>1)
            assert r['H2D_plan_bytes']==(r['compiled_rows']*8 if r['compiled_rows']>1 else 0)
            assert r['D2D_bytes']==(3840 if r['compiled_rows']==1 else 0)
            assert r['kernel_payload_bytes']==(r['compiled_rows']*3840 if r['compiled_rows']>1 else 0)
    postcheck.check(prefix,job)
    proof=None
    if job['diagnostic']==2:
        proof=load(stem+'.ack_oracle.json');assert proof['passed'] and proof['changed_rows_checked']>0
        assert proof['ACK_callbacks']==len(rows)+int(job.get("kind")=="micro")
    out.update(strict_capacity=capacity,per_ACK_oracle=proof,physical_operators=rows,raw_outputs=outputs(prefix));return out

def outputs(prefix):return {p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()}
