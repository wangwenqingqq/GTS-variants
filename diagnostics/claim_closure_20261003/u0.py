#!/usr/bin/env python3
"""Bounded native GTS multiset probes; output observation, no benchmark framework."""
import argparse
import collections
import difflib
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def squared(a, b):
    return sum((x-y)**2 for x, y in zip(a, b))


def random_rows(n):
    return [list(b''.join(hashlib.sha256(f'gts-original-20260924:{i}:{j}'.encode()).digest()
                         for j in range(4))) for i in range(n)]


def oracle(rows, ops, radius):
    base = list(rows); alive = [True]*len(base); buf = []; answers = []; builds = [base]
    for step, (flag, idx) in enumerate(ops):
        live = [v for v, keep in zip(base, alive) if keep]+buf
        if flag == 0:
            assert 0 <= idx < len(base)
            buf.append(base[idx])
            if len(buf) == 10:
                base = [v for v, keep in zip(base, alive) if keep]+buf
                alive = [True]*len(base); buf = []; builds.append(base)
        elif flag == 1:
            assert 0 <= idx < len(live)
            positions = [i for i, keep in enumerate(alive) if keep]
            if idx < len(positions): alive[positions[idx]] = False
            else: buf.pop(idx-len(positions))
        else:
            assert flag == 2 and 0 <= idx < len(base)
            ids = [i for i, v in enumerate(live) if squared(base[idx], v) <= radius**2]
            distances = [f32(math.sqrt(squared(base[idx], live[i]))) for i in ids]
            answers.append({'step': step, 'qid': idx, 'tree_size': len(base), 'buffer': len(buf),
                            'ids': ids, 'distances': distances, 'active_size': len(live)})
    return answers, builds


RESULT_OBSERVATION = r'''
            printf("U0_RESULT {\"step\":%d,\"qid\":%d,\"tree_size\":%d,\"buffer\":%d,\"ids\":[", i, qid_list[0], tree_size, in_size);
            for (int u0j=0; u0j<total_result_num; ++u0j) printf("%s%d", u0j ? "," : "", total_result_id[u0j]);
            printf("],\"distances\":[");
            for (int u0j=0; u0j<total_result_num; ++u0j) printf("%s%.9g", u0j ? "," : "", total_result_dis[u0j]);
            printf("]}\n"); fflush(stdout);
'''

TREE_OBSERVATION = r'''
    std::vector<TN> u0nodes(max_node_num[0]);
    std::vector<int> u0empty(max_node_num[0]), u0order(data_info[1]);
    CHECK(cudaMemcpy(u0nodes.data(), node_list, u0nodes.size()*sizeof(TN), cudaMemcpyDeviceToHost));
    CHECK(cudaMemcpy(u0empty.data(), empty_list, u0empty.size()*sizeof(int), cudaMemcpyDeviceToHost));
    CHECK(cudaMemcpy(u0order.data(), id_list, u0order.size()*sizeof(int), cudaMemcpyDeviceToHost));
    int u0cover=0;
    printf("U0_TREE {\"n\":%d,\"height\":%d,\"nodes\":[", data_info[1], tree_h);
    bool u0first=true;
    for(int u0i=0; u0i<max_node_num[0]; ++u0i) if(!u0empty[u0i]) {
        TN u0n=u0nodes[u0i];
        if(u0n.is_leaf) { if(u0n.size<1 || u0n.size>MAX_SIZE) exit(91); u0cover+=u0n.size; }
        printf("%s[%d,%d,%.9g,%d,%d,%d]", u0first ? "" : ",", u0i,u0n.pid,u0n.min_dis,u0n.size,u0n.lid,u0n.is_leaf); u0first=false;
    }
    printf("],\"order\":[");
    for(int u0i=0;u0i<data_info[1];++u0i) printf("%s%d",u0i ? "," : "",u0order[u0i]);
    printf("]}\n"); fflush(stdout);
    if(u0cover!=data_info[1]) exit(91);
'''


def observe(source, out):
    shutil.copytree(source, out)
    targets = [('include/update.cuh', '\t\t\tfprintf(fcost, "%d ", total_result_num);', RESULT_OBSERVATION),
               ('include/tree.cuh', '\tprintf("Tree height: %d\\n", tree_h);', TREE_OBSERVATION)]
    for name, anchor, addition in targets:
        p = out/name; before = p.read_text(); assert before.count(anchor) == 1
        after = before.replace(anchor, addition+anchor)
        p.write_text(after)
        (out/(p.stem+'.observation.diff')).write_text(''.join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True), fromfile='original/'+name, tofile='observed/'+name)))


