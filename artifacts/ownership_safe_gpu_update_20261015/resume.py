"""Authorized validator-only continuation;preserve old failure,never rerun old targets."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,importlib.util,json,sys
from pathlib import Path
from common import HERE,load,save,sha,jobs
import campaign as frozen

RECOVERY='qualification_recovery_01'

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--stage',choices=(RECOVERY,'screen','primary','shapes','calibration','profile'),required=True);a=p.parse_args()
    w=a.work.resolve();root=w.parent;amend=load(root/'CONTINUATION_AUTHORIZATION.json');review=load(root/'OFFLINE_REVIEW_R1/RECEIPT.json')
    assert amend['human_authorized'] and amend['no_GPU_reruns'] and amend['campaign_max_starts']==340 and amend['prior_starts']==16
    assert amend['controller_sha256']==sha(Path(__file__)) and amend['corrected_validator_sha256']==sha(a.validator)
    assert review['passed'] and review['GPU_starts']==0 and review['unchanged_measurement_sources_and_raw_outputs'] and len(review['records'])==16
    assert amend['offline_review_sha256']==sha(root/'OFFLINE_REVIEW_R1/RECEIPT.json')
    failed=load(w/'qualification/RESULTS.json');assert not failed['complete']
    initial=jobs('qualification');assert [r['label'] for r in failed['rows']]==[j['label'] for j in initial]
    assert [r['status'] for r in failed['rows']]==['passed']*15+['failed']+['not_executed']*26
    assert [r['label'] for r in review['records']]==[j['label'] for j in initial[:16]]
    starts=[json.loads(line) for line in (w/'STARTS.jsonl').read_text().splitlines()]
    assert [r['label'] for r in starts[:16]]==[j['label'] for j in initial[:16]] and all(r['stage']=='qualification' for r in starts[:16])
    if a.stage==RECOVERY:assert len(starts)==16
    else:
        admission=load(w/'QUALIFICATION_ADMISSION.json');assert admission['passed'] and admission['unique_qualified_targets']==42 and admission['prior_targets_reexecuted']==0
    spec=importlib.util.spec_from_file_location('corrected_CPU_validator',a.validator);validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    original_jobs=frozen.jobs
    frozen.jobs=lambda stage:initial[16:] if stage==RECOVERY else original_jobs(stage)
    frozen.STAGES=(RECOVERY,'screen','primary','shapes','calibration','profile')
    frozen.check=validator.check
    # No computation/timing function is patched;only stage admission and a CPU counter check.
    save(w/(a.stage+'.continuation.json'),dict(before_new_targets=True,authorization_sha256=sha(root/'CONTINUATION_AUTHORIZATION.json'),controller_sha256=sha(Path(__file__)),validator_sha256=sha(a.validator),original_executor_sha256=sha(HERE/'campaign.py'),original_failure_sha256=sha(w/'qualification/RESULTS.json'),jobs=frozen.jobs(a.stage)))
    sys.argv=[str(HERE/'campaign.py'),'--work',str(w),'--stage',a.stage];frozen.main()
    if a.stage==RECOVERY:
        result=load(w/RECOVERY/'RESULTS.json');assert result['complete'] and len(result['rows'])==26
        save(w/'QUALIFICATION_ADMISSION.json',dict(passed=True,unique_qualified_targets=42,prior_targets_reexecuted=0,original_failed_target_retained=True,original_failure_sha256=sha(w/'qualification/RESULTS.json'),prior_offline_review_sha256=sha(root/'OFFLINE_REVIEW_R1/RECEIPT.json'),recovery_result_sha256=sha(w/RECOVERY/'RESULTS.json'),validator_sha256=sha(a.validator),scope='16 original targets admitted by offline recheck +26 newly executed targets;original failure not overwritten'))

if __name__=='__main__':main()
