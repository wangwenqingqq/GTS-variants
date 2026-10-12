"""Fixed PCA8 enclosing shapes with operation-wise outward interval arithmetic."""
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
from projection_math import ETA, RHO, endpoints, prefix_bounds, round32
if not __debug__:
    raise RuntimeError('Safety checks require Python without -O')
NAMES = ['AABB', 'CENTROID_BALL', 'MINIMAX_BALL', 'DIAGONAL_ELLIPSOID']
BYTES = [64, 48, 48, 80]
LEVELS = {3: 1000, 4: 100, 5: 10}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def check_freeze():
    pins=json.loads((HERE/'evidence/SOURCE_FREEZE.json').read_text())['files']
    for relative,expected in pins.items():
        assert sha(HERE.parent/relative)==expected,relative


def up(v):
    return np.nextafter(v, np.inf)


def down(v):
    return np.nextafter(v, -np.inf)


def positive_down(v):
    return np.maximum(0., down(v))


def squared(v):
    total = np.zeros(v.shape[:-1], dtype=np.float64)
    for j in range(8):
        total = total + v[..., j] * v[..., j]
    return total


def norm_upper(v):
    total = np.zeros(v.shape[:-1], dtype=np.float64)
    for j in range(8):
        total = up(total + up(v[..., j] * v[..., j]))
    return up(np.sqrt(total))


def norm_lower(v):
    total = np.zeros(v.shape[:-1], dtype=np.float64)
    for j in range(8):
        total = positive_down(total + positive_down(v[..., j] * v[..., j]))
    return positive_down(np.sqrt(total))


QUERY_ERROR = float(up(up(np.sqrt(8.)) * ETA))


def finish(distance):
    return positive_down(positive_down(distance - QUERY_ERROR) - RHO)


def construct(z):
    """z: regions x ascending-object-ID points x eight cached coordinates."""
    assert z.ndim == 3 and z.shape[-1] == 8 and np.isfinite(z).all()
    nr, size, _ = z.shape
    raw = np.empty((nr, 8))
    for j in range(8):
        raw[:, j] = np.add.accumulate(z[:, :, j], axis=1)[:, -1] / size
    center = raw.astype(np.float32).astype(np.float64)
    delta = up(up(np.abs(z - center[:, None])) + ETA)
    radius = round32(norm_upper(delta).max(1), True)
    best = raw.copy(); current = raw.copy()
    best_sq = squared(z - current[:, None]).max(1)
    for t in range(1, 65):
        distances = squared(z - current[:, None])
        ix = distances.argmax(1)
        current = current + (z[np.arange(nr), ix] - current) / (t + 1)
        maximum = squared(z - current[:, None]).max(1)
        improve = maximum < best_sq
        best[improve] = current[improve]; best_sq[improve] = maximum[improve]
    minimax = best.astype(np.float32).astype(np.float64)
    mdelta = up(up(np.abs(z - minimax[:, None])) + ETA)
    mradius = round32(norm_upper(mdelta).max(1), True)
    scale = round32(delta.max(1), True).astype(np.float64)
    assert np.all(scale > 0)
    normalized = up(delta / scale[:, None])
    factor = round32(norm_upper(normalized).max(1), True)
    assert np.all(norm_upper(delta) <= radius[:, None])
    assert np.all(norm_upper(mdelta) <= mradius[:, None])
    assert np.all(norm_upper(normalized) <= factor[:, None])
    low, high = endpoints(z.min(1), z.max(1))
    # RN cached-point diameter is a numerical quality proxy, not a certified radius lower bound.
    ix = squared(z - raw[:, None]).argmax(1)
    witnessed = np.sqrt(squared(z - z[np.arange(nr), ix][:, None]).max(1)) / 2
    distances = np.sqrt(squared(z - center[:, None]))
    stats = dict(aabb_diagonal=np.sqrt(squared(high.astype(float) - low.astype(float))),
                 centroid_radius=radius.astype(float), minimax_radius=mradius.astype(float),
                 mean_centroid_distance=distances.mean(1), p90_centroid_distance=np.quantile(distances, .9, axis=1),
                 max_centroid_distance=distances.max(1), witnessed_half_diameter_proxy=witnessed,
                 minimax_to_witnessed_proxy_ratio=mradius / np.maximum(witnessed, np.finfo(float).tiny),
                 ellipsoid_factor=factor.astype(float))
    for j in range(8):
        stats['ellipsoid_scale_' + str(j)] = scale[:, j]
    meta = dict(low=low, high=high, center=center.astype(np.float32), radius=radius,
                minimax=minimax.astype(np.float32), minimax_radius=mradius,
                scale=scale.astype(np.float32), factor=factor)
    return meta, stats


