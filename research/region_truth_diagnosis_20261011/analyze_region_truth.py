#!/usr/bin/env python3
"""Exact frozen-tree oracle diagnosis. No CUDA calls and no latency promotion."""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
import struct
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'certified_navigation_20261010'
sys.path.insert(0, str(BASE))
from audit import load_index, sha, save

CLASSES = ['CURRENTLY_PRUNABLE', 'CERTIFICATE_FAILURE', 'PARTITION_FAILURE']
EPS = 1e-6


def require(condition, message):
    if not condition:
        raise ValueError(message)


def route(m1, m2, m3):
    a = m1 >= .30 and m1 >= 2 * m2
    b = m2 >= .50 or m3 >= .50
    if a and b:
        return 'INSUFFICIENT_EVIDENCE'
    if a:
        return 'CERTIFICATE_ROUTE'
    if b:
        return 'PARTITION_ROUTE'
    if .20 <= m1 <= .50 and .20 <= m2 <= .50:
        return 'MIXED_ROUTE'
    return 'INSUFFICIENT_EVIDENCE'


def classify(raw, truth_squared, kth_squared):
    u = math.sqrt(kth_squared)
    lb = np.maximum(0., np.nextafter(raw - EPS, -np.inf))
    truth = np.fromiter(map(math.sqrt, truth_squared), dtype=np.float64)
    a = raw > u + EPS
    c = truth_squared <= kth_squared
    require(np.array_equal(a, lb > u), 'native vs adjusted bound boundary mismatch')
    require(np.array_equal(c, truth <= u), 'squared vs sqrt truth boundary mismatch')
    require(not np.any(a & c), 'unsafe current prune overlaps region truth')
    require(np.all(lb <= truth), 'lower bound exceeds region truth')
    labels = np.where(a, 0, np.where(c, 2, 1)).astype(np.int8)
    return lb, truth, labels


