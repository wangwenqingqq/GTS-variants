"""Task-local identities and deterministic request schedule; no CUDA initialization."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MODES = ('S0', 'S1', 'S2_STALE', 'S2_INC')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()


def load(p): return json.loads(Path(p).read_text())


def save(p, value):
    with Path(p).open('x') as f: json.dump(value, f, indent=2); f.write('\n')


def sources():
    c = load(HERE/'CONTRACT.json')
    own = {str(p.relative_to(REPO)): sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.cu', '.cpp', '.json', '.md')}
    return {**c['parents'], **own}


def ends(workload, n):
    if workload == 0: return [0, 4, 8, 12, 16]
    if workload == 1: return [0, 16, 32, 48, 64]
    assert workload == 2
    return [0, n//20, n//5, n*35//100, n//2]


def requests(workload, n):
    """Only queries, including warmups; mutation count identifies the live set."""
    out = [dict(phase=-1, slot=i, mutation=0) for i in range(8)]
    points = ends(workload, n)
    for phase in range(5):
        for slot in range(32):
            count = points[phase-1] + slot//2 + 1 if workload == 1 and phase else points[phase]
            out.append(dict(phase=phase, slot=slot, mutation=count))
    assert len(out) == 168
    return out


def batches(workload, n):
    points = ends(workload, n); before = 0; out = []
    for phase in range(5):
        while before < points[phase]:
            count = min(512 if workload == 2 else 1, points[phase]-before)
            out.append(dict(phase=phase, begin=before, count=count)); before += count
    return out


def expected_jobs(stage):
    if stage == 'qualification':
        out = [dict(label=m+'_selftest', mode=m, kind='selftest') for m in MODES]
        out += [dict(label=m+'_'+t, mode=m, kind='selftest', tool=t) for m in MODES for t in ('memcheck', 'racecheck', 'synccheck')]
        out += [dict(label=m+'_bounded', mode=m, workload=2, N=4096, diagnostic=2) for m in MODES]
        out += [dict(label=m+f'_W{w}', mode=m, workload=w, N=1000000, diagnostic=2) for w in range(3) for m in MODES]
        assert len(out) == 32
        return out
    if stage == 'primary':
        return [dict(label=f'W{w}_r{r}_{m}', mode=m, workload=w, N=1000000, diagnostic=0, round=r,
                     order='forward' if r % 2 else 'reverse') for w in range(3) for r in range(1, 7) for m in (MODES if r % 2 else MODES[::-1])]
    if stage == 'query_ncu':
        return [dict(label=m+f'_W{w}', mode=m, workload=w, N=1000000, diagnostic=1, tool='ncu') for w in range(3) for m in MODES]
    assert stage == 'maintenance_ncu'
    return [dict(label='S2_INC_W2_maintenance', mode='S2_INC', workload=2, N=1000000, diagnostic=3, tool='ncu')]
