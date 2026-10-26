"""Reuse campaign v4 locks/PID ownership; add mandatory v3 fail-stop boundaries."""
import csv, ctypes, datetime, fcntl, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path

ELIGIBLE=(6,7,0,4,5,1,2,3)
POLL_SECONDS=30
_LAST_SNAPSHOT=None
_FATAL=None
STOP_ROOT=None
class Contaminated(RuntimeError): pass
class FatalStop(RuntimeError): pass
class NoIdleGPU(RuntimeError): pass

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''): h.update(b)
    return h.hexdigest()

def save(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2); f.write('\n')

def host_memory():
    return {line.split(':')[0]:int(line.split()[1])*1024
            for line in Path('/proc/meminfo').read_text().splitlines()}

def fatal(reason,detail=None):
    global _FATAL
    # FIRST evidence after an NVML timeout: host memory, not another NVML call.
    memory=host_memory()
    _FATAL={'reason':reason,'memory':memory,'detail':detail,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if STOP_ROOT is not None:
        path=Path(STOP_ROOT)/'STOP_CAMPAIGN.json'
        if not path.exists(): save(path,_FATAL)
    raise FatalStop(json.dumps(_FATAL))

def ensure_launch_memory():
    if _FATAL is not None: raise FatalStop('campaign already stopped')
    memory=host_memory()
    if memory['MemAvailable'] < 64*(1024**3):
        raise NoIdleGPU('prelaunch MemAvailable below 64 GiB; do not launch')
    return memory

def snapshot(index):
    global _LAST_SNAPSHOT
    if _FATAL is not None: raise FatalStop('campaign already stopped')
    if _LAST_SNAPSHOT is not None:
        time.sleep(max(0,POLL_SECONDS-(time.monotonic()-_LAST_SNAPSHOT)))
    _LAST_SNAPSHOT=time.monotonic()
    def q(field):
        command=['timeout','10','nvidia-smi','-i',str(index),field,'--format=csv,noheader,nounits']
        try:
            return subprocess.check_output(command,text=True,timeout=12)
        except subprocess.TimeoutExpired as e:
            fatal('nvidia-smi timeout',str(e))
        except subprocess.CalledProcessError as e:
            fatal('nvidia-smi timeout' if e.returncode==124 else 'nvidia-smi failed',str(e))
    gpu=q('--query-gpu=uuid,name,driver_version,memory.used,utilization.gpu,pstate,power.draw,clocks.current.graphics,clocks.current.memory')
    apps=q('--query-compute-apps=pid,process_name,used_memory')
    row=[x.strip() for x in next(csv.reader([gpu.strip()]))]
    return {'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'index':index,'uuid':row[0],
            'gpu':gpu,'apps':apps,'idle':not apps.strip() and int(row[3])<=256 and int(row[4])==0}

class IdentityUnavailable(RuntimeError):pass

def proc_identity(pid):
    try:
        text=Path(f'/proc/{pid}/stat').read_text();fields=text[text.rfind(')')+2:].split()
        return int(fields[1]),int(fields[19])
    except OSError as error:
        if error.errno not in (2,3):raise IdentityUnavailable('unreadable process identity') from error
        try:fd=os.pidfd_open(pid,0)
        except ProcessLookupError:return None
        except (OSError,AttributeError) as missing:raise IdentityUnavailable('cannot establish process absence') from missing
        else:os.close(fd);raise IdentityUnavailable('live PID without readable identity')
    except (ValueError,IndexError) as error:raise IdentityUnavailable('malformed process identity') from error

def owned_pid(pid,group,known):
    current=proc_identity(pid)
    if pid in known:
        if current is None:return True
        if known[pid] is not None:return current[1]==known[pid]
    cursor=pid;born=current[1] if current else None
    for _ in range(64):
        identity=proc_identity(cursor)
        if identity is None:return False
        if cursor in known and known[cursor] is not None:
            if identity[1]!=known[cursor]:return False
            known[pid]=born;return True
        if identity[0]<=1:return False
        cursor=identity[0]
    return False

def foreign_apps(state,group,known):
    bad=[]
    for row in csv.reader(state['apps'].splitlines()):
        if not row:continue
        try:owned=owned_pid(int(row[0].strip()),group,known)
        except (ValueError,IdentityUnavailable):owned=False
        if not owned:bad.append(row)
    return bad

def remember_target(run,known):
    file=run/'result.pid'
    if file.exists():known.setdefault(int(file.read_text()),None)

def signal_owned(pid,sig,group,known):
    try:fd=os.pidfd_open(pid,0)
    except (ProcessLookupError,PermissionError):return False
    try:
        identity=proc_identity(pid)
        if identity and owned_pid(pid,group,known) and known[pid]==identity[1]:
            try:signal.pidfd_send_signal(fd,sig,None,0);return True
            except ProcessLookupError:return False
        return False
    except IdentityUnavailable:return False
    finally:os.close(fd)

def terminate_owned(p,known):
    # pidfd keeps the signal bound to the verified process across PID reuse.
    for pid in sorted(known,reverse=True):signal_owned(pid,signal.SIGTERM,p.pid,known)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        for pid in sorted(known,reverse=True):signal_owned(pid,signal.SIGKILL,p.pid,known)
        p.wait()

def acquire(root):
    ensure_launch_memory()
    # One admission pass only; fatal NVML errors are never swallowed or retried.
    for index in ELIGIBLE:
        try: handle=open(f'/tmp/gtspp_gpu{index}.lock','r')
        except (FileNotFoundError,PermissionError): continue
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close(); continue
        try:
            state=snapshot(index)
            # Zero applications with utilization only may be an NVML tail.
            if not state['idle'] and not state['apps'].strip():
                state=snapshot(index)
            if state['idle']: return index,state,handle
        except BaseException:
            handle.close(); raise
        handle.close()
    raise NoIdleGPU('no idle GPU in one admission pass; no task launched')


_SUBREAPER=False


def enable_subreaper():
    """Retain orphaned setsid descendants inside this serialized runner."""
    global _SUBREAPER
    if sys.platform != 'linux':
        raise RuntimeError('guarded process supervision requires Linux')
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0) != 0:
        raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER failed')
    enabled=ctypes.c_int()
    if libc.prctl(37,ctypes.byref(enabled),0,0,0) != 0 or enabled.value != 1:
        raise RuntimeError('child subreaper was not enabled')
    _SUBREAPER=True


