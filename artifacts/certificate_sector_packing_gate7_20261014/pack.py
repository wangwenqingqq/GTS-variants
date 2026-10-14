"""The single frozen PACK8 algorithm and moment-sector policy."""
import numpy as np


def train_ids(n, excluded):
    rng = np.random.Generator(np.random.PCG64(2026101401))
    seen = set(excluded); ids = []; draws = 0
    while len(ids) < 1024:
        j = int(rng.integers(0,n)); draws += 1
        if j not in seen: ids.append(j); seen.add(j)
    return ids, draws


def co_select(top):
    w = np.zeros((960,960),dtype='<u2')
    for ids in top:
        if len(ids)!=128 or len(set(map(int,ids)))!=128 or np.max(ids)>=960:
            raise ValueError('invalid training top128')
        w[np.ix_(ids,ids)] += 1
    return w


def greedy(w):
    degree = w.sum(axis=1,dtype=np.uint64)
    unassigned = np.ones(960,dtype=bool); pi = []
    while unassigned.any():
        pool = np.flatnonzero(unassigned)
        seed = int(pool[np.argmax(degree[pool])])
        group = [seed]; unassigned[seed] = False
        while len(group)<8:
            pool = np.flatnonzero(unassigned)
            affinity = w[np.ix_(pool,group)].sum(axis=1,dtype=np.uint64)
            ranked = np.lexsort((pool,-degree[pool].astype(np.int64),-affinity.astype(np.int64)))
            j = int(pool[ranked[0]]); group.append(j); unassigned[j] = False
        pi.extend(group)
    return np.asarray(pi,dtype='<u2')


def coordinate_scores(q,stats):
    scores = (q.astype(np.float64)-stats[0].astype(np.float64))**2+stats[1].astype(np.float64)
    if not np.isfinite(scores).all(): raise ValueError('invalid moment scores')
    return scores


def sector_selection(scores,pi):
    packed = scores[pi].reshape(120,8)
    groups = np.zeros(120,dtype='<f8')
    for h in range(8): groups += packed[:,h]
    ranked = np.argsort(-groups,kind='stable')[:16].astype('<u2')
    sectors = np.sort(ranked)
    return sectors, ranked, groups


def demand_quality(top,pi):
    bins = np.empty(960,dtype=np.int64); bins[pi] = np.arange(960)//8
    counts = np.bincount(bins[top],minlength=120)
    return int(np.sum(counts*(counts-1)//2))/8128
