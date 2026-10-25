"""Account for failed-quality workloads without timing/promoting invalid outputs."""
import fcntl,json,sys,time
from pathlib import Path
import campaign_quality_support_v4 as m

def binary(root,arm,count=False):
    return root/'bin'/('arborx_count_fast' if count else 'arborx_bench') if arm=='X' else root/'bin'/('bench_count_v4' if count else 'bench_v3')

def verify_run(run,root,gpu,kind,q,k,arm,tool=None,fixture=False,count=False,dump=False):
    rec=json.loads((run/'receipt.json').read_text())
    expected={'gpu_uuid':gpu,'kind':kind,'Q':q,'k':k,'arm':arm,'tool':tool,'instrumented':count,'reps':0,'warmups':0,'dump':dump}
    assert all(rec.get(key)==value for key,value in expected.items()),('receipt identity mismatch',run)
    assert rec['binary_sha256']==m.sha(binary(root,arm,count))
    oracle=root/('bounded' if fixture else 'fixtures')/(kind+'.oracle')
    assert rec['oracle_sha256']==m.sha(oracle)
    assert rec['exit_code'] in (0,20,21) and not rec.get('exception')
    assert json.loads((run/'before.json').read_text())['idle'] and json.loads((run/'after.json').read_text())['idle']
    assert all(not row['foreign'] for row in json.loads((run/'checks.json').read_text()))
    for name,digest in rec['result_files'].items():
        assert Path(name).name==name and m.sha(run/name)==digest,(run,name)
    required={'result.pid'}
    if dump:required.add('result.native.bin')
    if count:required.add('result.work.json')
    if rec['exit_code']==0:required.add('result.json')
    assert required.issubset(rec['result_files']),('missing bound result files',run)
    if tool:assert rec['exit_code']==0
    if rec['exit_code']==0:assert rec['valid'] and json.loads((run/'result.json').read_text())['correct']
    return rec

def full_and_gates(root,epoch,index,state):
    gpu=state['uuid'];cases=[];evidence={}
    def call(label,kind,q,k,arm,**kw):return m.execute(root,epoch,index,gpu,label,kind,q,k,arm,**kw)
    for kind,k,q in m.cases():
        status={};paths={}
        for arm in ('ARS' if kind=='words' else 'ARSX'):
            label=f'full_{kind}_k{k}_q{q}_{arm}'
            run=call(label,kind,q,k,arm,dump=True,allow_quality_failure=True)
            rec=verify_run(run,root,gpu,kind,q,k,arm,dump=True)
            status[arm]='pass' if rec['exit_code']==0 else 'correctness_failed'
            paths[arm]=run/'result.native.bin';assert paths[arm].exists()
            evidence[label]={'path':str(run.relative_to(root)),'receipt_sha256':m.sha(run/'receipt.json'),'binary_sha256':rec['binary_sha256'],'status':status[arm]}
        assert m.same_file(paths['A'],paths['R']),('native_A_R_order',kind,k,q)
        cases.append({'kind':kind,'k':k,'Q':q,'quality':status,'eligible':all(v=='pass' for v in status.values()),'native_A_R_sha256':m.sha(paths['A'])})
    m.save(epoch/'FULL_QUALITY.json',{'cases':cases,'evidence':evidence,'all_required_workloads_accounted':18})
    gates={}
    for kind in ('words','tloc'):
        for arm in ('ARS' if kind=='words' else 'ARSX'):
            for tool in ('memcheck','synccheck'):
                for k in range(3):
                    label=f'gate_{kind}_{arm}_{tool}_k{k}'
                    run=call(label,kind,32,k,arm,tool=tool,fixture=True)
                    rec=verify_run(run,root,gpu,kind,32,k,arm,tool=tool,fixture=True)
                    assert 'ERROR SUMMARY: 0 errors' in (run/'stdout.log').read_text()+(run/'stderr.log').read_text()
                    gates[label]={'path':str(run.relative_to(root)),'receipt_sha256':m.sha(run/'receipt.json')}
        call('stress_'+kind+'_R',kind,32,1,'R',reps=1)
    m.save(epoch/'GATES_PASS.json',{'bounded_sanitizer_runs':42,'changing_ID_Graph_replays_per_metric':64,'evidence':gates})
    return cases

