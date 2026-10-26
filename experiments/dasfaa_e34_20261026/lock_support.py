"""Task-local safety adaptation of repaired-vs-scan's PID-safe admission helpers."""
import csv
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

GUARD = Path(os.environ.get('GTSPP_GUARD', 'guard.py'))
ELIGIBLE = (6, 7, 0, 1, 2, 3, 4, 5)
POLL_SECONDS = 30
_logdir = None
_last_snapshot = None
_fatal_telemetry = None
_guard_module = None


class Contaminated(RuntimeError):
    pass


class SafetyStop(RuntimeError):
    pass


class IdentityUnavailable(RuntimeError):
    pass


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(p, value):
    with Path(p).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def configure(logdir):
    global _logdir
    _logdir = Path(logdir)
    _logdir.mkdir(parents=True, exist_ok=True)


def meminfo():
    return Path('/proc/meminfo').read_text()


def preflight():
    raw = meminfo()
    available = next(int(line.split()[1]) for line in raw.splitlines()
                     if line.startswith('MemAvailable:'))
    if available < 64 * 1024**2:
        raise SafetyStop('MemAvailable below 64 GiB; no process launched')
    return raw


def guarded_command(log, cmd, timeout=900):
    if not 0 < timeout <= 900:
        raise ValueError('per-process timeout must be in (0,900] seconds')
    return [sys.executable, str(GUARD), '--log', str(log),
            '--rss-max-gb', '16', '--mem-available-min-gb', '48',
            '--timeout-s', str(timeout), '--', *map(str, cmd)]


def guarded_run(log, cmd, timeout_s=900, **kwargs):
    preflight()
    result = subprocess.run(guarded_command(log, cmd, timeout=timeout_s), **kwargs)
    if result.returncode:
        raise SafetyStop(f'guarded process exited {result.returncode}: {cmd}')
    return result


def snapshot(index):
    global _last_snapshot, _fatal_telemetry
    if _fatal_telemetry is not None:
        raise SafetyStop(_fatal_telemetry)
    if _logdir is None:
        raise SafetyStop('telemetry log directory was not configured')
    stamp = _logdir / '.last_snapshot_monotonic'
    previous = float(stamp.read_text()) if stamp.exists() else _last_snapshot
    if previous is not None:
        elapsed = time.monotonic() - previous
        if elapsed < 0:
            raise SafetyStop('host monotonic clock reset; do not resume a prior boot epoch')
        time.sleep(max(0, POLL_SECONDS - elapsed))
    _last_snapshot = time.monotonic()
    stamp.write_text(str(_last_snapshot) + '\n')

    def query(field):
        log = _logdir / f'nvml_{time.time_ns()}_{index}.guard.jsonl'
        cmd = ['timeout', '10', 'nvidia-smi', '-i', str(index), field,
               '--format=csv,noheader,nounits']
        result = subprocess.run(guarded_command(log, cmd, timeout=20),
                                text=True, capture_output=True)
        if result.returncode:
            raise SafetyStop(f'NVML/guard exited {result.returncode}: {result.stderr}')
        return result.stdout

    try:
        preflight()
        gpu = query('--query-gpu=uuid,name,driver_version,memory.used,utilization.gpu,pstate,power.draw,clocks.current.graphics,clocks.current.memory')
        apps = query('--query-compute-apps=pid,process_name,used_memory')
        row = [x.strip() for x in next(csv.reader([gpu.strip()]))]
        return {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'index': index, 'uuid': row[0], 'gpu': gpu, 'apps': apps,
                'idle': not apps.strip() and int(row[3]) <= 256 and int(row[4]) == 0}
    except BaseException as error:
        # Read host memory before any other action after a telemetry failure.
        memory = meminfo()
        _fatal_telemetry = f'telemetry stopped: {type(error).__name__}: {error}'
        save(_logdir / f'NVML_STOP_{time.time_ns()}.json',
             {'reason': _fatal_telemetry, 'meminfo': memory})
        raise SafetyStop(_fatal_telemetry) from error