def decode_bits(text, width):
    require(len(text) == (width + 3) // 4, 'bitset length')
    require(all(c in '0123456789abcdef' for c in text), 'bitset digits')
    if width % 4:
        require(int(text[-1], 16) >> (width % 4) == 0, 'bitset padding')
    return np.array([(int(text[i // 4], 16) >> (i % 4)) & 1
                     for i in range(width)], dtype=bool)


def bounds_and_replay(nodes, score, traces):
    count = len(nodes)
    parent = (np.arange(count) - 1) // 10
    raw = np.zeros(count)
    path = np.zeros(count)
    source = np.zeros(count, dtype=np.int32)
    active = np.zeros(count, dtype=bool)
    active[0] = True
    pivot_distance = np.zeros(count)
    start = 1
    for level, trace in enumerate(traces, 1):
        require(trace['level'] == level, 'trace level order')
        ix = np.arange(start, start + 10**level)
        p = parent[ix]
        if level >= 3:
            distance = np.fromiter((math.sqrt(score[nodes[i][0]]) for i in ix), dtype=np.float64)
            pivot_distance[ix] = distance
            low = np.array([nodes[i][1] for i in ix], dtype=np.float64)
            raw[ix] = np.maximum(low - .01 - (distance + EPS), 0.)
            finite = ix % 10 != 0
            hi = np.array([nodes[i+1][1] for i in ix[finite]], dtype=np.float64)
            raw[ix[finite]] = np.maximum(raw[ix[finite]], (distance[finite] - EPS) - (hi + .01))
            active[ix] = active[p] & (raw[ix] <= trace['upper'] + EPS)
        else:
            require(trace['upper'] is None, 'original query-reset skip policy changed')
            active[ix] = active[p]
        improve = raw[ix] > path[p]
        path[ix] = np.maximum(path[p], raw[ix])
        source[ix] = np.where(improve, ix, source[p])
        expected = decode_bits(trace['visit_bits_hex'], len(ix))
        require(np.array_equal(active[ix], expected), 'native replay differs at level ' + str(level))
        require(int(active[ix].sum()) == trace['visited'], 'trace visited count')
        start += 10**level
    return raw, path, source, active, pivot_distance


def scalar_score(query, row):
    total = 0.
    for x, y in zip(row, query):
        delta = float(x) - float(y)
        square = delta * delta
        total = total + square
    return total


def weights(labels, mask, sizes):
    return [int(sizes[mask & (labels == c)].sum()) for c in range(3)]


def read_oracle(path):
    b = path.read_bytes()
    n, d, q, k = struct.unpack_from('<4i', b)
    require((n, d, q, k) == (1000000, 960, 8, 8), 'oracle shape')
    require(len(b) == 16 + q*k*12, 'oracle length')
    ids = np.frombuffer(b, dtype='<i4', count=q*k, offset=16).reshape(q, k)
    scores = np.frombuffer(b, dtype='<f8', count=q*k, offset=16+q*k*4).reshape(q, k)
    return ids, scores


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    m = json.loads((HERE/'evidence/QUERY_MANIFEST.json').read_text())
    require(sha(a.index) == m['tree_sha256'], 'tree identity')
    require(sha(HERE/'region_truth8.qid') == m['query_sha256'], 'query identity')
    require(sha(HERE/'evidence/oracle8.bin') == m['oracle8_sha256'], 'oracle identity')
    source = json.loads((HERE/'evidence/SOURCE.json').read_text())
    scan = json.loads((a.run/'SCAN_RECEIPT.json').read_text())
    require(scan['exit_code'] == 0 and not scan['GPU_used'], 'CPU scan admission')
    require(scan['source_sha256'] == source['generated_sha256'], 'score source identity')
    for key in ['data_sha256', 'tree_sha256', 'query_sha256']:
        require(scan[key] == m[key], 'scan input identity ' + key)
    output_manifest = json.loads((a.run/'OUTPUT_MANIFEST.json').read_text())
    for name, expected in output_manifest.items():
        require(sha(a.run/name) == expected, 'scan output drift ' + name)
    require((a.run/'topk.bin').read_bytes() == (HERE/'evidence/oracle8.bin').read_bytes(), 'full top-K oracle bytes')
    old = json.loads((BASE/'evidence/e1_v7/SUMMARY.json').read_text())
    require(old['results']['G0']['geometry'] == dict(coverage_disabled_nodes=0, split_margin=.01, distance_envelope=EPS), 'native safe-bound policy')
    n, d, height, ids, nodes, flags = load_index(a.index)
    require((n, d, height) == (1000000, 960, 6) and not any(flags), 'tree shape')
    leaves = np.array([i for i, node in enumerate(nodes) if node[4]], dtype=np.int32)
    require(np.array_equal(leaves, np.arange(11111, 111111)), 'terminal node identity')
    sizes = np.array([nodes[i][2] for i in leaves], dtype=np.int32)
    require(np.all(sizes == 10), 'frozen terminal size')
    objects = np.array([ids[nodes[i][3]:nodes[i][3]+nodes[i][2]] for i in leaves], dtype=np.int32)
    with (a.run/'all_scores.bin').open('rb') as f:
        require(struct.unpack('<4i', f.read(16)) == (n, d, 8, 8), 'score shape')
    require((a.run/'all_scores.bin').stat().st_size == 16+8*n*8, 'score length')
    scores = np.memmap(a.run/'all_scores.bin', dtype='<f8', mode='r', offset=16, shape=(8,n))
    require(np.isfinite(scores).all() and (scores >= 0).all(), 'score domain')
    oracle_ids, oracle_scores = read_oracle(HERE/'evidence/oracle8.bin')
    traces = json.loads(gzip.decompress((HERE/'evidence/G0_trace8.json.gz').read_bytes()))
    require([t['query_id'] for t in traces] == m['queries'], 'trace query order')
    sample_manifest = json.loads((HERE/'evidence/SAMPLE_MANIFEST.json').read_text())
    vector_bytes = (a.run/'sample_vectors.bin').read_bytes()
    row_count, dim = struct.unpack_from('<2i', vector_bytes)
    require(dim == d and len(vector_bytes) == 8+row_count*4+row_count*d*4, 'validation vectors shape')
    row_ids = np.frombuffer(vector_bytes, dtype='<i4', offset=8, count=row_count)
    vectors = np.frombuffer(vector_bytes, dtype='<f4', offset=8+row_count*4).reshape(row_count,d)
    vmap = {int(row): vectors[i] for i, row in enumerate(row_ids)}
    require(len(vmap) == row_count, 'duplicate validation rows')
    samples_checked = []
    rows = []
    plots = []
    level_of = np.zeros(len(nodes), dtype=np.int32)
    start = 1
    for level in range(1, 6):
        level_of[start:start+10**level] = level
        start += 10**level
    headers = ['query_id','region_id','level','object_count','U_star','LB_GTS','LB_truth',
               'current_prunable','certificate_failure','partition_failure','gts_visited','object_weight',
               'truth_nearest_object_id','truth_nearest_distance','truth_min_squared','U_star_squared',
               'native_bound_source','native_bound_source_level','parent_region_id','pivot_id',
               'pivot_query_distance','region_low','region_high','native_leaf_bound','native_path_bound',
               'native_source_pivot_id','native_source_pivot_query_distance','classification']
    with (a.out/'region_truth.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for qi, qid in enumerate(m['queries']):
            score = scores[qi]
            rank = np.lexsort((np.arange(n), score))[:8]
            require(np.array_equal(rank, oracle_ids[qi]), 'exported score top-K IDs')
            require(score[rank].tobytes() == oracle_scores[qi].tobytes(), 'exported score top-K bits')
            kth = float(oracle_scores[qi,-1])
            u = math.sqrt(kth)
            require(u == m['selection'][qi]['U_star'], 'frozen independent U*')
            values = score[objects]
            truth_squared = values.min(axis=1)
            nearest = np.where(values == truth_squared[:,None], objects, n).min(axis=1)
            raw, path, src, active, distances = bounds_and_replay(nodes, score, traces[qi]['levels'])
            lb, truth, labels = classify(path[leaves], truth_squared, kth)
            visited = active[leaves]
            require(int(sizes[visited].sum()) == m['selection'][qi]['leaf_calls'], 'actual leaf work count')
            require(not np.any((labels != 0) & ~visited), 'fixed-U* survivor was not visited at looser native U')
            # Every sampled pair was fixed before score collection. Recompute all ten objects.
            for sample in sample_manifest['samples']:
                if sample['query_index'] != qi:
                    continue
                li = sample['region_id'] - 11111
                require(sample['query_id'] == qid and sample['object_ids'] == objects[li].tolist(), 'sample ownership')
                independent = [(scalar_score(vmap[qid], vmap[row]), row) for row in sample['object_ids']]
                for value, row in independent:
                    require(struct.pack('<d', value) == struct.pack('<d', score[row]), 'independent ordered scalar score mismatch')
                best = min(independent)
                require(best == (truth_squared[li], nearest[li]), 'independent region min/ID')
                samples_checked.append(dict(query_id=qid, region_id=sample['region_id'],
                    nearest_object_id=best[1], min_squared=best[0], min_distance=math.sqrt(best[0]),
                    score_hex=struct.pack('<d', best[0]).hex(), objects_checked=len(independent)))
            rc = np.bincount(labels, minlength=3).tolist()
            ow = weights(labels, np.ones(len(leaves),dtype=bool), sizes)
            vw = weights(labels, visited, sizes)
            total_visited = sum(vw)
            at_or_below = int((score <= kth).sum())
            ties = int((score == kth).sum())
            require(ow[2] <= 10*at_or_below, 'tie-aware perfect residual bound')
            m1, m2, m3 = vw[1]/total_visited, vw[2]/total_visited, ow[2]/n
            r = dict(query_id=qid, stratum=m['selection'][qi]['stratum'], U_star=u,
                U_final=m['selection'][qi]['U_final'], current_leaf_objects=total_visited,
                current_leaf_object_visit_fraction=total_visited/n,
                current_prunable_fraction=ow[0]/n, certificate_failure_fraction=ow[1]/n,
                partition_failure_fraction=ow[2]/n,
                perfect_certificate_prunable_object_fraction=(ow[0]+ow[1])/n,
                M1_visited_certificate_fraction=m1, M2_visited_partition_fraction=m2,
                M3_global_truth_residual_fraction=m3, visited_threshold_only_fraction=vw[0]/total_visited,
                objects_at_or_below_Ustar=at_or_below, objects_equal_Kth_score=ties,
                tie_aware_residual_upper_bound=10*at_or_below/n,
                leaf_only_vs_path_current_prunable_delta=int(((path[leaves]>u+EPS)&(raw[leaves]<=u+EPS)).sum()),
                decision=route(m1,m2,m3))
            for j, c in enumerate(CLASSES):
                r[c+'_regions'] = rc[j]
                r[c+'_objects'] = ow[j]
                r[c+'_visited_objects'] = vw[j]
            require(sum(rc) == len(leaves) and sum(ow) == n, 'classification partition')
            rows.append(r)
            np.savez_compressed(a.out/('query_'+str(qid)+'.npz'), LB_GTS=lb, LB_truth=truth,
                labels=labels, visited=visited, sizes=sizes, U_star=u)
            # Plot bins include all records, not a favorable scatter subsample.
            xedge = np.linspace(0., max(float(lb[visited].max()), u)*1.03, 71)
            yedge = np.linspace(0., float(truth[visited].max())*1.03, 71)
            h, _, _ = np.histogram2d(lb[visited], truth[visited], bins=(xedge,yedge))
            require(int(h.sum()) == int(visited.sum()), 'scatter density lost records')
            require(u > 0, 'ratio plots require nonzero U*; absolute-distance fallback needed')
            plots.append(dict(query_id=qid, U_star=u, visited_regions=int(visited.sum()),
                histogram=h.astype(int).tolist(), x_edges=xedge.tolist(), y_edges=yedge.tolist()))
            for j, nid in enumerate(leaves):
                sid = int(src[nid])
                writer.writerow([qid,int(nid),5,10,u,float(lb[j]),float(truth[j]),
                    int(labels[j]==0),int(labels[j]==1),int(labels[j]==2),int(visited[j]),10,
                    int(nearest[j]),float(truth[j]),float(truth_squared[j]),kth,sid,int(level_of[sid]),
                    int((nid-1)//10),nodes[nid][0],float(distances[nid]),nodes[nid][1],
                    nodes[nid+1][1] if nid%10 else 'inf',float(raw[nid]),float(path[nid]),
                    nodes[sid][0] if sid else '',float(distances[sid]) if sid else '',CLASSES[int(labels[j])]])
            print('PASS query', qid, 'M1/M2/M3', m1, m2, m3, flush=True)
    require(len(samples_checked) == sample_manifest['sample_count'] == 128, 'validation sample count')
    with (a.out/'per_query_summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    visited_total = sum(r['current_leaf_objects'] for r in rows)
    region_counts = [sum(r[c+'_regions'] for r in rows) for c in CLASSES]
    objects_total = 8*n
    object_counts = [sum(r[c+'_objects'] for r in rows) for c in CLASSES]
    visited_counts = [sum(r[c+'_visited_objects'] for r in rows) for c in CLASSES]
    m1, m2, m3 = visited_counts[1]/visited_total, visited_counts[2]/visited_total, object_counts[2]/objects_total
    summary = dict(query_count=8, query_region_rows=800000,
        scope='eight frozen stratified development queries, not population average or deployable performance',
        class_order=CLASSES, region_weighted=dict(counts=region_counts, denominator=800000,
            fractions=[x/800000 for x in region_counts]),
        object_weighted=dict(counts=object_counts, denominator=objects_total,
            fractions=[x/objects_total for x in object_counts]),
        visited_object_weighted=dict(counts=visited_counts, denominator=visited_total,
            fractions=[x/visited_total for x in visited_counts]),
        current_leaf_object_visit_fraction=visited_total/objects_total,
        current_prunable_fraction=object_counts[0]/objects_total,
        certificate_failure_fraction=object_counts[1]/objects_total,
        partition_failure_fraction=m3, perfect_certificate_residual_fraction=m3,
        M1_visited_certificate_fraction=m1, M2_visited_partition_fraction=m2,
        M3_global_truth_residual_fraction=m3, decision=route(m1,m2,m3),
        visited_threshold_only_fraction=visited_counts[0]/visited_total,
        threshold_only_saved_global_fraction=visited_counts[0]/objects_total,
        fixed_Ustar_current_bound_residual_fraction=(object_counts[1]+object_counts[2])/objects_total,
        per_query_decisions=[r['decision'] for r in rows],
        truth_residual_objects_per_query=[r['PARTITION_FAILURE_objects'] for r in rows],
        at_or_below_Ustar_objects_per_query=[r['objects_at_or_below_Ustar'] for r in rows],
        per_query_metrics={name:dict(mean=float(np.mean([r[name] for r in rows])),
            minimum=min(r[name] for r in rows), maximum=max(r[name] for r in rows)) for name in
            ['M1_visited_certificate_fraction','M2_visited_partition_fraction','M3_global_truth_residual_fraction']},
        no_inference_about_cheap_certificate_feasibility=True,
        terminal_size_variation=False, no_inference_about_upper_level_partition_quality=True)
    save(a.out/'aggregate_summary.json', summary)
    save(a.out/'VALIDATION.json', dict(status='PASS', oracle_full_bytes=True, topK_from_all_scores=True,
        exact_unique_terminal_ownership=True, replayed_queries=8, replayed_levels=40,
        replayed_node_bits=8*(10+100+1000+10000+100000), all_region_native_display_predicates_identical=True,
        all_region_squared_sqrt_predicates_identical=True, all_bounds_le_truth=True,
        classifications_exclusive_exhaustive=True, independent_scalar_pair_count=128,
        independent_scalar_distance_count=1280, independent_scalar_min_and_id_bitwise_equal=True,
        samples=samples_checked))
    save(a.out/'scatter_density.json', plots)
    save(a.out/'ANALYSIS_RECEIPT.json', dict(elapsed_seconds=time.monotonic()-started,
        python=sys.version.split()[0], numpy=np.__version__, source_sha256=sha(Path(__file__)),
        inputs={str(p.relative_to(HERE)):sha(p) for p in [HERE/'CONTRACT.yaml',
            HERE/'evidence/QUERY_MANIFEST.json',HERE/'evidence/SAMPLE_MANIFEST.json',
            HERE/'evidence/G0_trace8.json.gz',HERE/'evidence/oracle8.bin',HERE/'evidence/SOURCE.json']},
        prior_native_summary_sha256=sha(BASE/'evidence/e1_v7/SUMMARY.json'),
        tree_sha256=sha(a.index), scan_output_hashes=output_manifest,
        region_truth_csv_sha256=sha(a.out/'region_truth.csv'),
        scope='offline report generation, not deployable latency'))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