def prepare(source, root):
    pins = json.loads((HERE/'ORIGINAL_SOURCE.json').read_text())
    assert all(sha(source/name) == h for name, h in pins['files'].items())
    root.mkdir(exist_ok=False); shutil.copytree(source, root/'original')
    observe(root/'original', root/'observed')
    fixtures = root/'fixtures'; fixtures.mkdir(); cases = {}
    native = {
        'query_only': (0, [(2, 0)]*3), 'all_include': (10000, [(2, 0)]),
        'buffer_insert': (0, [(2, 0), (0, 0), (2, 0)]),
        'base_delete': (10000, [(2, 0), (1, 1), (2, 0)]),
        'buffer_delete': (0, [(0, 0), (2, 0), (1, 1000), (2, 0)]),
        'rebuild_no_prior_buffer_query': (0, [(0, 0)]*10+[(2, 0)]),
        'rebuild_after_buffer_query': (0, [(0, 0), (2, 0)]+[(0, 0)]*9+[(2, 0)]*2),
        'mixed_delete_rebuild': (10000, [(1, 1)]+[(0, 0)]*10+[(2, 0)]),
        'rebuild_then_delete': (0, [(0, 0)]*10+[(2, 0), (1, 1000), (2, 0)]),
        'zero_hit': (0, [(1, 0), (2, 0)]*1),
        'buffer_first_last_empty': (10000, [(0, 0), (0, 999), (2, 0), (1, 1000), (2, 0), (1, 1000), (2, 0)]),
        'threshold_each_prefix': (0, sum(([(0, 0), (2, 0)] for _ in range(11)), [])+[(2, 0)]*3),
        'rank_delete_twice': (10000, [(1, 1), (2, 0), (1, 1), (2, 0)]),
        'tombstone_pending_rebuild': (10000, [(1, 1), (1, 2), (0, 999), (2, 0)]+[(0, 3)]*9+[(2, 0)]*3),
        'far_buffer_then_rebuild': (0, [(2, 999)]+sum(([(0, 999), (2, 999)] for _ in range(10)), [])+[(2, 999)]*3),
    }
    axis = [[i-500]+[0]*127 for i in range(1000)]
    extra = {
        'tied_radius_boundary': (axis, 1, [(2, 500), (0, 499), (0, 501), (2, 500), (1, 1000), (2, 500)]),
        'leaf_capacity_20': (random_rows(2000), 10000, [(1, 0)]*10+sum(([(0, 1999), (2, 0)] for _ in range(11)), [])),
    }
    configs = {k: (random_rows(1000), r, ops) for k, (r, ops) in native.items()}; configs.update(extra)
    for name, (rows, radius, ops) in configs.items():
        data = fixtures/(name+'.data'); updates = fixtures/(name+'.updates')
        data.write_text(f'128 {len(rows)} 2\n'+''.join(' '.join(map(str, v))+'\n' for v in rows))
        updates.write_text(str(len(ops))+'\n'+''.join(f'{f} {i}\n' for f, i in ops))
        expected, builds = oracle(rows, ops, radius)
        assert all(len(b) <= 2000 for b in builds)
        cases[name] = {'n': len(rows), 'radius': radius, 'data_sha256': sha(data), 'updates_sha256': sha(updates),
                       'operations': ops, 'expected': expected, 'query_count': len(expected), 'builds': len(builds)}
    x = {'contract': 'U0_NATIVE_LOGICAL_MULTISET_20261003', 'upstream': pins,
         'observation_sha256': {name: sha(root/'observed'/name) for name in pins['files']},
         'harness_sha256': sha(Path(__file__)), 'cases': cases,
         'fresh_external_arrivals': 'not admitted: no native vector/stable-ID ingestion API',
         'timer': 'correctness only; observed process times are not performance samples',
         'build': 'nvcc -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo -Xnvlink=--ignore-host-info -Iobserved/include observed/src/main.cu -o bin/u0_original_obs'}
    (root/'manifest.json').write_text(json.dumps(x, indent=2)+'\n')
    for sub in ['bin', 'runs', 'logs']: (root/sub).mkdir()
    print('Frozen',len(cases),'cases;',sum(c['query_count'] for c in cases.values()),'full-output query checkpoints')


