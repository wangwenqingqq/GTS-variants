#!/usr/bin/env python3
"""Independent stdlib scalar gate; optional read-only NumPy proof-array audit."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent


def require(ok, message):
    if not ok: raise AssertionError(message)


def read(name):
    return json.loads((ROOT/name).read_text())


def sha(path):
    with Path(path).open('rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(8 << 20),b''): h.update(block)
    return h.hexdigest()


def quantile(values, p):
    values = sorted(values); rank = (len(values)-1)*p
    lo = int(rank); high = min(lo+1,len(values)-1)
    return values[lo]+(values[high]-values[lo])*(rank-lo)


def close(a,b):
    return math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-14)


def agate(o,b):
    return 'STRONG_HEADROOM' if 2*o<=b else ('WEAK_HEADROOM' if 5*o<=4*b else 'NO_COORDINATE_HEADROOM')


def cgate(c,b,p90):
    if 10*c<=7*b: return 'GO_PROOF_PER_BYTE_ROUTING' if p90<=Fraction(4,5) else 'UNCLASSIFIED'
    return 'CONDITIONAL' if 20*c<=17*b else 'NO_GO_PROOF_PER_BYTE_ROUTING'


def self_test():
    require(agate(50,100)=='STRONG_HEADROOM','A equality')
    require(agate(51,100)==agate(80,100)=='WEAK_HEADROOM','A gray region')
    require(agate(81,100)=='NO_COORDINATE_HEADROOM','A stop')
    require(cgate(70,100,Fraction(4,5))=='GO_PROOF_PER_BYTE_ROUTING','C equality')
    require(cgate(70,100,Fraction(81,100))=='UNCLASSIFIED','C p90 gap')
    require(cgate(71,100,0)==cgate(85,100,0)=='CONDITIONAL','C gray region')
    require(cgate(86,100,0)=='NO_GO_PROOF_PER_BYTE_ROUTING','C stop')


def scalars(repo):
    self_test()
    c = read('CONTRACT.json'); w = c['workload']; n = w['N']; ids = w['query_ids']
    for name,digest in c['parent_files'].items(): require(sha(repo/name)==digest,'parent differs: '+name)
    ar = read('evidence/A/QUERY_RESULTS.json'); aresult = read('evidence/A/RESULTS.json')
    require([r['query_id'] for r in ar]==ids and len(ar)==32,'A population incomplete')
    b0 = sum(r['B0']['survivors'] for r in ar); o1 = sum(r['O1']['survivors'] for r in ar)
    require(b0==c['baseline']['expected_total_survivors']==20932102,'B0 count differs')
    expected = c['baseline']['expected_queries']
    boundary = sum(r['oracle_numerical_boundary_pairs'] for r in ar)
    require(boundary==aresult['numerical_boundary_pairs']==0,'O1 ideal-bound classification unresolved')
    a = agate(o1,b0)
    require(a==aresult['gate'] and aresult['complete'] and aresult['pairs']==32*n,'A gate differs')
    for r,e in zip(ar,expected):
        require(r['B0']['survivors']==e['survivors'] and r['B0']['hits']==e['hits'],'B0 parent query differs')
        require(r['O1']['survivors']<=r['B0']['survivors'],'oracle lacks B0 dominance')
        require(r['full_distance_bit_mismatches']==0,'full distance bits differ')
    d = read('evidence/DECISION.json'); b_exists = (ROOT/'evidence/B').exists()
    require(b_exists==(a=='STRONG_HEADROOM'),'C1 execution does not follow gate')
    br = read('evidence/B/QUERY_RESULTS.json') if b_exists else []
    qr = read('analysis/QUERY_DISTRIBUTION.json')['queries']
    require([r['query_id'] for r in qr]==ids,'query distribution differs')
    b1 = read('baseline/B1_BIT4.json')
    prior = json.loads((repo/'artifacts/progressive_lossless_gate0_20261013/evidence/QUERY_RESULTS.json').read_text())
    require(not b1['remeasured'] and b1['source_bytes_per_object']==480,'historical-control scope differs')
    require([r['survivors'] for r in b1['queries']]==[r['stages'][0]['survivors'] for r in prior],'B1 control differs')
    methods = [('B0',ar,'baseline/B0_FIRST128.json'),('O1',ar,'oracle/O1_PAIR_TOP128.json')]
    if b_exists:
        require([r['query_id'] for r in br]==ids,'C1 population incomplete')
        total = sum(r['C1']['survivors'] for r in br)
        ratios = [Fraction(r['C1']['survivors'],e['survivors']) for r,e in zip(br,expected)]
        p90 = quantile(ratios,Fraction(9,10)); final = cgate(total,b0,p90)
        require(final==d['Gate5B']==read('evidence/B/RESULTS.json')['gate'],'C1 gate differs')
        require(close(float(p90),d['C1_query_p90']) and close(total/b0,d['C1_ratio']),'C1 estimator differs')
        for method,values in [('C1_over_B0',ratios),('O1_over_B0',[Fraction(r['O1']['survivors'],e['survivors']) for r,e in zip(ar,expected)])]:
            reported=read('analysis/QUERY_DISTRIBUTION.json')['ratio_distributions'][method]
            require(reported['count']==32,'ratio population differs')
            for label,p in [('min',0),('p10',Fraction(1,10)),('median',Fraction(1,2)),('p90',Fraction(9,10)),('max',1)]:
                require(close(reported[label],float(quantile(values,p))),'ratio quantile differs: '+method+'/'+label)
        methods.append(('C1',br,'routing/C1_MOMENT_SCORE.json'))
        for r in br: require(r['C1']['hits']==expected[r['query_index']]['hits'],'C1 true-hit count differs')
        selections = read('routing/SELECTIONS.json'); require([r['query_id'] for r in selections]==ids,'routing queries differ')
        sets = []
        for s in selections:
            dims = s['scan_dimensions']; ranked = s['ranked_dimensions']
            require(len(dims)==len(set(dims))==128 and dims==sorted(dims),'invalid selected dimensions')
            require(min(dims)>=0 and max(dims)<w['D'] and set(dims)==set(ranked),'ranked/scan ownership differs')
            sets.append(set(dims))
        overlap = read('analysis/OVERLAP.json')
        actual = [len(sets[i]&sets[j]) for i in range(32) for j in range(i+1,32)]
        require(actual==[r['intersection'] for r in overlap['query_pairs']] and len(actual)==496,'overlap differs')
        require(overlap['unique_selected_sets']==len({tuple(sorted(s)) for s in sets}),'set diversity differs')
        stats = read('routing/DATASET_STATS.json')
        raw = struct.pack('<1920f',*(stats['mean']+stats['variance']))
        require(len(raw)==stats['metadata_bytes']==7680 and hashlib.sha256(raw).hexdigest()==stats['sha256'],'moment metadata differs')
        require(stats['population_rows']==n and stats['ddof']==0,'moment population differs')
    else:
        final=a; require(d['Gate5B']=='NOT_RUN','unadmitted C1 reported')
    for name,rows,file in methods:
        m = read(file); count = sum(r[name]['survivors'] for r in rows)
        require(m['source_bytes_per_object']==512,'selected source budget differs: '+name)
        require(m['total_survivors']==count and m['mean_survivors']==count/32,'aggregate differs: '+name)
        require(close(m['reject_fraction'],1-count/(32*n)),'reject fraction differs: '+name)
        require(close(m['proof_yield_per_decimal_MB'],(32*n-count)/(32*n*512/1e6)),'proof denominator differs: '+name)
        for i,r in enumerate(rows):
            v=r[name]
            require(v['pairs']==n and v['hits']<=v['survivors']<=n,'pair count invalid')
            require(v['false_rejections']==v['unsafe_partial_bounds']==0,'exactness failed')
            require(qr[i][name]==v['survivors'],'per-query count differs: '+name)
    for label in ['A']+(['B'] if b_exists else []):
        reg = read('evidence/'+label+'/REGISTRATION.json')
        require(reg['contract_sha256']==sha(ROOT/'CONTRACT.json'),'contract not frozen')
        for name,digest in reg['source_sha256'].items(): require(sha(ROOT/name)==digest,'measurement source differs: '+name)
        closure = read('evidence/'+label+'/CLOSURE.json')
        require(closure['all_input_source_reference_hashes_unchanged'] and closure['query_count']==32,'closure incomplete')
        require(closure['population_processes']==1 and closure['CPU_workers']==4,'population budget differs')
        require(closure['GPU_starts']==closure['NCU_starts']==0,'GPU start detected')
        require(read('evidence/'+label+'/FIXTURES.json')['returncode']==0,'native fixtures failed')
        qual=read('evidence/'+label+'/QUALIFICATION.json')
        require(qual['passed'] and qual['pairs']==131072 and len(qual['queries'])==32,'qualification failed')
    if b_exists:
        require(read('evidence/A/BUILD.json')['binary_sha256']==read('evidence/B/BUILD.json')['binary_sha256'],'binary changed')
        require(read('evidence/A/START.json')['query_bytes_sha256']==read('evidence/B/START.json')['query_bytes_sha256'],'query values changed')
    q = read('quality/EXACTNESS.json')
    require(q['false_rejections']==q['unsafe_partial_bounds']==q['A_full_score_bit_mismatches']==0,'quality summary differs')
    require(q['read_only_saved_partial_checks']==32*n*(3 if b_exists else 2),'proof-check population differs')
    require(d['Gate5A']==a and d['final_diagnostic_gate']==final and d['GPU']=='NOT_RUN','decision scope differs')
    require(d['routing_prior_art_audit']==('COMPLETED_NOT_DISTINCT_ENOUGH_TO_IMPLEMENT' if final=='GO_PROOF_PER_BYTE_ROUTING' else 'NOT_TRIGGERED'),'routing novelty gate unresolved')
    if final=='GO_PROOF_PER_BYTE_ROUTING':
        novelty=read('evidence/ROUTING_NOVELTY.json')
        for field,file in [('contract_sha256','CONTRACT.json'),('document_sha256','PRIOR_ART_ROUTING.md'),('source_identities_sha256','evidence/SOURCE_IDENTITIES.json')]:
            require(novelty[field]==sha(ROOT/file),'routing evidence differs: '+file)
        require(novelty['numerical_gate']==final and novelty['verdict']=='NOT_DISTINCT_ENOUGH_TO_IMPLEMENT','novelty decision differs')
        require(novelty['GPU_admission'] is False and novelty['manuscript_claim_admission'] is False,'unexpected promotion')
    if (ROOT/'PUBLICATION_SET.json').exists():
        m = read('PUBLICATION_SET.json')['files']
        for name,entry in m.items():
            p=ROOT/name; require(p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],'publication file differs: '+name)
        actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        require(actual==set(m)|{'PUBLICATION_SET.json'},'publication set differs')
    print(f'PASS: exact parents/sources, B0 parity, gated populations, {q["read_only_saved_partial_checks"]} saved partial checks, counts/ratios/budget/metadata, {final}, no GPU admission')


def raw_audit(a,b,cache):
    import numpy as np
    n=1000000; cutoff=float.fromhex(read('CONTRACT.json')['workload']['cutoff_hex'])
    ids=read('CONTRACT.json')['workload']['query_ids']; checked=0
    refs=read('evidence/A/REGISTRATION.json')['reference_hashes']
    for qid in ids:
        rp=cache/f'{qid}.f64'; require(sha(rp)==refs[rp.name],'private oracle differs')
        ref=np.memmap(rp,mode='r',dtype='<f8',shape=(n,))
        for label,work,names in [('A',a,['B0','O1']),('B',b,['C1'])]:
            if work is None: continue
            rows=read('evidence/'+label+'/QUERY_RESULTS.json')
            r=next(x for x in rows if x['query_id']==qid)
            manifest=read('evidence/'+label+'/RAW_MANIFEST.json')['files']
            for name in names:
                f=f'{qid}.{name}.f64'; p=work/'raw'/f
                require(p.stat().st_size==manifest[f]['bytes']==n*8 and sha(p)==manifest[f]['sha256'],'private proof differs')
                v=np.memmap(p,mode='r',dtype='<f8',shape=(n,))
                require(np.isfinite(v).all() and (v>=0).all() and (v<=ref).all(),'unsafe saved partial')
                require(not np.any((v>cutoff)&(ref<=cutoff)),'saved false rejection')
                require(int((v<=cutoff).sum())==r[name]['survivors'],'saved survivor count differs')
                checked+=n; v._mmap.close()
        ref._mmap.close()
    print(f'PASS: independent read-only raw audit, {checked} partials, no candidate rerun')


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--raw-a',type=Path); p.add_argument('--raw-b',type=Path); p.add_argument('--cache',type=Path)
    a=p.parse_args(); scalars(a.repo.resolve())
    if a.raw_a:
        require(a.cache is not None,'cache required for raw audit')
        raw_audit(a.raw_a,a.raw_b,a.cache)
