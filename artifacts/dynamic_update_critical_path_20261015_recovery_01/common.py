"""Frozen shapes, process order and identities; imports do not initialize CUDA."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PARENT = HERE.parent/'dynamic_query_aware_exact_gpu_20261015'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


parent_protocol = module('immutable_dynamic_protocol', PARENT/'common.py')
MODES, requests, batches, ends = parent_protocol.MODES, parent_protocol.requests, parent_protocol.batches, parent_protocol.ends


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''): h.update(block)
    return h.hexdigest()


def load(path): return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as f: json.dump(value, f, indent=2); f.write('\n')


def jobs(stage):
    if stage == 'qualification':
        out = [dict(label=v+'_selftest', kind='selftest', variant=v) for v in ('PLAIN', 'MARKED')]
        out += [dict(label=v+'_'+t, kind='selftest', variant=v, tool=t) for v in ('PLAIN', 'MARKED') for t in ('memcheck', 'racecheck', 'synccheck')]
        out += [dict(label=f'PLAIN_{n}_{op}_{b}', kind='micro', variant='PLAIN', N=n, K=min(8192,n//2), op=op, batch=b, diagnostic=2)
                for n in (4096, 1000000) for op in ('I', 'D', 'R') for b in (1, 32, 512)]
        out += [dict(label=f'MARKED_full_{op}', kind='micro', variant='MARKED', N=1000000, K=8192, op=op, batch=512, diagnostic=2) for op in ('I', 'D', 'R')]
        assert len(out) == 29; return out
    if stage == 'primary':
        out = []
        cells = [(op, b) for op in ('I', 'D', 'R') for b in (1, 32, 512)]
        for r in range(1, 7):
            order = 'forward' if r % 2 else 'reverse'
            for op, b in (cells if r % 2 else cells[::-1]):
                variants = ['PLAIN', 'MARKED'] if op == 'R' and b in (1, 512) else ['PLAIN']
                for v in (variants if r % 2 else variants[::-1]):
                    out.append(dict(label=f'r{r}_{v}_{op}_{b}', kind='micro', variant=v, N=1000000, K=8192, op=op, batch=b, diagnostic=0, round=r, order=order))
            for mode in (('S1', 'S2_STALE') if r % 2 else ('S2_STALE', 'S1')):
                out.append(dict(label=f'r{r}_service_{mode}', kind='service', mode=mode, variant='PARENT', diagnostic=0, round=r, order=order))
            out.append(dict(label=f'r{r}_copy', kind='copy', variant='PLAIN', round=r, order=order))
        assert len(out) == 84; return out
    assert stage == 'timeline'
    out = [dict(label=f'trace_{op}_{b}', kind='micro', variant='MARKED', N=1000000, K=8192, op=op, batch=b, diagnostic=1, tool='nsys') for op in ('I', 'D', 'R') for b in (1, 32, 512)]
    out += [dict(label='trace_service', kind='service', variant='MARKED', mode='S2_STALE', diagnostic=3, tool='nsys'),
            dict(label='trace_copy', kind='copy', variant='MARKED', tool='nsys')]
    assert len(out) == 11; return out
