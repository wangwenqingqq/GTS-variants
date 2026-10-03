#!/usr/bin/env python3
"""Prepare a separate full-ID diagnostic of pinned original GTS V2."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def once(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


def prepare(source, out):
    pins = json.loads((HERE / 'ORIGINAL_SOURCE_PINS.json').read_text())
    names = {k.removeprefix('GTS/'): v for k, v in pins['sha256'].items()
             if k.startswith('GTS/')}
    assert len(names) == 8
    for name, digest in names.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest, name
    out.mkdir(exist_ok=False)
    for directory in ('original', 'adapted'):
        for name in names:
            target = out / directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
    tree = out / 'adapted/include/tree.cuh'
    tree.write_text(once(tree.read_text(), '__managed__ int MAX_H = 3;',
                         '__managed__ int MAX_H = 6; // Capacity for one million rows.'))
    path = out / 'adapted/include/search_v2.cuh'
    s = path.read_text()
    s = once(s, 'float *res_dis;', 'int *diag_ids;\nfloat *diag_dist;\nfloat *res_dis;')
    signature = 'int cur_level, int nnum_up, float *res_dis, int k)'
    s = once(s, signature, signature[:-1] + ', TN *nodes, int *ids, int *full_ids, float *full_dist, int leaf_slots)')
    anchor = '\t\tres_dis[qid] = p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * (3 + MAX_SIZE) + idx];'
    s = once(s, anchor, anchor + '''
        // Extract the existing sorted positions; no second search or sorting.
        const int cap = size_list[cur_level] / (MAX_SIZE * 3 + 3);
        for (int rank = 0; rank < k; ++rank) {
            const int slot = s + rank - offset_p - cap * 3;
            int original_id = -1;
            float distance = INFI_DIS;
            if (slot >= 0 && slot < leaf_slots) {
                const int pos = int(p_list_k[s + rank]);
                if (pos >= 0 && pos < leaf_slots) {
                    const int nid = int(p_list_k[offset_p + cap + pos / MAX_SIZE]);
                    const TN node = nodes[nid];
                    const int did = pos % MAX_SIZE;
                    distance = float(p_list_k[offset_p + cap * (3 + MAX_SIZE) + pos]);
                    if (did < node.size && node.is_leaf && distance < INFI_DIS)
                        original_id = ids[node.lid + did];
                }
            }
            full_ids[qid * k + rank] = original_id;
            full_dist[qid * k + rank] = distance;
        }''')
    s = once(s, '\tCHECK(cudaMallocManaged((void **)&res_dis, qnum * sizeof(float)));',
             '\tCHECK(cudaMallocManaged((void **)&res_dis, qnum * sizeof(float)));\n'
             '\tCHECK(cudaMalloc((void **)&diag_ids, size_t(qnum) * k * sizeof(int)));\n'
             '\tCHECK(cudaMalloc((void **)&diag_dist, size_t(qnum) * k * sizeof(float)));')
    s = once(s, 'nnum_up, res_dis, k);',
             'nnum_up, res_dis, k, node_list, id_list, diag_ids, diag_dist, lnum * MAX_SIZE);')
    assert s.count('avail = avail / 2;') == 2
    s = s.replace('avail = avail / 2;', 'avail = 1024ULL * 1024 * 1024; // Frozen query workspace.')
    # Suppress console output within the timed query, not its control flow.
    s = s.replace('cout << "Searching..." << endl;', '// Timed console output disabled.')
    s = s.replace('printf("qnum_l_low: %d\\n", qnum_l_low);', '// Timed console output disabled.')
    path.write_text(s)
    diff = []
    hashes = {}
    for name in names:
        a, b = out / 'original' / name, out / 'adapted' / name
        hashes[name] = hashlib.sha256(b.read_bytes()).hexdigest()
        diff.extend(difflib.unified_diff(a.read_text().splitlines(True), b.read_text().splitlines(True),
                                       'original/' + name, 'adapted/' + name))
    (out / 'adaptation.patch').write_text(''.join(diff))
    (out / 'SOURCE_PINS.json').write_text(json.dumps({'upstream_commit': pins['commit'],
        'original': names, 'adapted': hashes}, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    prepare(a.source, a.out)
