#!/usr/bin/env python3
"""Offline immutable input/output/resource closure; never starts a GPU workload."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser()
    for k in ('root','parent','reference','checker','data','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--parent-registration-sha256',required=True)
    a=p.parse_args();r=a.root;original=read(r/'REGISTERED.json');resume=read(r/'RESUME_REGISTERED.json');i=resume['identity']
    assert sha(a.data)==i['data_sha256']==original['data_sha256'];assert sha(a.parent/'campaign/REGISTERED.json')==a.parent_registration_sha256
    prior=read(a.parent/'campaign/REGISTERED.json')['reference'];assert prior==i['reference']==original['reference']
    assert all(sha(a.reference.parent/n)==h for n,h in prior.items())
    assert all(sha(r/n)==h for n,h in i['inputs'].items()) and all(sha(a.checker/n)==h for n,h in i['checker'].items())
    phases={};quality_payloads=0
    expected_qual={'unit_'+m for m in ('P0','P1','P2')}|{'unit_'+m+'_'+t for m in ('P1','P2') for t in ('memcheck','racecheck','synccheck')}|{c+'_'+m for c in ('bounded','target') for m in ('P0','P1','P2')}|{'bounded_'+m+'_'+t for m in ('P1','P2') for t in ('memcheck','racecheck','synccheck')}
    for phase in ('qualify','work','profile','formal'):
        g=read(r/phase/'GATE.json');assert g['passed'];assert all(sha(r/phase/n)==h for n,h in g['outputs'].items())
        rows=g['rows'];assert len({x['label'] for x in rows})==len(rows)
        if phase=='qualify':assert {x['label'] for x in rows}==expected_qual
        for row in rows:
            receipt=read(r/phase/'runs'/row['label']/'receipt.json')
            if row['label']!='ncu_probe':assert receipt['runtime_valid']
            else:assert 'ERR_NVGPUCTRPERM' in (r/phase/'runs/ncu_probe/stdout.log').read_text()+(r/phase/'runs/ncu_probe/stderr.log').read_text()
            if 'quality_sha256' in row:
                path=r/phase/'outputs'/(row['label']+'.quality.json');assert sha(path)==row['quality_sha256']
                for suffix,q in read(path).items():
                    assert q['passed'];prefix=r/phase/'outputs'/(row['label']+('.warmup' if suffix=='.warmup' else ''))
                    for field,h in q['payload_hashes'].items():assert sha(str(prefix)+field)==h;quality_payloads+=1
        phases[phase]={'processes':len(rows),'passed':True,'gate_sha256':sha(r/phase/'GATE.json')}
    assert sum(x['processes'] for x in phases.values())==49
    b=read(r/'BUILD_GATE.json')
    for m,records in b['modes'].items():
        for kind,rec in records.items():
            for suffix,key in [('', 'binary_sha256'),('.build.log','build_log_sha256'),('.resources.txt','resources_sha256'),('.sass.txt','sass_sha256')]:assert sha(r/m/(kind+suffix))==rec[key]
        for dirname,pinfile in [('source','SOURCE_PINS.json'),('count_source','COUNT_PINS.json')]:
            pins=read(r/m/pinfile);pins=pins['sources'] if dirname=='source' else pins
            for n,h in pins.items():assert sha(r/m/dirname/n)==h
    apps=subprocess.check_output(['nvidia-smi','-i',original['gpu'],'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip();assert not apps
    j=dict(passed=True,scope='Offline post-campaign hashes; no new GPU process; UUID/paths omitted',phases=phases,main_processes=48,diagnostic_NCU_probes=1,
        original_registration_sha256=sha(r/'REGISTERED.json'),resume_registration_sha256=sha(r/'RESUME_REGISTERED.json'),
        data_sha256=sha(a.data),parent_registration_sha256=sha(a.parent/'campaign/REGISTERED.json'),reference_hashes=prior,
        frozen_root_inputs=len(i['inputs']),checker_files=len(i['checker']),qualified_payload_files_rebound_to_original_quality_hashes=quality_payloads,
        unit_payload_closure='Nine deterministic real-kernel payloads independently revalidated by CPU-only verify_unit_payload.py; see UNIT_PAYLOAD_CLOSURE.json',gpu_clear_after=True,
        retained_failures=['first static shared admission','mutable outer run.log incorrectly frozen; original21 retained, offline resumed without rerun'])
    a.out.write_text(json.dumps(j,indent=2)+'\n');print('CLOSURE PASS: all49 receipts, external inputs/references, payloads, source/resource/SASS pins; GPU clear')
if __name__=='__main__':main()