def proc_identity(pid):
    try:
        text = Path(f'/proc/{pid}/stat').read_text()
        fields = text[text.rfind(')') + 2:].split()
        return int(fields[1]), int(fields[19])
    except OSError as error:
        if error.errno not in (2, 3):
            raise IdentityUnavailable('unreadable process identity') from error
        try:
            fd = os.pidfd_open(pid, 0)
        except ProcessLookupError:
            return None
        except (OSError, AttributeError) as missing:
            raise IdentityUnavailable('cannot establish process absence') from missing
        else:
            os.close(fd)
            raise IdentityUnavailable('live PID without readable identity')
    except (ValueError, IndexError) as error:
        raise IdentityUnavailable('malformed process identity') from error


def owned_pid(pid, group, known):
    current = proc_identity(pid)
    if pid in known:
        if current is None:
            return True
        if known[pid] is not None:
            return current[1] == known[pid]
    cursor = pid
    born = current[1] if current else None
    for _ in range(64):
        identity = proc_identity(cursor)
        if identity is None:
            return False
        if cursor in known and known[cursor] is not None:
            if identity[1] != known[cursor]:
                return False
            known[pid] = born
            return True
        if identity[0] <= 1:
            return False
        cursor = identity[0]
    return False


def foreign_apps(state, group, known):
    bad = []
    for row in csv.reader(state['apps'].splitlines()):
        if not row:
            continue
        try:
            owned = owned_pid(int(row[0].strip()), group, known)
        except (ValueError, IdentityUnavailable):
            owned = False
        if not owned:
            bad.append(row)
    return bad


def stable_idle(index, seconds=90, group=None, known=None):
    history = []
    deadline = time.monotonic() + seconds
    stable = 0
    while True:
        state = snapshot(index)
        history.append(state)
        if state['apps'].strip() and (known is None or foreign_apps(state, group, known)):
            return state, history
        stable = stable + 1 if state['idle'] else 0
        if stable >= 3 or time.monotonic() >= deadline:
            return state, history
        # snapshot enforces the same >=30s cadence across admission and monitoring.


def acquire(root):
    while True:
        preflight()
        for index in ELIGIBLE:
            handle = open(f'/tmp/gtspp_gpu{index}.lock', 'r')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                state = snapshot(index)
                if state['idle']:
                    return index, state, handle
            except BaseException:
                handle.close()
                raise
            handle.close()
        print('WAIT no admissible idle card; no foreign processes signaled', flush=True)
        time.sleep(POLL_SECONDS)


def remember_target(run, known):
    file = run / 'result.pid'
    if file.exists():
        known.setdefault(int(file.read_text()), None)


def remember_descendants(pid, known):
    global _guard_module
    if _guard_module is None:
        spec = importlib.util.spec_from_file_location('gtspp_resource_guard', GUARD)
        _guard_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_guard_module)
    # Reuse guard's /proc traversal; do not shell out or infer ownership by name.
    for child in _guard_module.descendants(pid):
        if owned_pid(child, pid, known):
            identity = proc_identity(child)
            if identity:
                known[child] = identity[1]


def signal_owned(pid, sig, group, known):
    try:
        fd = os.pidfd_open(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    try:
        identity = proc_identity(pid)
        if identity and owned_pid(pid, group, known) and known[pid] == identity[1]:
            try:
                signal.pidfd_send_signal(fd, sig, None, 0)
                return True
            except ProcessLookupError:
                return False
        return False
    except IdentityUnavailable:
        return False
    finally:
        os.close(fd)


def terminate_owned(p, known):
    remember_descendants(p.pid, known)
    # Keep the watchdog alive until it reaps its separately sessioned child.
    # Unverified descendants must remain guarded, never orphaned by monitor death.
    targets = [pid for pid in known if pid != p.pid]
    for pid in targets:
        signal_owned(pid, signal.SIGTERM, p.pid, known)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    for pid in targets:
        signal_owned(pid, signal.SIGKILL, p.pid, known)
    p.wait(timeout=610)
