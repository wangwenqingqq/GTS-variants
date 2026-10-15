"""Verify the public stopped checkpoint without a GPU or private raw evidence."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import collections
import shutil
import subprocess
import tempfile
from pathlib import Path
from common import HERE, REPO, load, sha


def main():
    manifest=load(HERE/'PUBLIC_MANIFEST.json')['files']
    actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name!='PUBLIC_MANIFEST.json'}
    assert actual==set(manifest) and all(not p.is_symlink() for p in HERE.rglob('*'))
    for name,r in manifest.items():assert sha(HERE/name)==r['sha256'] and (HERE/name).stat().st_size==r['bytes']
    e=load(HERE/'evidence/EXECUTION_R1.json');q=load(HERE/'evidence/QUALITY_R1.json');cpu=load(HERE/'evidence/CPU_FIX_VALIDATION.json')
    assert not e['complete'] and not e['native_Host_attribution_admissible'] and e['GPU_starts']==84 and e['original_max_GPU_starts']==124
    assert e['qualification_passed']==29 and e['primary_passed']==54 and e['interrupted']==1 and e['primary_not_executed']==29 and e['timeline_not_executed']==11
    assert e['exact_partial_stage_census'] and e['automatic_retries']==0 and e['no_foreign_signals']
    assert collections.Counter(r['status'] for r in e['records'])==dict(passed=83,failed=1,not_executed=29)
    assert q['nonselftest_rows_rechecked']==75 and q['selftests']==8 and q['does_not_repair_R1_timing_provenance']
    assert len(q['records'])==83 and q['interrupted_output_only_not_measurement']
    assert cpu['passed'] and cpu['GPU_starts']==0 and cpu['cases']==27 and cpu['negative_mutation_tests']==27 and cpu['negative_field_accounting_tests']==14
    raw=load(HERE/'evidence/RAW_MANIFEST_R1.json')
    assert raw['stable_archive']['bytes']>0 and len(raw['stable_archive']['sha256'])==64
    assert raw['first_archive_rejected']['exit_code']==1 and raw['cleanup_receipt_sha256']
    assert 'interrupted_telemetry_child_cleanup' in e
    identities=load(HERE/'provenance/R1_SOURCE_IDENTITY.json')['R1_executed_task_sources']
    with tempfile.TemporaryDirectory(prefix='update-r1-source-') as temporary:
        target=Path(temporary)
        for name in ('generate.py','quality.py','test_protocol.py'):shutil.copyfile(HERE/name,target/name)
        subprocess.run(['patch','--batch','-R','-p1','-i',str(HERE/'provenance/R1_SOURCE.diff')],cwd=target,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for name,h in identities.items():
            path=target/name if (target/name).exists() else HERE/'provenance/SCOPE_R1.md' if name=='SCOPE.md' else HERE/name
            assert sha(path)==h, ('Original R1 source reconstruction',name)
        raw_source=load(HERE/'evidence/IDENTITY_R1.json')['executed_sources']
        own='artifacts/dynamic_update_critical_path_20261015/'
        for name,h in raw_source.items():
            if name.startswith(own):assert identities[name[len(own):]]==h
            else:assert sha(REPO/name)==h
    assert sha(HERE/'CONTRACT.json')==sha(HERE/'provenance/CONTRACT_R1.json')
    print('PUBLIC_CHECKPOINT_PASS:exact manifest,84-start stop,75 offline outputs,R1 source reconstruction;NO GPU/native attribution admission')


if __name__=='__main__':main()
