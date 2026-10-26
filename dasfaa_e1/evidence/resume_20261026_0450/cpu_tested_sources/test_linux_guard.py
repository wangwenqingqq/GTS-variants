"""CPU-only Linux evidence for the exact runner/resource-watchdog composition.

Run this script under the authoritative resource guard. It never intentionally
triggers a resource refusal, resource kill, fail-fast exit or GPU/NVML call.
It does not validate standalone guard.py against daemonized descendants.
"""
import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import gpu_guard as guard

PAYLOAD=r'''
import os,signal,sys,time,threading
from pathlib import Path
out=Path(sys.argv[1]);deadline=time.monotonic()+12
signal.alarm(12)
def mark(label):
    with (out/'pids.jsonl').open('a') as f:
        f.write(__import__('json').dumps({'label':label,'pid':os.getpid(),'ppid':os.getppid(),'sid':os.getsid(0)})+'\n')
def wait():
    while time.monotonic()<deadline:time.sleep(.02)
mark('root')
pid=os.fork()
if pid==0:
    os.setsid();mark('separate-session-child')
    time.sleep(.10)
    late=os.fork()
    if late==0:
        os.setsid();mark('late-orphan-grandchild');wait();os._exit(0)
    os._exit(0)
# The parent intentionally does not reap; the late process must reach subreaper.
wait()
'''


def wait_for(predicate,timeout=3):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=predicate()
        if result:return result
        time.sleep(.01)
    raise AssertionError('bounded fixture condition not reached')


def locks_available(paths):
    handles=[]
    try:
        for path in paths:
            handle=path.open('a');handles.append(handle)
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return False
        return True
    finally:
        for handle in handles:handle.close()


def exercise(folder,resource_guard,inject_failure):
    folder.mkdir()
    payload=folder/'payload.py';payload.write_text(PAYLOAD)
    lock_paths=[folder/'device.lock',folder/'task.lock']
    locks=[path.open('a') for path in lock_paths]
    for handle in locks:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    known=guard.job_known()
    command=[sys.executable,str(resource_guard),'--log',str(folder/'resource.guard.jsonl'),
             '--rss-max-gb','1','--mem-available-min-gb','48','--timeout-s','30','--',
             sys.executable,str(payload),str(folder)]
    with (folder/'stdout.log').open('x') as out,(folder/'stderr.log').open('x') as err:
        p=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True,
                           pass_fds=tuple(handle.fileno() for handle in locks))
        identity=guard.proc_identity(p.pid);assert identity
        known[p.pid]=identity[1]
        try:
            def read_pids():
                path=folder/'pids.jsonl'
                if not path.exists():return None
                rows=[json.loads(line) for line in path.read_text().splitlines()]
                return rows if len(rows)>=3 else None
            rows=wait_for(read_pids)
            assert not (folder/'result.pid').exists()
            assert rows[1]['sid'] != rows[0]['sid']
            # Wait until the late orphan has been adopted, not merely forked.
            orphan=rows[-1]['pid']
            wait_for(lambda:guard.proc_identity(orphan)[0] == os.getpid())
            for handle in locks:handle.close()
            assert not locks_available(lock_paths),'watchdog did not retain both locks'
            failure_observed=False
            if inject_failure:
                original=guard.signal_owned
                def reject_kill(pid,sig,*args):
                    if pid == orphan and sig == signal.SIGKILL:return False
                    return original(pid,sig,*args)
                with patch.object(guard,'signal_owned',side_effect=reject_kill):
                    assert not guard.terminate_guarded(p,known),'injected failure was ignored'
                assert not locks_available(lock_paths),'locks released during incomplete cleanup'
                failure_observed=True
            complete=guard.terminate_guarded(p,known)
            assert complete,'whole subtree was not verified absent'
            assert p.returncode not in (3,97,98),'unexpected mandatory stop code'
            assert not guard.owned_children(p,known),'adopted descendant survived'
            assert all(guard.proc_identity(row['pid']) is None for row in rows),'fixture process survived'
            assert locks_available(lock_paths),'locks not released after verified completion'
            events=[json.loads(line) for line in (folder/'resource.guard.jsonl').read_text().splitlines()]
            assert events[-1]['event']=='end','missing final watchdog receipt'
            return {'passed':True,'injected_failure_checked':failure_observed,'rows':rows,
                    'watchdog_exit':p.returncode,'guard_receipt':events[-1],
                    'no_result_pid':True,'inherited_locks_retained':True,
                    'whole_subtree_absent':True,'locks_released_only_after_completion':True}
        finally:
            for handle in locks:handle.close()
            if p.poll() is None or guard.owned_children(p,known):
                # Fixture-only recovery, never a retry of the experimental gate.
                if not guard.terminate_guarded(p,known):
                    for pid in guard.owned_children(p,known):
                        guard.signal_owned(pid,signal.SIGCONT,p.pid,known)
                    p.wait(timeout=15)
                    guard.reap_adopted(p,known)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resource-guard',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert sys.platform=='linux','Linux-only integration test'
    args.out.mkdir(parents=True,exist_ok=False)
    guard.enable_subreaper()
    records=[]
    for label,inject in [('late_fork_and_locks',False),('termination_failure_and_locks',True)]:
        record=exercise(args.out/label,args.resource_guard,inject);record['label']=label
        records.append(record);print(json.dumps(record),flush=True)
    result={'passed':True,'scope':'CPU runner cancellation and inherited-lock composition only',
            'standalone_resource_guard_daemon_containment_validated':False,
            'outer_guard_kill_can_bypass_runner_cleanup':True,
            'gpu_admission_cleared':False,'records':records}
    (args.out/'COMPLETE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