def ellipsoid_bound(center, scale, factor, q, return_lambda=False):
    c = center.astype(float); s = scale.astype(float); r = factor.astype(float)
    d = q - c; s2 = s * s
    inside = squared(d / s) <= r * r
    lo = np.zeros(len(c)); hi = np.sqrt(squared(s * d)) / r
    for _ in range(64):
        mid = (lo + hi) / 2
        value = squared(s * d / (s2 + mid[:, None]))
        outside = value > r * r
        lo = np.where(outside, mid, lo); hi = np.where(outside, hi, mid)
    lam = np.where(inside, 0., (lo + hi) / 2)
    assert np.isfinite(lam).all() and np.all(lam>=0) and np.all(s>0) and np.all(r>0)
    # Any nonnegative stored lambda yields a valid dual; solving accurately is not a safety premise.
    abslo = positive_down(np.abs(q - c))
    total = np.zeros(len(c))
    for j in range(8):
        numerator = positive_down(lam * positive_down(abslo[:, j] * abslo[:, j]))
        denom = up(up(s[:, j] * s[:, j]) + lam)
        term = positive_down(numerator / denom)
        total = positive_down(total + term)
    penalty = up(lam * up(r * r))
    dual = positive_down(total - penalty)
    bound = finish(positive_down(np.sqrt(dual)))
    return (bound, lam) if return_lambda else bound


def all_bounds(meta, q):
    result = [prefix_bounds(meta['low'], meta['high'], q)[8]]
    for ck, rk in [('center', 'radius'), ('minimax', 'minimax_radius')]:
        delta = positive_down(np.abs(q - meta[ck].astype(float)))
        distance = positive_down(norm_lower(delta) - meta[rk].astype(float))
        result.append(finish(distance))
    result.append(ellipsoid_bound(meta['center'], meta['scale'], meta['factor'], q))
    return np.array(result)


def pack(meta, shape):
    if shape == 'AABB':
        values = np.stack([meta['low'], meta['high']], axis=-1).reshape(-1, 16)
    elif shape == 'DIAGONAL_ELLIPSOID':
        values = np.column_stack([meta['center'], meta['scale'], meta['factor']])
    else:
        ck, rk = ('center', 'radius') if shape == 'CENTROID_BALL' else ('minimax', 'minimax_radius')
        values = np.column_stack([meta[ck], meta[rk]])
    logical = values.shape[1] * 4; aligned = BYTES[NAMES.index(shape)]
    records = np.zeros((len(values), aligned), dtype=np.uint8)
    records[:, :logical] = values.astype('<f4').view(np.uint8).reshape(len(values), logical)
    return records.tobytes()


def unpack(blob, shape):
    aligned = BYTES[NAMES.index(shape)]; n = len(blob) // aligned
    rec = np.frombuffer(blob, dtype=np.uint8).reshape(n, aligned)
    logical = {'AABB':64, 'CENTROID_BALL':36, 'MINIMAX_BALL':36, 'DIAGONAL_ELLIPSOID':68}[shape]
    assert not rec[:, logical:].any()
    v = rec[:, :logical].copy().view('<f4')
    if shape == 'AABB':
        return dict(low=v[:, 0::2], high=v[:, 1::2])
    if shape == 'DIAGONAL_ELLIPSOID':
        return dict(center=v[:, :8], scale=v[:, 8:16], factor=v[:, 16])
    ck, rk = ('center', 'radius') if shape == 'CENTROID_BALL' else ('minimax', 'minimax_radius')
    return {ck:v[:, :8], rk:v[:, 8]}


def decision(rows):
    by = {(r['shape'], r['level']):r for r in rows}
    def val(r, key):
        if key == 'worst':
            return min(Fraction(n, d) for n, d in zip(r['hard_query_pruned'], r['hard_query_truth_prunable']))
        pre = 'hard_' if key == 'hard' else ''
        return Fraction(r[pre+'pruned_objects'], r[pre+'truth_prunable_objects'])
    def gain(r, key='hard'):
        return val(r,key) - val(by['AABB',r['level']],key)
    new = [r for r in rows if r['shape'] != 'AABB']; ancestors = [r for r in new if r['level'] in (3,4)]
    strong = [r for r in ancestors if val(r,'hard') >= Fraction(3,5) and val(r,'all') >= Fraction(3,5)
              and val(r,'worst') >= Fraction(1,4) and r['aligned_bytes'] <= 64]
    signal = [r for r in ancestors if val(r,'hard') >= Fraction(9,20) and gain(r) >= Fraction(3,20) and gain(r,'worst') >= Fraction(1,10)]
    leaf = [r for r in new if r['level'] == 5 and gain(r) >= Fraction(3,20) and
            all(gain(by[r['shape'],l]) < Fraction(1,20) for l in (3,4))]
    kill = all(gain(r) < Fraction(1,20) for r in ancestors)
    result = ('CERTIFIED_REGION_GEOMETRY_SUPPORTED' if strong else 'REGION_SHAPE_SIGNAL' if signal else
              'LEAF_ONLY_SHAPE_GAIN' if leaf else 'PROJECTED_SHAPE_CERTIFICATE_KILLED' if kill else 'INSUFFICIENT_EVIDENCE')
    return dict(decision=result, strong_cells=[(r['shape'],r['level']) for r in strong],
                signal_cells=[(r['shape'],r['level']) for r in signal], leaf_cells=[(r['shape'],r['level']) for r in leaf],
                K1=kill, K2='not applicable: all frozen shapes <=80B; >128B prerequisite absent')
