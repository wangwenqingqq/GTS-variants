#!/usr/bin/env python3
"""Curate gated CPU counts and exactly specified diagnostics; never rerun search."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from run import distribution, gate_a, quality, read, require, save, sha

ROOT = Path(__file__).resolve().parent


def arrays(work, qid, name, manifest, n):
    file = f'{qid}.{name}.f64'; p = work/'raw'/file
    require(p.stat().st_size == n*8 == manifest[file]['bytes'] and
            sha(p) == manifest[file]['sha256'], 'raw proof identity differs: '+file)
    return np.memmap(p,mode='r',dtype='<f8',shape=(n,))


def aggregate(rows, name, n, source_bytes):
    total = sum(r[name]['survivors'] for r in rows)
    return {'status': 'MEASURED_CPU_CERTIFICATE_DIAGNOSTIC', 'query_count': len(rows),
            'pairs': n*len(rows), 'total_survivors': total, 'mean_survivors': total/len(rows),
            'reject_fraction': 1-total/(n*len(rows)), 'source_bytes_per_object': source_bytes,
            'proof_yield_per_decimal_MB': (n*len(rows)-total)/(n*len(rows)*source_bytes/1e6),
            'queries': [{'query_id': r['query_id'], **r[name]} for r in rows]}


def analyze(args):
    c = read(ROOT/'CONTRACT.json'); w = c['workload']; n = w['N']; cutoff = float.fromhex(w['cutoff_hex'])
    arows = read(args.stage_a/'QUERY_RESULTS.json'); ar = read(args.stage_a/'RESULTS.json')
    require(ar['complete'] and len(arows) == 32, 'Gate5A incomplete')
    require([r['query_id'] for r in arows] == w['query_ids'], 'Gate5A queries differ')
    b0total = sum(r['B0']['survivors'] for r in arows); o1total = sum(r['O1']['survivors'] for r in arows)
    require(b0total == 20932102 and o1total == ar['O1_total_survivors'], 'population scalar mismatch')
    agate = 'UNCLASSIFIED' if ar['numerical_boundary_pairs'] else gate_a(o1total,b0total)
    require(agate == ar['gate'], 'Gate5A decision differs')
    b = args.stage_b
    require((b is not None) == (agate == 'STRONG_HEADROOM'), 'gated C1 execution missing or unauthorized')
    brows = read(b/'QUERY_RESULTS.json') if b else []
    br = read(b/'RESULTS.json') if b else None
    if b:
        require(br['complete'] and [r['query_id'] for r in brows] == w['query_ids'], 'Gate5B incomplete')
    output = args.output.resolve(); output.mkdir()
    for name in ('CONTRACT.json','probe.cpp','run.py','test_probe.py','analyze.py','PRIOR_ART.md'):
        shutil.copy2(ROOT/name,output/name)
    b1 = read(ROOT/'baseline/B1_BIT4.json')
    save(output/'baseline/B1_BIT4.json',b1)
    receipts = ['REGISTRATION.json','INPUT_CHECK.json','BUILD.json','FIXTURES.json','QUALIFICATION.json',
                'START.json','QUERY_RESULTS.json','RAW_MANIFEST.json','RESULTS.json','CLOSURE.json']
    for label,work in [('A',args.stage_a),('B',b)]:
        if work:
            for name in receipts: save(output/'evidence'/label/name,read(work/name))
    baseline = aggregate(arows,'B0',n,512)
    baseline['exact_parent_count_parity'] = True
    oracle_record = aggregate(arows,'O1',n,512)
    oracle_record.update(ratio_to_B0=o1total/b0total, gate=agate,
                         deployable=False, actual_diagnostic_source_bytes_per_object=3840,
                         selector_cost_priced=False, numerical_boundary_pairs=ar['numerical_boundary_pairs'])
    save(output/'baseline/B0_FIRST128.json',baseline)
    save(output/'oracle/O1_PAIR_TOP128.json',oracle_record)
    if b:
        candidate = aggregate(brows,'C1',n,512)
        candidate.update(ratio_to_B0=br['ratio'], gate=br['gate'],
                         per_query_ratio_distribution=br['per_query_ratio_distribution'])
        save(output/'routing/C1_MOMENT_SCORE.json',candidate)
        stats = read(b/'DATASET_STATS.json'); selections = read(b/'ROUTING_SELECTIONS.json')
        save(output/'routing/DATASET_STATS.json',stats)
        save(output/'routing/SELECTIONS.json',selections)
    else:
        candidate = {'status': 'NOT_RUN', 'reason': 'Gate5A is not STRONG_HEADROOM'}
        save(output/'routing/C1_MOMENT_SCORE.json',candidate)
        save(output/'routing/DATASET_STATS.json',candidate)
    qrows = []
    for i,r in enumerate(arows):
        row = {'query_index': i, 'query_id': r['query_id'], 'B0': r['B0']['survivors'],
               'B1': b1['queries'][i]['survivors'], 'O1': r['O1']['survivors'],
               'O1_over_B0': r['O1']['survivors']/r['B0']['survivors']}
        if b:
            row['C1'] = brows[i]['C1']['survivors']; row['C1_over_B0'] = row['C1']/row['B0']
        qrows.append(row)
    ratios = {'O1_over_B0': distribution([r['O1_over_B0'] for r in qrows])}
    if b: ratios['C1_over_B0'] = distribution([r['C1_over_B0'] for r in qrows])
    save(output/'analysis/QUERY_DISTRIBUTION.json', {'quantiles': 'linear; equal query weight',
                                                  'queries': qrows, 'ratio_distributions': ratios})
    if b:
        sets = [set(s['scan_dimensions']) for s in selections]
        overlap = []
        for i in range(32):
            require(len(sets[i]) == 128, 'invalid selected subset')
            for j in range(i+1,32):
                size = len(sets[i]&sets[j])
                overlap.append({'query_i': w['query_ids'][i], 'query_j': w['query_ids'][j],
                                'intersection': size, 'fraction_of128': size/128,
                                'Jaccard': size/(256-size)})
        save(output/'analysis/OVERLAP.json', {'query_pairs': overlap, 'pair_count': len(overlap),
                                            'unique_selected_sets': len({tuple(sorted(s)) for s in sets}),
                                            'intersection_distribution': distribution([r['intersection'] for r in overlap]),
                                            'fraction_distribution': distribution([r['fraction_of128'] for r in overlap]),
                                            'Jaccard_distribution': distribution([r['Jaccard'] for r in overlap]),
                                            'B0_overlap_per_query': [len(s&set(range(128))) for s in sets]})
    else:
        save(output/'analysis/OVERLAP.json',candidate)
    manifests = {label: read(work/'RAW_MANIFEST.json')['files']
                 for label,work in [('A',args.stage_a),('B',b)] if work}
    identity = read(args.stage_a/'REGISTRATION.json')['reference_hashes']
    fractions = {'B0': [], **({'C1': []} if b else {})}
    margins = {name: {'nonhit_rejected': [], 'nonhit_survived': []} for name in fractions}
    concentration_rows = []; margin_rows = []; proof_checks = 0; zero_denominators = 0
    for i,qid in enumerate(w['query_ids']):
        refpath = args.cache/f'{qid}.f64'
        require(sha(refpath) == identity[refpath.name], 'frozen reference differs')
        ref = np.memmap(refpath,mode='r',dtype='<f8',shape=(n,))
        positive = ref > 0; nonhit = ref > cutoff; zeros = int((~positive).sum())
        zero_denominators += zeros
        o1 = arrays(args.stage_a,qid,'O1',manifests['A'],n)
        require(quality(o1,ref,cutoff) == arows[i]['O1'], 'O1 saved proof differs')
        proof_checks += n; o1._mmap.close()
        cr = {'query_id': qid, 'excluded_zero_full_distances': zeros}; mr = {'query_id': qid}
        for name in fractions:
            part = arrays(args.stage_a if name=='B0' else b,qid,name,
                           manifests['A' if name=='B0' else 'B'],n)
            expected = arows[i]['B0'] if name=='B0' else brows[i]['C1']
            require(quality(part,ref,cutoff) == expected, name+' saved proof differs')
            proof_checks += n
            fraction = part[positive]/ref[positive]
            fractions[name].append(fraction); cr[name] = distribution(fraction)
            mr[name] = {}
            for group,mask in [('nonhit_rejected',nonhit&(part>cutoff)),
                               ('nonhit_survived',nonhit&(part<=cutoff))]:
                values = part[mask]/cutoff
                margins[name][group].append(values); mr[name][group] = distribution(values)
            part._mmap.close()
        ref._mmap.close(); concentration_rows.append(cr); margin_rows.append(mr)
    pooled_fraction = {name: distribution(np.concatenate(values)) for name,values in fractions.items()}
    pooled_margin = {name: {group: distribution(np.concatenate(values)) for group,values in groups.items()}
                     for name,groups in margins.items()}
    save(output/'analysis/CONTRIBUTION_CONCENTRATION.json', {'metric': 'ordered selected partial / ordered full score',
                                                          'excluded_zero_full_distances': zero_denominators,
                                                          'pooled': pooled_fraction, 'queries': concentration_rows,
                                                          'C1_status': 'MEASURED' if b else 'NOT_RUN'})
    save(output/'analysis/MARGIN.json', {'metric': 'partial / cutoff; only nonhits, grouped by strict certificate outcome',
                                       'pooled': pooled_margin, 'queries': margin_rows,
                                       'C1_status': 'MEASURED' if b else 'NOT_RUN'})
    save(output/'quality/EXACTNESS.json', {'A_pairs': 32000000, 'B_pairs': 32000000 if b else 0,
                                         'false_rejections': 0, 'unsafe_partial_bounds': 0,
                                         'A_full_score_bit_comparisons': 32000000,
                                         'A_full_score_bit_mismatches': 0,
                                         'read_only_saved_partial_checks': proof_checks,
                                         'exact_B0_parent_parity': True, 'oracle_numerical_boundary_pairs': ar['numerical_boundary_pairs'],
                                         'complete_search_result_claim': False})
    final = br['gate'] if b else agate
    prior_gate = 'REQUIRED' if final=='GO_PROOF_PER_BYTE_ROUTING' else 'NOT_TRIGGERED'
    if final=='GO_PROOF_PER_BYTE_ROUTING' and (ROOT/'evidence/ROUTING_NOVELTY.json').exists():
        novelty = read(ROOT/'evidence/ROUTING_NOVELTY.json')
        require(novelty['contract_sha256']==sha(ROOT/'CONTRACT.json') and
                novelty['verdict']=='NOT_DISTINCT_ENOUGH_TO_IMPLEMENT', 'routing audit does not match this contract')
        require(novelty['document_sha256']==sha(ROOT/'PRIOR_ART_ROUTING.md'), 'routing audit document differs')
        for name in ('PRIOR_ART_ROUTING.md','evidence/ROUTING_NOVELTY.json','evidence/SOURCE_IDENTITIES.json'):
            shutil.copy2(ROOT/name,output/name)
        prior_gate = 'COMPLETED_NOT_DISTINCT_ENOUGH_TO_IMPLEMENT'
    save(output/'evidence/DECISION.json', {'Gate5A': agate, 'Gate5B': br['gate'] if b else 'NOT_RUN',
                                        'final_diagnostic_gate': final, 'GPU': 'NOT_RUN',
                                        'routing_prior_art_audit': prior_gate,
                                        'C1_ratio': br['ratio'] if b else None,
                                        'C1_query_p90': br['per_query_ratio_distribution']['p90'] if b else None})
    save(output/'evidence/OFFLINE_AUDIT.json', {'passed': True, 'partial_checks': proof_checks,
                                             'hashes_and_all_saved_partials_against_frozen_scores': True,
                                             'candidate_search_rerun': False, 'new_GPU_starts': 0})
    save(output/'evidence/OBSERVATION_ORDER.json', {'Gate5A_query_ids': w['query_ids'],
                                                 'Gate5B_query_ids': w['query_ids'] if b else [],
                                                 'qualification_pairs_per_stage': 131072,
                                                 'performance_claim': False})
    print(json.dumps({'Gate5A': agate,'Gate5B': final if b else 'NOT_RUN',
                      'B0_mean': baseline['mean_survivors'],'O1_mean': oracle_record['mean_survivors'],
                      'C1_mean': candidate.get('mean_survivors'), 'proof_checks': proof_checks},indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('stage-a','cache','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage-b',type=Path)
    analyze(p.parse_args())
