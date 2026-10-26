"""Single-epoch, serialized, resource-guarded correctness gates (never timings)."""
import argparse
import fcntl
import json
import os
import subprocess
import time
from pathlib import Path
import gpu_guard as guard

RESOURCE_GUARD=os.environ.get('GTS_RESOURCE_GUARD')
# Linux teardown/race/lock-lifetime regression has NOT run; do not bypass.
REMOTE_LAUNCH_READY=False
RESOURCE_GUARD_SHA256='2e9233cc2705b7edabfef722657997080dd1e73d8798f5bccc6bf00f91d960b7'
THREAD_ENV={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}


def save(path,value):
    guard.save(path,value)


def guarded_command(command,log,timeout=900):
    assert 0 < timeout <= 900
    if not RESOURCE_GUARD:
        raise ValueError('GTS_RESOURCE_GUARD or --resource-guard is required')
    return ['python3',str(RESOURCE_GUARD),'--log',str(log),'--rss-max-gb','16',
            '--mem-available-min-gb','48','--timeout-s',str(timeout),'--',*command]


def check_exit(code,label):
    if code in (3,97,98):
        guard.fatal('mandatory fail-stop return code',{'code':code,'label':label})
    if code != 0:
        raise RuntimeError(f'{label}: nonzero exit {code}; no automatic retry')


