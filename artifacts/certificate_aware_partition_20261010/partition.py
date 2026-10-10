#!/usr/bin/env python3
"""Query-independent partitions and conservative offline certificate evaluation."""
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'block_certificate_headroom_20261010'
sys.path.insert(0, str(BASE))
from run import sha, save, outside_repo, interval, radius_upper, rejected, raw, stats

if not __debug__:
    raise RuntimeError('Assertions are required')


def validate_partition(perm, starts, n, capacity):
    assert perm.dtype.kind in 'iu' and starts.dtype.kind in 'iu'
    assert len(perm) == n and np.array_equal(np.sort(perm), np.arange(n))
    assert len(starts) and starts[0] == 0
    sizes = np.diff(np.r_[starts, n])
    assert np.all((sizes > 0) & (sizes <= capacity))
    return sizes


def make_partition(norms, occurrence, tree, kind, capacity=256, balanced=False):
    """Only signatures, occurrence IDs and fixed tree order are admitted inputs."""
    p, n = norms.shape
    assert p == 4 and n > 0 and np.isfinite(norms).all()
    assert len(occurrence) == n and len(np.unique(occurrence)) == n
    assert kind in ('P0', 'P1', 'P2', 'P3') and 0 < capacity <= 256
    if kind == 'P0':
        perm = np.asarray(tree, dtype=np.int64).copy()
        starts = np.arange(0, n, capacity)
    elif kind == 'P1':
        perm = np.lexsort((occurrence, *norms[::-1]))
        starts = np.arange(0, n, capacity)
    else:
        global_span = np.ptp(norms, axis=1)
        leaves = []

        def visit(ids, budget=None):
            if (budget == 1) if balanced else (len(ids) <= capacity):
                leaves.append(ids)
                return
            span = np.ptp(norms[:, ids], axis=1)
            if kind == 'P3':
                span = np.divide(span, global_span, out=np.zeros_like(span), where=global_span > 0)
            j = int(np.argmax(span))
            ordered = ids[np.lexsort((occurrence[ids], norms[j, ids]))]
            left = budget // 2 if balanced else None
            cut = len(ids) * left // budget if balanced else len(ids) // 2
            visit(ordered[:cut], left)
            visit(ordered[cut:], budget - left if balanced else None)

        visit(np.arange(n), (n + capacity - 1) // capacity if balanced else None)
        starts = np.r_[0, np.cumsum([len(x) for x in leaves])[:-1]]
        perm = np.concatenate(leaves)
    validate_partition(perm, starts, n, capacity)
    return perm, starts


def block_stats(scores, perm, starts, d=960):
    norms = np.sqrt(scores)
    span = np.ptp(norms, axis=1)
    width = np.maximum.reduceat(norms[:, perm], starts, axis=1) - np.minimum.reduceat(norms[:, perm], starts, axis=1)
    normalized = np.divide(width, span[:, None], out=np.zeros_like(width), where=span[:, None] > 0)
    low, high = interval(scores, d)
    lo = np.minimum.reduceat(low[:, perm], starts, axis=1)
    hi = np.maximum.reduceat(high[:, perm], starts, axis=1)
    sizes = np.diff(np.r_[starts, len(perm)])
    summary = dict(total_blocks=len(starts), size=stats(sizes), imbalance=float(sizes.max()/sizes.mean()),
                   physical_occupancy=float(len(perm)/(256*len(starts))),
                   mean_normalized_width=stats(normalized.mean(axis=0)),
                   width_by_pivot=[stats(w) for w in width], normalized_width_by_pivot=[stats(w) for w in normalized],
                   global_span=span.tolist())
    return lo, hi, sizes, width, normalized, summary


def queries(scores, perm, starts, lo, hi, truth, qids, p, radius, d=960):
    sizes = np.diff(np.r_[starts, len(perm)])
    qlo, qhi = interval(scores[:p, qids], d)
    rows = []
    for qi, q in enumerate(qids):
        req = np.maximum.reduceat(truth[qi, perm], starts)
        keep = ~np.any(rejected(lo[:p], hi[:p], qlo[:, qi, None], qhi[:, qi, None], radius_upper(radius, d)), axis=0)
        false = int(np.count_nonzero(req & ~keep))
        assert false == 0, ('false prune', p, qi)
        nk, nr, nb = int(keep.sum()), int(req.sum()), len(starts)
        rows.append(dict(query=qi, qid=q, pivot_count=p, query_pivot_distance_count=p,
                         total_blocks=nb, surviving_blocks=nk, rejected_blocks=nb-nk,
                         surviving_block_fraction=nk/nb, false_prune_blocks=false,
                         oracle_required_blocks=nr, oracle_fraction=nr/nb, oracle_gap_blocks=nk-nr,
                         candidate_objects_in_surviving_blocks=int(sizes[keep].sum()),
                         surviving_object_fraction=float(sizes[keep].sum()/len(perm)),
                         surviving_physical_slots=256*nk, certificate_scalar_reads=2*p*nb,
                         certificate_metadata_bytes=16*p*nb))
    return rows


def query_summary(rows):
    keys = ['surviving_block_fraction', 'surviving_blocks', 'oracle_fraction', 'oracle_gap_blocks',
            'candidate_objects_in_surviving_blocks', 'surviving_object_fraction', 'false_prune_blocks']
    return {k: stats([r[k] for r in rows]) for k in keys}


def decide(summary):
    entries = {(r['snapshot'], r['strategy'], r['partition']): r for r in summary if r['pivot_count'] == 4}
    names = ('initial', 'first_rebuilt')
    assert len(entries) == 16
    values = lambda s, p: [entries[n, s, p]['statistics']['surviving_block_fraction']['mean'] for n in names]
    configs = [(s, p) for s in ('S0', 'S1') for p in ('P0', 'P1', 'P2', 'P3')]
    go = [[s, p] for s, p in configs if max(values(s, p)) <= .5]
    strong = [[s, p] for s, p in configs if max(values(s, p)) <= .35]
    aware = [(s, p) for s, p in configs if p != 'P0']
    best = {n: min(entries[n, s, p]['statistics']['surviving_block_fraction']['mean'] for s, p in aware) for n in names}
    conditional = [[s, p] for s, p in configs if .5 < max(values(s, p)) <= .65 and
                   all(entries[n, s, p]['statistics']['oracle_fraction']['mean'] <= .1 for n in names)]
    no_go = max(best.values()) > .7 and min(best.values()) > .5
    label = 'GO' if go else 'NO-GO_GLOBAL_PIVOT' if no_go else 'CONDITIONAL'
    reason = 'joint_GO' if go else 'optimistic_per_snapshot_envelope_failed' if no_go else 'specified_conditional_band' if conditional else 'uncovered_interval'
    top = min(aware, key=lambda x: (max(values(*x)), np.mean(values(*x)), *x))
    return dict(decision=label, reason=reason, GO=go, strong_GO=strong, conditional_supported=conditional,
                best_per_snapshot=best, top_one=list(top), top_one_survival=dict(zip(names, values(*top))),
                GPU_admitted_this_round=False, scope='Only the fixed global-pivot interval family, tested partitions, snapshots and queries; no general impossibility claim')


def bind_inputs(prior, verification, maintenance, references):
    contract = json.loads((HERE/'CONTRACT.json').read_text())
    assert sha(prior/'PROOF.json') == contract['prior_proof_sha256']
    assert sha(verification) == contract['prior_verification_sha256']
    proof = json.loads((prior/'PROOF.json').read_text())
    verified = json.loads(verification.read_text())
    assert proof['passed'] and verified['passed'] and verified['proof_sha256'] == sha(prior/'PROOF.json')
    files = {prior/'PROOF.json': sha(prior/'PROOF.json'), verification: sha(verification)}
    for name in contract['snapshots']:
        binding = proof['bindings'][name]
        assert binding['queries'] == contract['inputs'][name]['qids']
        for filename in [name+'_L3.npy'] + [name+'_'+s+'_scores.npy' for s in contract['strategies']]:
            files[prior/filename] = proof['raw_files'][filename]
        for suffix, key in [('occurrence', 'occurrence_sha256'), ('lineage', 'lineage_sha256')]:
            for label, digest in contract[key].items():
                files[maintenance/(label+'.'+suffix+'.npy')] = digest
        files[references/name/'REFERENCE.json'] = contract['inputs'][name]['reference_sha256']
        for q, digest in binding['reference_file_hashes'].items():
            files[references/name/(q+'.f64')] = digest
    files[maintenance/'PREPARED.json'] = contract['prepared_sha256']
    for path, digest in files.items():
        assert sha(path) == digest, ('input changed', path.name)
    return contract, proof, files


def source_hashes():
    own = [HERE/f for f in ('CONTRACT.json', 'partition.py', 'experiment.py', 'test_partition.py')]
    reused = [BASE/f for f in ('run.py', 'update.py', 'NUMERICS.md')]
    reused += [HERE.parent/'external_closure/pruning_value'/f for f in ('build.py', 'analyze.py')]
    return {str(p.relative_to(HERE.parent)): sha(p) for p in own+reused}
