"""Tamper only fresh fixtures,never benchmark source,payloads or receipts."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,json
from pathlib import Path
import bind
import export as curate
from bind import digest,census,payloads,exact_stage,device_identity,require_closed
from unittest.mock import patch
from protocol import sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.work.mkdir();prefix=a.work/'sample';raw=Path(str(prefix)+'.ids.i32');raw.write_bytes(b'original');spec={raw.name:dict(sha256=sha(raw),bytes=8)};payloads(prefix,spec);count=0
    def reject(fn):
        nonlocal count
        try:fn()
        except (AssertionError,FileNotFoundError):count+=1;return
        raise RuntimeError('Tampered evidence was admitted')
    raw.write_bytes(b'changed!');reject(lambda:payloads(prefix,spec));raw.unlink();reject(lambda:payloads(prefix,spec));raw.write_bytes(b'original')
    extra=Path(str(prefix)+'.unexpected');extra.write_bytes(b'new');reject(lambda:payloads(prefix,spec));extra.unlink();payloads(prefix,spec)
    expected=[dict(label='A'),dict(label='B')];rows=[dict(label=label,status='passed',checked_sha256='x',guard_sha256='y') for label in ('A','B')];census(rows,expected)
    reject(lambda:census(rows[:1],expected));reject(lambda:census(rows+rows[:1],expected));reject(lambda:census(rows[::-1],expected));reject(lambda:census([{**rows[0],'status':'failed'},rows[1]],expected))
    for name in ('command.json','checked.json','guard.json'):
        f=a.work/name;f.write_bytes(b'original');h=sha(f);f.write_bytes(b'changed!');reject(lambda:digest(f,h));f.write_bytes(b'original');digest(f,h)
    assert count==10
    # Empty/stale inventories must fail in the actual admission entry point.
    receipt=a.work/'REGISTERED.json';receipt.write_bytes(b'registered fixture')
    source=a.work/'source.py';source.write_bytes(b'fixture source')
    expected={receipt,source,raw};proof=dict(schema=2,passed=True,CPU_rechecked_GIST_targets=338,source_guard_ready_command_census_complete=True,raw_payload_set_and_hash_complete=True,registration_sha256=sha(receipt),closure_validator_sha256=sha(Path(bind.__file__)),study_files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in expected},external_files={})
    with patch.object(bind,'inventory',return_value=(expected,set())),patch.object(bind,'load',return_value=proof):
        require_closed(a.work)
        for key in (None,'source.py',raw.name):
            old=proof['study_files'];proof['study_files']={} if key is None else {k:v for k,v in old.items() if k!=key}
            reject(lambda:require_closed(a.work));proof['study_files']=old
    with patch.object(bind,'load',return_value=dict(passed=True,CPU_rechecked_GIST_targets=338,study_files={},external_files={})):reject(lambda:require_closed(a.work/'nonexistent'))
    stage=a.work/'stage';stage.mkdir();[(stage/n).mkdir() for n in ('guards','outputs','reports')]
    jobs=[dict(label='fixture',kind='selftest',tool='plain')]
    for n in ('REGISTERED.json','RESULTS.json','fixture.command.json','fixture.checked.json','fixture.outer.log'):(stage/n).write_text('{}')
    guard=stage/'guards/fixture';guard.mkdir()
    for n in ('command.json','before.json','checks.json','after.json','stdout.log','receipt.json','gpu.csv','stderr.log'):(guard/n).write_text('{}')
    exact_stage(stage,jobs)
    for n in ('extra.command.json','extra.checked.json'):
        f=stage/n;f.touch();reject(lambda:exact_stage(stage,jobs));f.unlink()
    extra_guard=stage/'guards/extra';extra_guard.mkdir();reject(lambda:exact_stage(stage,jobs));extra_guard.rmdir()
    extra_output=stage/'outputs/unregistered.ids.i32';extra_output.touch();reject(lambda:exact_stage(stage,jobs));extra_output.unlink()
    before=dict(device='0, GPU-fixture, device, 0 MiB, 0 %',apps='');after=dict(before);r=dict(gpu='0')
    device_identity(r,before,after,'0','GPU-fixture')
    reject(lambda:device_identity(dict(gpu='1'),before,after,'0','GPU-fixture'))
    reject(lambda:device_identity(r,before,{**after,'device':'0, GPU-other, device'},'0','GPU-fixture'))
    assert count==20
    closed=a.work/'CLOSED_IDENTITY.json';closed.write_text('closed fixture')
    names={'analysis/SUMMARY.json','profile_analysis/SUMMARY.json'}
    for name in names:
        f=a.work/name;f.parent.mkdir(exist_ok=True);f.write_text('derived fixture')
    dproof=dict(passed=True,independently_recomputed=True,closed_identity_sha256=sha(closed),sources={'fixture.py':'source digest'},files={n:dict(sha256=sha(a.work/n),bytes=(a.work/n).stat().st_size) for n in names})
    with patch.object(bind,'derived_names',return_value=names),patch.object(bind,'derived_sources',return_value={'fixture.py':'source digest'}),patch.object(bind,'load',return_value=dproof):
        bind.require_derived(a.work,{'fixture':True})
        old=dproof['files'];dproof['files']={};reject(lambda:bind.require_derived(a.work,{'fixture':True}));dproof['files']=old
        f=a.work/'analysis/SUMMARY.json';f.write_text('tampered');reject(lambda:bind.require_derived(a.work,{'fixture':True}));f.write_text('derived fixture')
        dproof['sources']={'fixture.py':'different digest'};reject(lambda:bind.require_derived(a.work,{'fixture':True}));dproof['sources']={'fixture.py':'source digest'}
        f=a.work/'profile_analysis/extra.json';f.touch();reject(lambda:bind.require_derived(a.work,{'fixture':True}));f.unlink()
        dproof['independently_recomputed']=False;reject(lambda:bind.require_derived(a.work,{'fixture':True}));dproof['independently_recomputed']=True
    assert count==25
    work=a.work/'external_source_archive';work.mkdir()
    for folder in bind.STAGES:(work/folder).mkdir()
    outside=a.work/'outside_checkout';outside.mkdir();(outside/'frozen.py').write_text('measured source')
    here=outside/'curator';here.mkdir();(here/'export.py').write_text('curation source')
    with patch.object(curate,'REPO',outside),patch.object(curate,'HERE',here):
        entries,paths=curate.raw_files(work,{'sources':{'frozen.py':'fixture'}})
    assert set(entries)=={'source/frozen.py','curation_source/export.py'} and set(paths)==set(entries)
    assert all(not Path(n).is_absolute() and paths[n].is_file() and entries[n]['sha256']==sha(paths[n]) for n in entries)
    print(json.dumps(dict(passed=True,tamper_rejections=count,missing_unconsumed_payload_rejected=True,changed_checked_command_guard_rejected=True,empty_proof_and_missing_source_payload_rejected=True,extra_physical_stage_entries_rejected=True,actual_device_mismatch_rejected=True,derived_result_tampering_rejected=True,source_outside_work_archive_fixture=True,exact_census=True,GPU_starts=0,scope='CPU fixtures,not actual raw mutation')))
if __name__=='__main__':main()