def run(root,epoch,index,gpu,case,arm,B,limit=0,tool=None,lock_fds=()):
    label=case.name+'_'+arm+(f'_{tool}' if tool else '')
    folder=epoch/label
    folder.mkdir()
    binary=root/'bin'/('G' if arm=='GB' else arm)
    command=[str(binary),str(case/'case.bin'),arm,str(B),str(folder/'result'),str(limit)]
    if tool:
        command=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','90',*command]
    guard.ensure_launch_memory()
    before=guard.snapshot(index)
    save(folder/'before_initial.json',before)
    settling=[]
    if not before['idle'] and not before['apps'].strip():
        settling.append(before)
        before=guard.snapshot(index)
    save(folder/'pre_settling.json',settling)
    save(folder/'before.json',before)
    if not before['idle']:
        raise guard.Contaminated('occupied before '+label)
    cmd=guarded_command(command,folder/'resource.guard.jsonl')
    receipt=dict(command=cmd,binary_sha256=guard.sha(binary),case_sha256=guard.sha(case/'case.bin'),
                 gpu_uuid=gpu,arm=arm,B=B,limit=limit,timing_eligible=False,adapter='native-knn-tombstone-overfetch-exact-delta')
    checks=[]
    problem=None
    known=guard.job_known()
    start=time.monotonic()
    with (folder/'stdout.log').open('x') as out,(folder/'stderr.log').open('x') as err:
        assert len(lock_fds)==2,'device and campaign lock descriptors required'
        p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True,pass_fds=lock_fds,
                           env={**os.environ,**THREAD_ENV,'CUDA_VISIBLE_DEVICES':gpu},cwd=root)
        receipt['guard_pid']=p.pid
        try:
            identity=guard.proc_identity(p.pid)
            known[p.pid]=identity[1] if identity else None
            while p.poll() is None:
                # Ownership is rooted at the subreaper, never an optional PID file.
                try:
                    p.wait(timeout=guard.POLL_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    state=guard.snapshot(index)
                    bad=guard.foreign_apps(state,p.pid,known)
                    checks.append(dict(time_utc=state['time_utc'],apps=state['apps'],foreign=bad))
                    if bad:
                        raise guard.Contaminated('foreign application '+label)
            receipt['exit_code']=p.wait()
            if guard.owned_children(p,known):
                problem=RuntimeError('guard exited with surviving descendants; no further launches')
        except BaseException as error:
            problem=error
        finally:
            if problem:
                receipt['cleanup_complete']=guard.terminate_guarded(p,known)
                if not receipt['cleanup_complete']:
                    guard.hold_failed_cleanup(p,known,folder/'CLEANUP_INCOMPLETE.json')
            receipt.setdefault('exit_code',p.poll())
    receipt['elapsed_s']=time.monotonic()-start
    if problem:
        receipt['exception']=type(problem).__name__+': '+str(problem)
    # Persist and latch mandatory codes before parsing possibly partial output.
    save(folder/'exit_status.json',{'exit_code':receipt['exit_code']})
    if receipt['exit_code'] in (3,97,98):
        save(folder/'receipt.json',receipt)
        check_exit(receipt['exit_code'],label)
    result=folder/'result.json'
    if result.exists():
        try:
            receipt['summary']=json.loads(result.read_text())
        except (OSError,json.JSONDecodeError) as error:
            receipt['summary_parse_error']=str(error)
    if tool:
        text=(folder/'stderr.log').read_text()+(folder/'stdout.log').read_text()
        receipt['sanitizer_zero_errors']='ERROR SUMMARY: 0 errors' in text
    save(folder/'checks.json',checks)
    save(folder/'receipt.json',receipt)
    print(label,receipt['exit_code'],receipt.get('summary'),flush=True)
    if problem:
        raise problem
    # Mandatory exits are checked BEFORE any further NVML access or launch.
    check_exit(receipt['exit_code'],label)
    if tool and not receipt['sanitizer_zero_errors']:
        raise RuntimeError('sanitizer gate failed '+label)
    if not receipt.get('summary',{}).get('correct',False):
        raise RuntimeError('correctness-failed '+label+'; retain output, no timing')
    after=guard.snapshot(index)
    save(folder/'after_initial.json',after)
    settling=[]
    if not after['idle'] and not after['apps'].strip():
        settling.append(after)
        after=guard.snapshot(index)
    save(folder/'after.json',after)
    save(folder/'settling.json',settling)
    if not after['idle']:
        raise guard.Contaminated('occupied after '+label)
    return receipt


def main():
    global RESOURCE_GUARD
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--resource-guard',default=RESOURCE_GUARD)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['bounded','full','sanitizers'],default='full')
    p.add_argument('--datasets',nargs='+')
    p.add_argument('--arms',nargs='+',choices=['D','G','P'],default=['D','G','P'])
    a=p.parse_args()
    if not REMOTE_LAUNCH_READY:
        raise RuntimeError('launch blocked: Linux guarded-subtree teardown and lock-lifetime validation pending')
    RESOURCE_GUARD=a.resource_guard
    if not RESOURCE_GUARD or guard.sha(RESOURCE_GUARD)!=RESOURCE_GUARD_SHA256:
        raise RuntimeError('authoritative resource guard hash mismatch or missing path')
    root=a.root.resolve()
    cases=a.cases.resolve()
    a.out=a.out.resolve()
    a.out.mkdir(exist_ok=True,parents=True)
    guard.STOP_ROOT=a.out
    if (a.out/'STOP_CAMPAIGN.json').exists():
        raise guard.FatalStop('prior STOP_CAMPAIGN.json exists; explicit user resumption required')
    guard.enable_subreaper()
    subprocess.run(['python3',str(root/'check_no_direct_insert.py')],check=True)
    manifest=json.loads((cases/'SMOKE_PINS.json').read_text())
    manifest=[c for c in manifest if not a.datasets or c['dataset'] in a.datasets]
    if a.mode=='sanitizers':
        manifest=[c for c in manifest if c['seed']==20261026]
    assert manifest,'no selected cases'
    for c in manifest:
        case=cases/(c['dataset']+'_'+str(c['seed']))
        for path,digest in c['hashes'].items():
            assert guard.sha(case/path)==digest,('frozen case hash',case,path)
    task=(a.out/'campaign.lock').open('a')
    fcntl.flock(task,fcntl.LOCK_EX|fcntl.LOCK_NB)
    index,state,device=guard.acquire(a.out)
    epoch=a.out/f'{a.mode}_{time.time_ns()}'
    epoch.mkdir()
    save(epoch/'admission.json',state)
    save(epoch/'runner.json',{'sha256':guard.sha(__file__),'gpu_guard_sha256':guard.sha(guard.__file__),'mode':a.mode})
    records=[]
    try:
        for c in manifest:
            case=cases/(c['dataset']+'_'+str(c['seed']))
            for arm in a.arms:
                B=10 if arm=='G' else 300
                if a.mode=='sanitizers':
                    for tool in ('memcheck','synccheck'):
                        records.append(run(root,epoch,index,state['uuid'],case,arm,7 if arm=='P' else B,30,tool,lock_fds=(device.fileno(),task.fileno())))
                else:
                    records.append(run(root,epoch,index,state['uuid'],case,arm,B,30 if a.mode=='bounded' else 0,lock_fds=(device.fileno(),task.fileno())))
        save(epoch/'COMPLETE.json',dict(mode=a.mode,records=records,performance_complete=False,
             all_processes_success=True,all_correct=True,
             sanitizers_pass=all(r.get('sanitizer_zero_errors',False) for r in records) if a.mode=='sanitizers' else None))
        print('COMPLETE',epoch,flush=True)
    except BaseException as error:
        save(epoch/'FAILED.json',dict(reason=type(error).__name__+': '+str(error),all_timing_ineligible=True))
        raise
    finally:
        device.close()
        task.close()

if __name__=='__main__':
    main()