def run_epoch(root,epoch,index,state):
    gpu=state['uuid'];m.save(epoch/'admission.json',state)
    frozen=json.loads((root/'FROZEN_CPU_ORACLE.json').read_text());verified={}
    for p,v in frozen['files'].items():
        if p.startswith('fixtures/'):assert m.sha(root/p)==v['sha256'];verified[p]=v['sha256']
    m.save(epoch/'frozen_inputs_verified.json',verified)
    bins={p.name:m.sha(p) for p in [binary(root,'A'),binary(root,'A',True),binary(root,'X'),binary(root,'X',True)]};m.save(epoch/'binaries.json',bins)
    m.save(epoch/'source_plan.json',{'planner_sha256':m.sha(__file__),'monitor_sha256':m.sha(m.__file__),'policy':'failed quality is retained, ineligible for timing and ratios; no radius/oracle change'})
    cases=full_and_gates(root,epoch,index,state)
    counted={}
    for case in cases:
        kind,k,q=case['kind'],case['k'],case['Q']
        for arm in ('ARS' if kind=='words' else 'ARSX'):
            label=f'count_{kind}_k{k}_q{q}_{arm}'
            run=m.execute(root,epoch,index,gpu,label,kind,q,k,arm,count=True,allow_quality_failure=True)
            rec=verify_run(run,root,gpu,kind,q,k,arm,count=True);assert (run/'result.work.json').exists()
            assert (rec['exit_code']==0)==(case['quality'][arm]=='pass')
            counted[label]={'receipt_sha256':m.sha(run/'receipt.json'),'quality':case['quality'][arm]}
    m.save(epoch/'COUNT_COLLECTED.json',counted)
    schedule=[{**case,'orders':m.THREE if case['kind']=='words' else m.FOUR,'timed_arms':('ARS' if case['kind']=='words' else 'ARSX') if case['eligible'] else ''.join(a for a,v in case['quality'].items() if v=='pass')} for case in cases]
    m.save(epoch/'TIMING_SCHEDULE.json',schedule)
    for g in range(6):
        for case in schedule:
            for arm in case['orders'][g]:
                if arm not in case['timed_arms']:continue
                m.execute(root,epoch,index,gpu,f"time_g{g}_{case['kind']}_k{case['k']}_q{case['Q']}_{arm}",case['kind'],case['Q'],case['k'],arm,reps=3,warm=3)
        m.save(epoch/f'ROUND_{g}_COMPLETE.json',{'round':g,'gpu_uuid':gpu})
    assert bins=={p.name:m.sha(p) for p in [binary(root,'A'),binary(root,'A',True),binary(root,'X'),binary(root,'X',True)]}
    m.save(epoch/'TIMING_COMPLETE.json',{'gpu_uuid':gpu,'rounds':6,'eligible_cases':sum(c['eligible'] for c in cases),'quality_failed_cases':sum(not c['eligible'] for c in cases),'all_required_workloads_accounted':18,'binary_hashes':bins,'state':'complete_eligible_timing_with_retained_quality_failures'})

def main(root):
    assert hasattr(__import__('os'),'pidfd_open') and hasattr(__import__('signal'),'pidfd_send_signal'),'Linux pidfd support required'
    root=Path(root).resolve();task=(root/'campaign.lock').open('a');fcntl.flock(task,fcntl.LOCK_EX|fcntl.LOCK_NB)
    while True:
        index,state,lock=m.acquire(root);epoch=root/'runs'/f'quality_{time.time_ns()}';epoch.mkdir();(root/'logs/active_epoch.txt').write_text(str(epoch)+'\n');(root/'logs/runner.pid').write_text(str(__import__('os').getpid())+'\n')
        try:run_epoch(root,epoch,index,state)
        except m.Contaminated as e:m.save(epoch/'INVALID_EPOCH.json',{'reason':str(e),'all_timing_ineligible':True});print('RESTART ENTIRE TIMING EPOCH',e,flush=True);lock.close();time.sleep(5);continue
        except BaseException as e:m.save(epoch/'FAILED.json',{'reason':type(e).__name__+': '+str(e)});lock.close();raise
        lock.close();print('TIMING COMPLETE',epoch,flush=True);return
if __name__=='__main__':main(*sys.argv[1:])