def job_known():
    if not _SUBREAPER:
        raise RuntimeError('enable child subreaper before launching a guarded task')
    identity=proc_identity(os.getpid())
    if identity is None:
        raise IdentityUnavailable('runner identity unavailable')
    return {os.getpid():identity[1]}


def descendants(pid):
    seen,stack=set(),[pid]
    result=[]
    while stack:
        current=stack.pop()
        if current in seen:continue
        seen.add(current);result.append(current)
        try:
            tasks=os.listdir(f'/proc/{current}/task')
        except FileNotFoundError:continue
        except OSError as error:raise IdentityUnavailable('cannot inspect descendant tasks') from error
        for tid in tasks:
            try:
                children=Path(f'/proc/{current}/task/{tid}/children').read_text()
            except FileNotFoundError:continue
            except OSError as error:raise IdentityUnavailable('cannot inspect descendant children') from error
            stack.extend(int(child) for child in children.split())
    return result


def thread_states(pid,birth):
    identity=proc_identity(pid)
    if identity is None or identity[1] != birth:return []
    try:
        tasks=list(Path(f'/proc/{pid}/task').iterdir())
    except FileNotFoundError:return []
    except OSError as error:raise IdentityUnavailable('cannot inspect thread states') from error
    states=[]
    for task in tasks:
        try:
            text=(task/'stat').read_text()
        except FileNotFoundError:continue
        except OSError as error:raise IdentityUnavailable('cannot inspect thread state') from error
        states.append(text[text.rfind(')')+2:].split()[0])
    return states


