"""Independent stable-sort enumeration and scalar conservative bound reference."""
import math
import numpy as np


def proposals(z, ids, depth):
    ids = np.sort(ids)
    coords = z[ids]
    axes = sorted(range(8), key=lambda j: (-float(max(coords[:, j]) - min(coords[:, j])), j))
    def axis_order(dim):
        return ids[np.argsort(coords[:, dim], kind='stable')]
    result = [axis_order(axes[0])] + [axis_order(j) for j in range(8)] + [axis_order(depth % 8)]
    secondary = np.argsort(coords[:, axes[1]], kind='stable')
    primary = np.argsort(coords[secondary, axes[0]], kind='stable')
    result.append(ids[secondary[primary]])
    c = []
    for j in range(8):
        total = 0.
        for v in coords[:, j]:
            total = total + float(v)
        c.append(total / len(ids))
    radius = np.zeros(len(ids))
    for j in range(8):
        delta = coords[:, j] - c[j]
        radius = radius + delta * delta
    result.append(ids[np.argsort(radius, kind='stable')])
    return result


def down(v): return math.nextafter(v, -math.inf)
def up(v): return math.nextafter(v, math.inf)


def endpoint(value, upper):
    expanded = up(value + 1e-8) if upper else down(value - 1e-8)
    stored = np.float32(expanded)
    if (upper and float(stored) < expanded) or (not upper and float(stored) > expanded):
        stored = np.nextafter(stored, np.float32(math.inf if upper else -math.inf))
    return float(stored)


def bound(low, high, query):
    total = 0.
    for j in range(8):
        gap = max(0., down(low[j] - up(float(query[j]) + 1e-8)),
                  down(down(float(query[j]) - 1e-8) - high[j]))
        square = max(0., down(gap * gap))
        total = max(total, max(0., down(total + square)))
    return max(0., down(down(math.sqrt(total)) - 1e-4))


def enumerate_scores(z, ids, depth, queries, u):
    result = proposals(z, ids, depth); counts = []
    for ordering in result:
        boxes = []
        for child in ordering.reshape(10, -1):
            coords = z[child]
            low = [endpoint(float(min(coords[:, j])), False) for j in range(8)]
            high = [endpoint(float(max(coords[:, j])), True) for j in range(8)]
            boxes.append((low, high))
        counts.append([sum(bound(lo, hi, q) > float(threshold) for lo, hi in boxes) * (len(ids) // 10)
                       for q, threshold in zip(queries, u)])
    return np.array(counts, dtype=np.int64), result
