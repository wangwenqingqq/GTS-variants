"""Prepare approved query isolation and immutable E1 workload inputs, never results."""
import argparse
import datetime
import json
import struct
from pathlib import Path

import numpy as np
from audit_inputs import SPECS, capacity, load, rowkey, sha

SEED = 20261026
ANN_DATASETS = {'sift', 'gist', 'deep'}
RATIOS = ('4:4:2', '8:1:1', '1:8:1')


def save_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def isolated_indices(x, native_queries, name, query_count=1000,
                     exclude_ann_overlap=False, amendment=None):
    """Return source-row maps; feature duplicates of held-out queries all leave."""
    if name in ANN_DATASETS:
        query_rows = None
        queries = native_queries
        policy = 'native-independent-query'
    else:
        if len(x) < query_count:
            raise ValueError('corpus has fewer rows than requested held-out queries')
        query_rows = np.random.Generator(np.random.PCG64(SEED)).choice(
            len(x), query_count, replace=False).astype('<i8')
        queries = [x[int(i)] for i in query_rows]
        policy = 'corpus-PCG64-choice-without-replacement'
    keys = {rowkey(row) for row in queries}
    excluded = np.fromiter((i for i, row in enumerate(x) if rowkey(row) in keys),
                           dtype='<i8')
    if name in ANN_DATASETS and len(excluded):
        if not exclude_ann_overlap:
            return dict(status='input-contract-blocked', policy=policy,
                        query_rows=query_rows, excluded=excluded)
        if not amendment:
            raise ValueError('ANN corpus-overlap removal needs an amendment reference')
        policy += '-explicit-approved-corpus-exclusion'
    keep = np.ones(len(x), dtype=bool)
    keep[excluded] = False
    remaining = np.flatnonzero(keep).astype('<i8')
    permutation = np.random.Generator(np.random.PCG64(SEED)).permutation(len(remaining))
    remaining = remaining[permutation]
    na = len(remaining) // 10
    return dict(status='input-pass', policy=policy, query_rows=query_rows,
                excluded=excluded, arrival=remaining[:na], base=remaining[na:])


def skew_arrivals(name, x, arrival_rows, retained_rows, cluster_labels=None):
    """Sort arrivals only; the split itself never changes across arrival orders."""
    if name in ANN_DATASETS:
        if cluster_labels is None:
            raise ValueError('frozen full-corpus k-means(k=64) labels are required')
        labels = np.asarray(cluster_labels)
        if labels.shape != (len(x),) or not np.issubdtype(labels.dtype, np.integer):
            raise ValueError('cluster labels must be one integer per original corpus row')
        if not ((labels >= 0) & (labels < 64)).all():
            raise ValueError('cluster labels outside [0,64)')
        order = np.argsort(labels[arrival_rows], kind='stable')
    elif name == 'tloc':
        corpus = np.asarray(x)
        lo, hi = corpus.min(axis=0), corpus.max(axis=0)
        span = hi - lo
        cells = np.floor((np.asarray(x)[arrival_rows] - lo) /
                         np.where(span > 0, span, 1) * 64).astype(np.int64)
        cells = np.clip(cells, 0, 63)
        # Lexicographic coordinates are the specified row-major cell ordering.
        order = np.lexsort(tuple([np.arange(len(arrival_rows))] +
                                 [cells[:, j] for j in reversed(range(cells.shape[1]))]))
    elif name in ('word', 'protein'):
        order = sorted(range(len(arrival_rows)),
                       key=lambda i: (len(x[int(arrival_rows[i])]),
                                      x[int(arrival_rows[i])].encode('latin1'),
                                      int(arrival_rows[i])))
    elif name == 'chembl':
        counts = np.asarray(x)[arrival_rows].sum(axis=1)
        order = np.argsort(counts, kind='stable')
    else:
        raise ValueError('unsupported dataset: ' + name)
    return arrival_rows[order]


def make_trace(nb, na, nq, length, ratio, k, seed=SEED):
    """Exact ratios, fresh sequential stable IDs and uniform live-ID deletion."""
    feasible = capacity(nb + na, na, length, ratio, k)
    if feasible['reasons']:
        raise ValueError(','.join(feasible['reasons']))
    rng = np.random.Generator(np.random.PCG64(seed))
    counts = [feasible[key] for key in ('inserts', 'deletes', 'queries')]
    ops = np.repeat(np.arange(3), counts)
    rng.shuffle(ops)
    query_order = rng.permutation(nq)
    active = list(range(nb))
    events = []
    inserted = queried = snapshot = 0
    for seq, op in enumerate(ops):
        uid = off = qid = -1
        if op == 0:
            uid = nb + inserted
            off = inserted
            inserted += 1
            active.append(uid)
            snapshot += 1
        elif op == 1:
            if not active:
                raise ValueError('prefix_active_cardinality_empty')
            position = int(rng.integers(len(active)))
            uid = active[position]
            active[position] = active[-1]
            active.pop()
            snapshot += 1
        else:
            if len(active) < k:
                raise ValueError('prefix_active_cardinality_below_k')
            qid = int(query_order[queried % nq])
            queried += 1
        events.append(dict(seq=seq, op=('insert', 'delete', 'query')[op], id=uid,
                           vector_split='arrival' if op == 0 else ('query' if op == 2 else None),
                           vector_offset=off if op == 0 else qid, query_id=qid,
                           required_snapshot=snapshot, active_size=len(active)))
    assert inserted == counts[0] and queried == counts[2]
    return events