def same_process(pid,known):
    identity=proc_identity(pid)
    return identity is not None and known.get(pid) == identity[1]


def freeze_owned(pid,group,known,deadline):
    identity=proc_identity(pid)
    if identity is None:return True
    if not owned_pid(pid,group,known):return False
    states=thread_states(pid,identity[1])
    if all(state in ('T','t','Z','X') for state in states):return True
    if not signal_owned(pid,signal.SIGSTOP,group,known):
        return not same_process(pid,known)
    while time.monotonic() < deadline:
        if all(state in ('T','t','Z','X') for state in thread_states(pid,identity[1])):
            return True
        time.sleep(.005)
    return False


def owned_children(p,known):
    # This process is dedicated to one serialized task; adopted orphans are owned.
    anchor=os.getpid() if os.getpid() in known else p.pid
    result=[]
    for pid in descendants(anchor):
        if pid == anchor:continue
        if owned_pid(pid,p.pid,known):result.append(pid)
        else:raise IdentityUnavailable('descendant ownership could not be proved')
    return result


def reap_adopted(p,known):
    for pid in list(known):
        if pid in (os.getpid(),p.pid):continue
        try:os.waitpid(pid,os.WNOHANG)
        except ChildProcessError:pass


def terminate_guarded(p,known,timeout=5):
    """Freeze the entire owned tree before killing; verify absence before unlock."""
    deadline=time.monotonic()+timeout
    try:
        # STOP, unlike KILL, preserves the watchdog and inherited lock descriptors.
        if p.poll() is None and not freeze_owned(p.pid,p.pid,known,deadline):return False
        previous=None
        while time.monotonic() < deadline:
            current=owned_children(p,known)
            for pid in current:
                if pid != p.pid and not freeze_owned(pid,p.pid,known,deadline):return False
            final=owned_children(p,known)
            if final == current and current == previous:break
            previous=current
        else:return False
        for pid in reversed(final):
            if pid == p.pid:continue
            if same_process(pid,known) and not signal_owned(pid,signal.SIGKILL,p.pid,known):return False
        # No fork can race this proof: every thread in every parent is stopped.
        children=[pid for pid in final if pid != p.pid]
        if p.poll() is None:
            if children:
                if not signal_owned(p.pid,signal.SIGCONT,p.pid,known):return False
            else:
                # Watchdog was frozen before its child existed, or has no work left.
                if not signal_owned(p.pid,signal.SIGKILL,p.pid,known):return False
        try:p.wait(timeout=max(.001,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:return False
        while time.monotonic() < deadline:
            reap_adopted(p,known)
            residual=owned_children(p,known)
            live=[pid for pid in known if pid != os.getpid() and same_process(pid,known)]
            if not residual and not live:return True
            time.sleep(.005)
        return False
    except BaseException:
        return False


def hold_failed_cleanup(p,known,receipt_path):
    """Unvalidated fail-closed quarantine; GPU admission must remain blocked."""
    # Attempt to resume the watchdog; failure still blocks production clearance.
    try:signal_owned(p.pid,signal.SIGCONT,p.pid,known)
    except BaseException:pass
    try:
        save(receipt_path,{'cleanup_complete':False,'action':'locks retained; manual intervention required',
                           'guard_pid':p.pid,'known':known})
    except BaseException:pass
    # This cannot be bounded safely with the unchanged outer killpg watchdog.
    # Never turn a logging/proc/interrupt exception into permission to unlock.
    while True:
        try:
            reap_adopted(p,known)
            if p.poll() is not None and not owned_children(p,known):
                if not any(same_process(pid,known) for pid in known if pid != os.getpid()):
                    return
            time.sleep(1)
        except BaseException:pass
