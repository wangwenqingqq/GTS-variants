"""Explicitly authorized same-card recovery after foreign activity;no automatic retry."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,importlib.util,sys
from pathlib import Path
from common import HERE,load,save,sha,jobs
import campaign as frozen

RECOVERY='primary_recovery_02'

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--stage',choices=(RECOVERY,'shapes','calibration','profile'),required=True);a=p.parse_args()
    w=a.work.resolve();root=w.parent;amend=load(root/'CONTINUATION_PRIMARY_AUTHORIZATION.json')
    assert amend['human_authorized'] and amend['same_gpu_required'] and amend['prior_starts']==93 and amend['campaign_max_starts']==341
    assert amend['controller_sha256']==sha(Path(__file__)) and amend['corrected_validator_sha256']==sha(a.validator)
    assert amend['original_primary_failure_sha256']==sha(w/'primary/RESULTS.json')
    initial=jobs('primary');old=load(w/'primary/RESULTS.json')
    assert [r['label'] for r in old['rows']]==[j['label'] for j in initial]
    assert [r['status'] for r in old['rows']]==['passed']*44+['failed']+['not_executed']*147
    guard=load(w/'primary/guards'/initial[44]['label']/'receipt.json')
    assert not guard['runtime_valid'] and guard['stop_reason']=='foreign GPU activity'
    assert load(w/'REGISTERED.json')['gpu']==amend['gpu']==guard['gpu']
    assert load(w/'QUALIFICATION_ADMISSION.json')['passed'] and load(w/'SCREEN_DECISION.json')['operator_screen_supports_expansion']
    assert sha(w/'ANALYSIS_FREEZE.json')==amend['original_analysis_freeze_sha256']
    if a.stage==RECOVERY:assert len((w/'STARTS.jsonl').read_text().splitlines())==93
    else:
        admission=load(w/'PRIMARY_ADMISSION.json');assert admission['passed'] and admission['unique_qualified_primary_targets']==192 and admission['passed_targets_reexecuted']==0
    spec=importlib.util.spec_from_file_location('corrected_CPU_validator',a.validator);validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    original_jobs=frozen.jobs
    frozen.jobs=lambda stage:initial[44:] if stage==RECOVERY else original_jobs(stage)
    frozen.STAGES=('qualification_recovery_01','screen',RECOVERY,'shapes','calibration','profile')
    frozen.check=validator.check
    # The amendment changes only the CPU launch-budget field,not the frozen file or any measurement function.
    def amended_load(path):
        value=load(path)
        if Path(path).resolve()==HERE/'CONTRACT.json':
            assert value['max_GPU_starts']==340;value={**value,'max_GPU_starts':341}
        return value
    frozen.load=amended_load
    save(w/(a.stage+'.recovery_02.json'),dict(before_new_targets=True,authorization_sha256=sha(root/'CONTINUATION_PRIMARY_AUTHORIZATION.json'),controller_sha256=sha(Path(__file__)),validator_sha256=sha(a.validator),
        original_executor_sha256=sha(HERE/'campaign.py'),original_primary_failure_sha256=sha(w/'primary/RESULTS.json'),jobs=frozen.jobs(a.stage),only_budget_override=dict(original=340,authorized=341)))
    sys.argv=[str(HERE/'campaign.py'),'--work',str(w),'--stage',a.stage];frozen.main()
    if a.stage==RECOVERY:
        result=load(w/RECOVERY/'RESULTS.json');assert result['complete'] and len(result['rows'])==148
        save(w/'PRIMARY_ADMISSION.json',dict(passed=True,unique_qualified_primary_targets=192,passed_targets_reexecuted=0,invalid_target_reexecuted=1,
            old_44_retained=True,original_failed_guard_retained=True,original_result_sha256=sha(w/'primary/RESULTS.json'),recovery_result_sha256=sha(w/RECOVERY/'RESULTS.json'),
            scope='44 original passed targets +148 recovered targets;the single foreign-contaminated attempt is retained but excluded from timing.'))

if __name__=='__main__':main()
