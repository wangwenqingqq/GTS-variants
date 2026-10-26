"""Reuse campaign v4 locks/PID ownership; add mandatory v3 fail-stop boundaries."""
import csv, datetime, fcntl, hashlib, json, os, signal, subprocess, time
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


def descendants(pid):
    seen, stack = [], [pid]
    while stack:
        p = stack.pop()
        seen.append(p)
        try:
            for t in os.listdir(f"/proc/{p}/task"):
                with open(f"/proc/{p}/task/{t}/children") as f:
                    stack.extend(int(c) for c in f.read().split())
        except OSError:
            pass
    return seen


def terminate_guarded(p,known):
    """Keep the watchdog alive; freeze/kill only its verified owned subtree."""
    history=[]
    previous=None
    for _ in range(8):
        current=descendants(p.pid)[1:]
        for pid in current:
            identity=proc_identity(pid)
            if identity is not None and owned_pid(pid,p.pid,known):
                signal_owned(pid,signal.SIGSTOP,p.pid,known)
        history=current
        if current==previous: break
        previous=current
    for pid in reversed(history):
        signal_owned(pid,signal.SIGKILL,p.pid,known)
    try:
        p.wait(timeout=5)
        return True
    except subprocess.TimeoutExpired:
        # Never kill the watchdog while its separate-session command may live.
        return False
