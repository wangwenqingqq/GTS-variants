"""Bind inherited guarded crossings and prepare fixed CPU-only sharing cases."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def write_cases(path, orders, contexts):
    b, z = orders.shape
    assert 1 <= b <= 8 and 1 <= z <= 30
    assert all(sorted(r.tolist()) == list(range(z)) for r in orders)
    with path.open('xb') as f:
        f.write(struct.pack('<8sIII', b'BQSI001\n', b, z, len(contexts)))
        f.write(np.asarray(orders, dtype=np.uint8).tobytes())
        for key, count in sorted(contexts.items()):
            assert count > 0 and key >> (5*b) == 0
            assert all((key >> (5*q)) & 31 <= z for q in range(b))
            f.write(struct.pack('<QI', key, count))


def prepare(raw, out):
    c = load(HERE/'CONTRACT.json')
    parent = HERE.parent/c['parent_artifact']
    manifest = parent/'evidence/RAW_MANIFEST.json'
    assert sha(manifest) == c['parent_raw_manifest_sha256']
    assert sha(parent/'CONTRACT.json') == c['parent_contract_sha256']
    identities = load(manifest)['files']
    source = load(raw/'RESULTS.json')
    assert source['complete'] and source['pairs'] == c['N']*c['queries'] and source['GPU_starts'] == 0
    assert source['contract_sha256'] == c['parent_contract_sha256']
    out.mkdir()
    n = c['N']
    assert n % 8 == 0
    depths = np.empty((32,n//8), np.uint8)
    orders, inputs, queries = [], {}, []
    for i, record in enumerate(source['records']):
        assert record['query_index'] == i and record['qid'] == c['qids'][i]
        assert record['N'] == n and record['full_score_bit_mismatches'] == record['safe_false_rejections'] == 0
        for kind in ('safe', 'order'):
            name = f'q{i:02}_{kind}.bin'
            f = raw/'raw'/name
            identity = dict(bytes=f.stat().st_size, sha256=sha(f))
            assert identity == identities[name] == record['raw'][name]
            inputs[name] = identity
        safe = np.fromfile(raw/'raw'/f'q{i:02}_safe.bin', '<u2')
        order = np.fromfile(raw/'raw'/f'q{i:02}_order.bin', '<i4')
        assert safe.shape == (n,) and np.all((safe >= 1) & (safe <= 960))
        assert np.bincount(safe,minlength=961).tolist() == record['histograms']['safe']
        assert order.shape == (960,) and sorted(order.tolist()) == list(range(960))
        zone = (order.reshape(30,32)[:,0]//32).astype(np.uint8)
        assert np.array_equal(order, (zone[:,None].astype(int)*32+np.arange(32)).reshape(-1))
        assert zone.tolist() == record['zone_ids']
        rounded = ((safe.astype(np.uint32)+31)//32).astype(np.uint8)
        depths[i] = rounded.reshape(-1,8).max(axis=1)
        orders.append(zone)
        queries.append(dict(query_index=i,qid=record['qid'],filter_dimension_operations=int(rounded.astype(np.uint64).sum())*32,
                            terminal_query_points=int((rounded == 30).sum()),
                            terminal_sectors=int((depths[i] == 30).sum()),depth_histogram=np.bincount(depths[i],minlength=31).tolist()))
    assert len(orders) == 32
    depths.tofile(out/'DEPTHS.bin')
    membership = list(range(32))
    random.Random(c['batch_seed']).shuffle(membership)
    batches = []
    for b in c['batch_sizes']:
        for start in range(0,32,b):
            group = membership[start:start+b]
            keys = np.zeros(n//8, np.uint64)
            for q, index in enumerate(group):
                keys |= depths[index].astype(np.uint64) << (5*q)
            values, freq = np.unique(keys,return_counts=True)
            contexts = {int(k):int(v) for k,v in zip(values,freq)}
            label = f'b{b}_g{start//b:02}'
            path = out/(label+'.bin')
            write_cases(path,np.asarray(orders)[group],contexts)
            batches.append(dict(label=label,B=b,query_indices=group,orders=[orders[q].tolist() for q in group],
                                contexts=len(contexts),sectors=n//8,input_sha256=sha(path),input_bytes=path.stat().st_size,
                                terminal_shared_sectors=int(np.any(depths[group] == 30,axis=0).sum()),
                                terminal_independent_sectors=sum(queries[q]['terminal_sectors'] for q in group),
                                filter_dimension_operations=sum(queries[q]['filter_dimension_operations'] for q in group),
                                terminal_query_points=sum(queries[q]['terminal_query_points'] for q in group)))
    result = dict(passed=True,contract_sha256=sha(HERE/'CONTRACT.json'),parent_results_sha256=sha(raw/'RESULTS.json'),
                  source_files=inputs,depths_sha256=sha(out/'DEPTHS.bin'),queries=queries,batches=batches,
                  membership=membership,all_inherited_pairs=32000000,new_distance_evaluations=0,GPU_starts=0)
    save(out/'PREPARE.json',result)
    print('PREPARE_PASS',len(batches),'fixed batches;0 GPU targets')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--parent-raw',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    prepare(a.parent_raw,a.out)