def repair(root):
    x = json.loads((root/'manifest.json').read_text()); source = root/'observed'; out = root/'repaired'
    assert all(sha(source/n) == h for n, h in x['observation_sha256'].items())
    shutil.copytree(source, out); p = out/'include/update.cuh'; before = p.read_text()
    anchor = '\t\t\tif (in_size > 0)\n'; assert before.count(anchor) == 1
    after = before.replace(anchor, '\t\t\trnum[0] = 0;\n'+anchor); p.write_text(after)
    (out/'rnum_reset.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                            fromfile='observed/include/update.cuh', tofile='repaired/include/update.cuh')))
    x['repaired_sha256'] = {n: sha(out/n) for n in x['upstream']['files']}
    (root/'manifest.json').write_text(json.dumps(x, indent=2)+'\n')


def tree_audit(tree, rows):
    assert tree['n'] == len(rows) and sorted(tree['order']) == list(range(len(rows)))
    nodes = {n[0]: n[1:] for n in tree['nodes']}; order = tree['order']; covered = []
    pair_checks = 0
    for idx, (pivot, lo, size, start, leaf) in nodes.items():
        assert 0 <= start < len(rows) and 0 < size <= len(rows)-start
        if leaf: assert size <= 20; covered.extend(range(start, start+size))
        if idx == 0: continue
        parent = nodes[(idx-1)//10]; assert parent[3] <= start and start+size <= parent[3]+parent[2]
        assert 0 <= pivot < len(rows)
        upper = nodes[idx+1][1] if idx % 10 and idx+1 in nodes else math.inf
        for pos in range(start, start+size):
            # Integer squared sums <=2^24 are exact in the original FP32 accumulation.
            d = f32(math.sqrt(squared(rows[pivot], rows[order[pos]])))
            assert f32(lo) <= d <= f32(upper), (idx, order[pos], lo, d, upper)
            pair_checks += 1
    assert sorted(covered) == list(range(len(rows)))
    return pair_checks


def check(root, case, log):
    manifest = json.loads((root/'manifest.json').read_text()); c = manifest['cases'][case]
    data = root/'fixtures'/(case+'.data'); assert sha(data) == c['data_sha256']
    assert sha(root/'fixtures'/(case+'.updates')) == c['updates_sha256']
    rows = [list(map(int, l.split())) for l in data.read_text().splitlines()[1:]]
    _, builds = oracle(rows, c['operations'], c['radius'])
    actual = []; trees = []; parse_errors = []
    for line in log.read_text(errors='replace').splitlines():
        for prefix, dest in [('U0_RESULT ', actual), ('U0_TREE ', trees)]:
            if line.startswith(prefix):
                try: dest.append(json.loads(line[len(prefix):]))
                except ValueError as e: parse_errors.append(str(e))
    failure = None; records = []; pairs = 0
    try:
        assert not parse_errors, parse_errors
        assert len(trees) == len(builds), 'missing tree observations'
        for tree, base in zip(trees, builds): pairs += tree_audit(tree, base)
        assert len(actual) == len(c['expected']), 'missing query outputs'
        for got, expected in zip(actual, c['expected']):
            ids = got['ids']; gold = expected['ids']; mapping = dict(zip(gold, expected['distances']))
            invalid = [i for i in ids if not 0 <= i < expected['active_size']]
            duplicates = sum(n-1 for n in collections.Counter(ids).values())
            fn = sorted(set(gold)-set(ids)); fp = sorted(set(ids)-set(gold))
            fields = len(ids) == len(got['distances']) and all(math.isfinite(d) and d >= 0 and
                i in mapping and abs(d-mapping[i]) <= 1e-5*max(1,mapping[i]) for i,d in zip(ids,got['distances']))
            state = all(got[k] == expected[k] for k in ['step','qid','tree_size','buffer'])
            record = {'step': expected['step'], 'expected_count': len(gold), 'actual_count': len(ids),
                      'invalid_ids': invalid, 'duplicate_ids': duplicates, 'FN': fn, 'FP': fp,
                      'fields_pass': fields, 'state_pass': state}
            records.append(record)
            if invalid or duplicates or fn or fp or not fields or not state:
                failure = record; break
    except AssertionError as e: failure = {'observation_or_capacity_failure': str(e)}
    receipt = {'case': case, 'pass': failure is None, 'first_divergence': failure, 'queries_checked': len(records),
               'queries_expected': len(c['expected']), 'ancestor_member_checks': pairs,
               'ancestor_scope': 'All stored ancestor intervals cover their physical members under native FP32 norm at each build; unchanged tree covers delete-only prefixes; buffer is separately scanned. No general FP32 real-metric proof.',
               'output_records': records, 'stdout_sha256': sha(log), 'manifest_sha256': sha(root/'manifest.json')}
    (log.parent/'quality.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'output_records'}))
    return receipt['pass']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('prepare'); a.add_argument('source', type=Path); a.add_argument('root', type=Path)
    a = sub.add_parser('repair'); a.add_argument('root', type=Path)
    a = sub.add_parser('check'); a.add_argument('root', type=Path); a.add_argument('case'); a.add_argument('stdout', type=Path)
    args = p.parse_args()
    if args.action == 'prepare': prepare(args.source, args.root)
    elif args.action == 'repair': repair(args.root)
    else: raise SystemExit(0 if check(args.root, args.case, args.stdout) else 1)