def write_rows(path, x, rows, metric, dim):
    """Bounded chunks avoid a second multi-GB GIST corpus allocation."""
    shape = (len(rows),) if metric == 6 else (len(rows), dim)
    out = np.lib.format.open_memmap(path, mode='w+', dtype='S109' if metric == 6 else '<f4',
                                   shape=shape)
    for start in range(0, len(rows), 1024):
        selected = rows[start:start + 1024]
        if metric == 6:
            block = [x[int(i)].encode('latin1') for i in selected]
            if any(b'\0' in row or len(row) > 108 for row in block):
                raise ValueError('edit payload must fit the existing 109-byte NUL-terminated format')
            out[start:start + len(selected)] = block
        else:
            block = np.asarray(x)[selected]
            if not np.isfinite(block).all() or (metric == 8 and not np.isin(block, [0, 1]).all()):
                raise ValueError('nonfinite or nonbinary feature')
            out[start:start + len(selected)] = block
    out.flush()
    del out


def write_workload(path, events, metadata):
    path.mkdir()
    with (path / 'events.jsonl').open('x') as stream:
        for event in events:
            stream.write(json.dumps(event) + '\n')
    packed = np.asarray([[('insert', 'delete', 'query').index(e['op']), e['id'],
                          e['vector_offset'], e['query_id'], e['required_snapshot']]
                         for e in events], dtype='<i4')
    with (path / 'events.bin').open('xb') as stream:
        stream.write(packed.tobytes())
    save_json(path / 'manifest.json', dict(metadata, schema=1,
              hashes={file: sha(path / file) for file in ('events.jsonl', 'events.bin')}))


def prepare_dataset(data_root, out, name, exclude_ann_overlap=False, amendment=None,
                    labels_path=None, lengths=(10000, 100000), query_count=1000):
    """Create a new directory only; blocked rows remain in the full matrix."""
    out.mkdir()
    x, q, _, dim = load(data_root, name)
    metric = SPECS[name][3]
    source, query_file = SPECS[name][:2]
    split = isolated_indices(x, q, name, query_count, exclude_ann_overlap, amendment)
    manifest = dict(schema=3, dataset=name, seed=SEED, source_rows=len(x), dim=dim,
                    metric=metric, query_policy=split['policy'], amendment_reference=amendment,
                    input_status=split['status'], excluded_corpus_rows=len(split['excluded']),
                    corpus=dict(file=source, sha256=sha(data_root / source)),
                    native_query_file=dict(file=query_file, sha256=sha(data_root / query_file)),
                    query_count=len(q) if name in ANN_DATASETS else query_count,
                    query_seed_sampling='NumPy PCG64 choice(replace=False); independent reset for split',
                    loads=[], before_insert_status='pending: calibration and trace contract not yet materialized')
    np.save(out / 'excluded_source_rows.npy', split['excluded'])
    if split['status'] != 'input-pass':
        manifest['loads'] = [dict(length=length, ratio=ratio, order=order, k=k,
                                  status='input-contract-blocked')
                             for length in lengths for ratio in RATIOS
                             for order in ('random', 'skew')
                             for k in ((8, 10) if metric == 2 else (8,))]
        manifest['hashes'] = {'excluded_source_rows.npy': sha(out / 'excluded_source_rows.npy')}
        save_json(out / 'manifest.json', manifest)
        return manifest
    nb, na = len(split['base']), len(split['arrival'])
    if nb + na > 10000000:
        raise ValueError('N exceeds the mandatory 10-million ceiling')
    if metric != 6 and (nb + na + 1) * dim > np.iinfo(np.int32).max:
        raise ValueError('flattened corpus addressing exceeds archival int32 indexing')
    manifest.update(N=nb + na, base_rows=nb, arrival_rows=na,
                    synthetic_or_replicated_arrivals=False,
                    stable_id_policy='base [0,nb), arrivals [nb,nb+na), no reuse; source IDs in row maps')
    for label in ('base', 'arrival'):
        np.save(out / (label + '_source_rows.npy'), split[label])
    query_rows = split['query_rows']
    if query_rows is None:
        query_rows = np.arange(len(q), dtype='<i8')
        query_source = q
    else:
        query_source = x
    np.save(out / 'query_source_rows.npy', query_rows)
    write_rows(out / 'base.npy', x, split['base'], metric, dim)
    write_rows(out / 'arrival_random.npy', x, split['arrival'], metric, dim)
    write_rows(out / 'query.npy', query_source, query_rows, metric, dim)
    skew_error = None
    labels = None
    if labels_path:
        provenance_path = labels_path.with_suffix(labels_path.suffix + '.manifest.json')
        provenance = json.loads(provenance_path.read_text())
        expected = dict(k=64, seed=SEED, corpus_sha256=manifest['corpus']['sha256'],
                        labels_sha256=sha(labels_path))
        if any(provenance.get(key) != value for key, value in expected.items()):
            raise ValueError('k-means label provenance does not match k, seed or source hashes')
        labels = np.load(labels_path, mmap_mode='r', allow_pickle=False)
        manifest['kmeans_labels'] = dict(file=str(labels_path), **expected,
                                         provenance=provenance,
                                         provenance_sha256=sha(provenance_path))
    try:
        skew_rows = skew_arrivals(name, x, split['arrival'],
                                  np.concatenate((split['base'], split['arrival'])), labels)
        np.save(out / 'arrival_skew_source_rows.npy', skew_rows)
        write_rows(out / 'arrival_skew.npy', x, skew_rows, metric, dim)
    except ValueError as exc:
        skew_error = str(exc)
    (out / 'loads').mkdir()
    for length in lengths:
        for ratio in RATIOS:
            for order in ('random', 'skew'):
                for k in ((8, 10) if metric == 2 else (8,)):
                    name_id = f'{length}_{ratio.replace(":", "")}_{order}_k{k}'
                    row = dict(id=name_id, length=length, ratio=ratio, order=order, k=k,
                               **capacity(nb + na, na, length, ratio, k))
                    if row['reasons']:
                        pass
                    elif order == 'skew' and skew_error:
                        row.update(status='preparation-blocked', reasons=[skew_error])
                    else:
                        try:
                            events = make_trace(nb, na, manifest['query_count'], length, ratio, k)
                            row['status'] = 'prepared-not-evaluated'
                            write_workload(out / 'loads' / name_id, events, row)
                        except ValueError as exc:
                            row.update(status='contract-infeasible', reasons=[str(exc)])
                    manifest['loads'].append(row)
    manifest['hashes'] = {str(path.relative_to(out)): sha(path)
                          for path in sorted(out.rglob('*')) if path.is_file()}
    save_json(out / 'manifest.json', manifest)
    return manifest


