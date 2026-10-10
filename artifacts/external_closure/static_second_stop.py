#!/usr/bin/env python3
"""Rebind the second interrupted matrix without converting its invalid sample into a pass."""
import argparse,json,math
from pathlib import Path
import static_campaign as c
from static_check import read,check,requests
from qualify import cpu

def structure(reg,rows,labels,complete):
    expected=c.jobs('recovery')
    assert reg['jobs']==expected and not complete
    assert list(rows)==[j['label'] for j in expected[:44]]
    assert labels=={j['label'] for j in expected[:45]}

def inspect(a):
    c.verify_inputs(a.work);admitted=c.qualification_gate(a);retained=c.stopped_prefix(a)
    folder=a.work/'recovery';reg=read(folder/'REGISTERED.json');rows=read(folder/'ROWS.json');expected=c.jobs('recovery')
    structure(reg,rows,c.guard_labels(folder/'guards'),(folder/'COMPLETE.json').exists())
    assert reg['source_sha256']==c.sources() and cpu.sha(folder/'EXECUTED.py')==c.sources()['static_campaign.py']
    assert reg['preserved_prefix']==retained and reg['preflight_sha256']==cpu.sha(folder/'DEPENDENCIES_PREFLIGHT.json')
    assert reg['recovery_contract_sha256']==cpu.sha(c.HERE/'STATIC_RECOVERY.json')
    for key,val in dict(contract_sha256=cpu.sha(c.HERE/'STATIC_CONTRACT.json'),inputs_sha256=cpu.sha(a.work/'INPUTS.json'),build_sha256=cpu.sha(a.build/'BUILD.json'),guard_sha256=cpu.sha(a.guard),gpu=a.gpu,numa_node=a.numa_node).items():assert reg[key]==val
    built=read(a.build/'BUILD.json');assert all(cpu.sha(a.build/'bin'/n)==h for n,h in built['binaries'].items())
    for j in read(a.build/'PREPARED.json')['sources']:
        assert cpu.sha(a.build/'source'/j)==read(a.build/'PREPARED.json')['sources'][j]
    inputs=read(a.work/'INPUTS.json')['records'];valid=[];guards={};failed=expected[44]['label']
    for job in expected[:45]:
        label=job['label'];g=folder/'guards'/label;receipt=read(g/'receipt.json');command=read(folder/(label+'.command.json'))
        assert receipt['gpu']==a.gpu and receipt['command'][1:3]==[f'--cpunodebind={a.numa_node}',f'--membind={a.numa_node}']
        assert receipt['command'][3:]==command['command'] and command['environment']==reg['environment']
        assert command['request_sha256']==cpu.sha(folder/'requests'/(label+'.txt'))
        process=read(folder/(label+'.process.json'));assert process['returncode']==0 and all(math.isfinite(process[k]) and process[k]>=0 for k in ('wall_s','cpu_user_s','cpu_system_s','max_rss_bytes'))
        r=inputs[job['snapshot']];gold=read(a.work/'reference'/job['snapshot']/'REFERENCE.json');gold['folder']=a.work/'reference'/job['snapshot']
        actual=check(folder/'outputs'/label,job['method'],requests(r['qids'],job['method'],job['order']),gold)
        if label!=failed:
            guards[label]=c.guard_check(g);assert actual==rows[label]
            if job['method']=='GTSPP_P':assert actual['canonical_sha256']==admitted['rows']['P_'+job['snapshot']]['canonical_sha256']
            valid.append(dict(**job,quality_passed=True,queries=actual['queries'],items=actual['items'],output_hashes=actual['output_hashes'],canonical_sha256=actual['canonical_sha256'],receipt_sha256=cpu.sha(g/'receipt.json')))
        else:
            assert receipt['exit_code']==0 and not receipt['runtime_valid'] and receipt['stop_reason']=='foreign GPU activity'
            checks=read(g/'checks.json');assert len([r for r in checks if r['foreign']])==1
            fail=dict(label=label,exit_code=0,runtime_valid=False,stop_reason=receipt['stop_reason'],wall_s=receipt['wall_s'],process_wall_s=process['wall_s'],output_quality_passed=actual['passed'],output_hashes=actual['output_hashes'],check_count=len(checks),flagged_checks=[r for r in checks if r['foreign']],before_empty=read(g/'before.json')['apps']=='',after_empty=read(g/'after.json')['apps']=='',receipt_sha256=cpu.sha(g/'receipt.json'))
    return dict(verifier_sha256=cpu.sha(__file__),status='SECOND_STOP_INCOMPLETE_NO_FORMAL_RANKING',valid_total=48,original_valid=4,recovery_valid=44,external_attempts=50,total_primary_attempts_including_RTP=68,remaining_valid_slots=24,unattempted=23,retained_failures=2,registration_sha256=cpu.sha(folder/'REGISTERED.json'),rows_sha256=cpu.sha(folder/'ROWS.json'),source_sha256=reg['source_sha256'],contract_sha256=reg['contract_sha256'],build_sha256=reg['build_sha256'],binary_sha256=built['binaries'],retained_original=retained,guard_hashes=guards,rows=valid,failure=fail,failed_file_hashes={str(p.relative_to(folder)):cpu.sha(p) for p in folder.rglob('*') if p.is_file() and (p.name.startswith(failed+'.') or failed in p.parts)},interpretation='The old guard did not log owned PID identities. An exit/snapshot race is possible from its source and a CPU-only regression, but historical ownership is unproven. The sample remains invalid. No automatic replacement.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('work','build','guard','qualification-source','original-source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True);a=p.parse_args();assert __debug__
    a.output=c.outside_repo(a.output)
    value=inspect(a);a.output.open('x').write(json.dumps(value,indent=2)+'\n');print('PASS all48 retained observations, complete output rechecks and both retained failures; matrix still incomplete')
