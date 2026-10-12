"""CPU-only verification of the curated publication tree and scalar decision."""
import hashlib
import json
from pathlib import Path
import numpy as np
from analyze import fit, distribution
from campaign import jobs

ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    manifest=read(ROOT/'PUBLIC_MANIFEST.json')
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLIC_MANIFEST.json'}
    assert actual==set(manifest['files'])
    for name,h in manifest['files'].items():assert sha(ROOT/name)==h,name
    c=read(ROOT/'CONTRACT.json');inputs=read(ROOT/'evidence/INPUT_IDENTITY.json')
    assert inputs['contract_sha256']==sha(ROOT/'CONTRACT.json')
    for name,h in inputs['frozen_measurement_sources'].items():assert sha(ROOT.parent/name)==h,name
    closure=read(ROOT/'evidence/EXECUTION_CLOSURE.json')
    assert closure['passed'] and closure['top_level_starts']==75 and closure['GPU_failures']==0
    samples=read(ROOT/'timing/PROCESS_SAMPLES.json');receipts=read(ROOT/'evidence/QUALITY_RECEIPTS.json')
    expected=[(s,j['label'],j['B'],j['N']) for s in ('qualification','keeper','primary','ncu') for j in jobs(s)]
    assert [(v['stage'],v['label'],v['B'],v['N']) for v in samples]==expected
    assert [(v['stage'],v['label']) for v in receipts]==[(s,l) for s,l,_,_ in expected]
    assert all(v['passed'] and v['all_complete_members'] and v['max_native_scale_error']<=5e-5 for v in receipts)
    assert all(len(v['measured_invocation_ms'])==32 and np.isclose(np.mean(v['measured_invocation_ms']),v['mean_invocation_ms'],rtol=1e-14) for v in samples)
    timing=read(ROOT/'timing/BATCH_SCALING.json')
    for b in c['workload']['B']:
        values=[v['mean_invocation_ms'] for v in samples if v['stage']=='primary' and v['B']==b]
        assert distribution(values)==timing[str(b)]['invocation_ms']
    work=read(ROOT/'counters/EXECUTED_WORK.json');stored=read(ROOT/'models/TILE_MODEL_FIT.json')
    for k,v in fit(work,c).items():assert v==stored[k],k
    assert stored['final_decision_valid'] and stored['B1_reproduction']['passed']
    assert stored['decision'] in (ROOT/'DECISION.md').read_text()
    print('PASS: publication hashes, frozen sources,75 receipts,48 primary processes and causal classifier')

if __name__=='__main__':verify()
