"""Regenerate the qualified synthetic inputs; no external dataset is required."""
import hashlib
import random

import numpy as np

DATA_SHA = '3289dc170cfb98ebaba1f077db2a54fd6837ff13eafe9549c0ebdfee0439688d'
EVENT_SHA = 'b9f893d57d2a3617ec1798a4ccc42913c6c9ff4286c665e0612749ba6eee8ce8'
SEED = 2026100431


def data_bytes():
    rows = [list(b''.join(hashlib.sha256(f'gts-original-20260924:{i}:{j}'.encode()).digest()
                         for j in range(4))) for i in range(1000)]
    result = ('128 1000 2\n' + ''.join(' '.join(map(str, row)) + '\n' for row in rows)).encode()
    assert hashlib.sha256(result).hexdigest() == DATA_SHA
    return result


def full_operations():
    rng = random.Random(SEED)
    base = list(range(1000)); alive = [True] * 1000; buffer = []; ops = []

    def query():
        ops.append((2, rng.randrange(len(base))))

    def update(flag, index):
        nonlocal base, alive, buffer
        ops.append((flag, index))
        if flag == 0:
            buffer.append(base[index])
            if len(buffer) == 10:
                base = [v for v, keep in zip(base, alive) if keep] + buffer
                alive = [True] * len(base); buffer = []
        else:
            positions = [i for i, keep in enumerate(alive) if keep]
            if index < len(positions):
                alive[positions[index]] = False
            else:
                buffer.pop(index - len(positions))

    for cycle in range(100):
        for _ in range(10):
            query()
            if cycle % 2 == 0:
                update(1, rng.randrange(sum(alive))); query()
                update(0, rng.randrange(len(base))); query()
            else:
                update(0, rng.randrange(len(base))); query()
                update(1, sum(alive) + len(buffer) - 1); query()
        for _ in range(70):
            query()
        assert len(base) == sum(alive) == 1000 and not buffer
    assert [sum(f == kind for f, _ in ops) for kind in (0, 1, 2)] == [1000, 1000, 10000]
    return ops


def boundary_operations():
    return ([(2, 0), (0, 0), (2, 0), (0, 0), (1, 0), (2, 0),
             (1, 999), (2, 0), (1, 999), (2, 0)]
            + [(0, 0)] * 9 + [(2, 0), (0, 0), (2, 0), (1, 0), (2, 0)]
            + [(0, 1), (2, 1), (1, 1008), (2, 1)] + [(1, 0)] * 10
            + [(0, 0)] * 9 + [(2, 0), (0, 0), (2, 0)] + [(2, 999)] * 7)


def events_bytes(ops):
    return (str(len(ops)) + '\n' + ''.join(f'{f} {i}\n' for f, i in ops)).encode()


def generate(root):
    cases = {}
    for name, radius, operations in [('full', 0, full_operations()),
                                     ('boundary0', 0, boundary_operations()),
                                     ('boundary10000', 10000, boundary_operations())]:
        case = root / name; case.mkdir(parents=True, exist_ok=False)
        (case / 'data.txt').write_bytes(data_bytes())
        (case / 'events.txt').write_bytes(events_bytes(operations))
        if name == 'full':
            assert hashlib.sha256((case / 'events.txt').read_bytes()).hexdigest() == EVENT_SHA
        cases[name] = dict(radius=radius, operations=operations)
    return cases


def load_case(path):
    data = np.loadtxt(path / 'data.txt', skiprows=1, dtype=np.int64)
    ops = np.loadtxt(path / 'events.txt', skiprows=1, dtype=np.int64).tolist()
    assert data.shape == (1000, 128) and np.all((data >= 0) & (data <= 255))
    return data, ops