def materialize_case(dataset, load_id, destination):
    """Emit one legacy-format case on demand instead of duplicating every corpus."""
    manifest = json.loads((dataset / 'manifest.json').read_text())
    if manifest['input_status'] != 'input-pass':
        raise ValueError('cannot materialize an input-contract-blocked dataset')
    row = next(row for row in manifest['loads'] if row['id'] == load_id)
    if row['status'] != 'prepared-not-evaluated':
        raise ValueError('cannot materialize an unprepared/infeasible load')
    files = ['base.npy', 'arrival_' + row['order'] + '.npy', 'query.npy',
             'loads/' + load_id + '/events.bin']
    for file in files:
        if sha(dataset / file) != manifest['hashes'][file]:
            raise ValueError('immutable prepared input hash mismatch: ' + file)
    header = [manifest[key] for key in ('metric', 'dim', 'base_rows', 'arrival_rows', 'query_count')]
    header += [row['k'], row['length']]
    with destination.open('xb') as stream:
        stream.write(b'E1CASE1\0')
        stream.write(struct.pack('<7i', *header))
        for file in files[:3]:
            array = np.load(dataset / file, mmap_mode='r', allow_pickle=False)
            for first in range(0, len(array), 1024):
                stream.write(array[first:first + 1024].tobytes())
        with (dataset / files[3]).open('rb') as events:
            for block in iter(lambda: events.read(1 << 20), b''):
                stream.write(block)
    return dict(case_file=str(destination), sha256=sha(destination), load_id=load_id,
                prepared_manifest_sha256=sha(dataset / 'manifest.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--data-root', type=Path, required=True)
    prepare.add_argument('--out', type=Path, required=True)
    prepare.add_argument('--dataset', choices=SPECS, required=True)
    prepare.add_argument('--exclude-ann-corpus-overlap', action='store_true')
    prepare.add_argument('--amendment-reference')
    prepare.add_argument('--kmeans-labels', type=Path)
    case = commands.add_parser('case')
    case.add_argument('--prepared', type=Path, required=True)
    case.add_argument('--load-id', required=True)
    case.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare_dataset(args.data_root, args.out, args.dataset,
                                 args.exclude_ann_corpus_overlap, args.amendment_reference,
                                 args.kmeans_labels)
        summary = dict(dataset=result['dataset'], input_status=result['input_status'],
                       rows=result.get('N'), loads=len(result['loads']))
    else:
        summary = materialize_case(args.prepared, args.load_id, args.out)
        save_json(args.out.with_suffix(args.out.suffix + '.manifest.json'), summary)
    print(datetime.datetime.now(datetime.timezone.utc).isoformat(),
          json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
