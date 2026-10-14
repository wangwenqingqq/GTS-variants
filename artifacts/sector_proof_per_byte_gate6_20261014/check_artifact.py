#!/usr/bin/env python3
"""Independent stdlib scalar gates; optional read-only proof and selection audit."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent


def require(ok,message):
    if not ok:raise AssertionError(message)


def read(name):return json.loads((ROOT/name).read_text())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def quantile(v,p):
    v=sorted(v);rank=(len(v)-1)*p;lo=int(rank);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(rank-lo)


def close(a,b):return math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-14)


def agate(o,b):
    return 'STRONG_SECTOR_HEADROOM' if 2*o<=b else ('WEAK_SECTOR_HEADROOM' if 5*o<=4*b else 'NO_SECTOR_HEADROOM')


def bgate(f,b,p):
    if 5*f<=4*b:return 'GO_SECTOR_PROOF_PER_BYTE' if p<=Fraction(1,2) else 'UNCLASSIFIED'
    return 'CONDITIONAL_SECTOR_PROOF' if f<=b else 'NO_GO_SECTOR_PROOF'


def self_test():
    require(agate(50,100)=='STRONG_SECTOR_HEADROOM' and agate(80,100)=='WEAK_SECTOR_HEADROOM' and agate(81,100)=='NO_SECTOR_HEADROOM','A boundaries')
    require(bgate(80,100,Fraction(1,2))=='GO_SECTOR_PROOF_PER_BYTE','GO equality')
    require(bgate(80,100,Fraction(51,100))=='UNCLASSIFIED','uncovered robustness stop')
    require(bgate(81,100,0)==bgate(100,100,0)=='CONDITIONAL_SECTOR_PROOF' and bgate(101,100,0)=='NO_GO_SECTOR_PROOF','B byte boundaries')


def scalars(repo):
    self_test();c=read('CONTRACT.json');w=c['workload'];ids=w['query_ids'];n=w['N']
    for name,digest in c['parent_files'].items():require(sha(repo/name)==digest,'parent differs: '+name)
    parent=repo/'artifacts/proof_per_byte_512_gate5_20261013'
    old=json.loads((parent/'baseline/B0_FIRST128.json').read_text())
    rows=read('evidence/A/QUERY_RESULTS.json');ar=read('evidence/A/RESULTS.json')
    require([r['query_id'] for r in rows]==ids and len(rows)==32,'A incomplete')
    b0=sum(r['B0']['survivors'] for r in rows);o2=sum(r['O2']['survivors'] for r in rows)
    require(b0==c['baseline']['expected_total_survivors']==old['total_survivors']==20932102,'B0 count differs')
    old_o1=json.loads((parent/'oracle/O1_PAIR_TOP128.json').read_text())['queries']
    for r,e,o in zip(rows,old['queries'],old_o1):
        require(r['B0']['survivors']==e['survivors'] and r['B0']['hits']==e['hits'],'per-query parent differs')
        require(o['survivors']<=r['O2']['survivors']<=r['B0']['survivors'],'oracle subset-family count order differs')
        require(r['full_distance_bit_mismatches']==0,'full score differs')
    boundary=sum(r['oracle_numerical_boundary_pairs'] for r in rows)
    require(boundary==ar['numerical_boundary_pairs']==0,'ideal-oracle rounding unresolved')
    a=agate(o2,b0);require(ar['gate']==a and ar['complete'],'A gate differs')
    b_exists=(ROOT/'evidence/B').exists();require(b_exists==(a=='STRONG_SECTOR_HEADROOM'),'B not gated by A')
    d=read('evidence/DECISION.json');qr=read('analysis/QUERY_DISTRIBUTION.json')['queries']
    require([r['query_id'] for r in qr]==ids,'query order differs')
    methods=[('B0',rows,'baseline/B0_FIRST16_SECTORS.json'),('O2',rows,'oracle/O2_PAIR_TOP16_SECTORS.json')]
    c1=read('baseline/C1_SCATTERED_REFERENCE.json');old_c1=json.loads((parent/'routing/C1_MOMENT_SCORE.json').read_text())
    require(c1['remeasured'] is False and c1['sector_gate_eligible'] is False and c1['queries']==old_c1['queries'],'scattered reference scope differs')
    if b_exists:
        br=read('evidence/B/QUERY_RESULTS.json');require([r['query_id'] for r in br]==ids,'B incomplete')
        total=sum(r['S1']['survivors'] for r in br);ft=32*512000000+3328*total
        account=json.loads((repo/'artifacts/exact_representation_gate1_20261012/bytes/STAGE_ACCOUNTING.json').read_text())
        bt=sum(r['coordinate_bytes'] for r in account['rows'])
        require(Fraction(bt,32)==c['byte_model']['strong_baseline_mean_bytes']==1014828776,'strong byte baseline differs')
        ratios=[Fraction(r['S1']['survivors'],e['B0']['survivors']) for r,e in zip(br,rows)]
        p90=quantile(ratios,Fraction(9,10));final=bgate(ft,bt,p90)
        result=read('evidence/B/RESULTS.json');cost=read('cost/FULL_FALLBACK_BYTES.json');cand=read('routing/S1_SECTOR_MOMENT.json')
        require(final==result['gate']==cost['gate']==cand['gate']==d['Gate6B'],'B gate differs')
        require(ft==cost['total_bytes_all32']==result['fallback_total_bytes'] and ft/32==cost['mean_bytes'],'modeled byte total differs')
        require(bt==cost['strong_baseline_total_bytes_all32']==c['byte_model']['strong_baseline_total_bytes_all32'],'byte baseline total differs')
        require(Fraction(4*bt,5*32)==Fraction(cost['GO_mean_ceiling_exact']),'exact byte gate differs')
        require((Fraction(4*bt,5*32)-512000000)/3328==Fraction(cost['S1_mean_survivor_GO_ceiling_exact']),'exact survivor ceiling differs')
        require(Fraction(result['p90_exact_numerator'],result['p90_exact_denominator'])==p90,'p90 fraction differs')
        require(close(cand['headroom_realization'],(b0-total)/(b0-o2)),'headroom realization differs')
        for r,bc in zip(br,cost['queries']):require(bc['query_id']==r['query_id'] and bc['modeled_coordinate_bytes']==512000000+3328*r['S1']['survivors'],'query byte model differs')
        methods.append(('S1',br,'routing/S1_SECTOR_MOMENT.json'))
        selections=read('routing/SECTOR_SELECTIONS.json');require([r['query_id'] for r in selections]==ids,'selection IDs differ')
        sets=[]
        for s in selections:
            v=s['scan_sectors'];require(len(v)==len(set(v))==16 and v==sorted(v) and 0<=min(v)<=max(v)<120,'invalid selected sectors')
            require(set(v)==set(s['ranked_sectors']),'sector ownership differs');sets.append(set(v))
        overlap=read('analysis/SECTOR_OVERLAP.json');actual=[len(sets[i]&sets[j]) for i in range(32) for j in range(i+1,32)]
        require(actual==[r['intersection'] for r in overlap['query_pairs']] and overlap['pair_count']==496,'sector overlap differs')
        require(overlap['matrix_fraction']==[[len(x&y)/16 for y in sets] for x in sets],'sector matrix differs')
        require(overlap['unique_selected_sets']==len({tuple(sorted(v)) for v in sets}),'sector diversity differs')
        require([r['intersection'] for r in read('analysis/B0_OVERLAP.json')['queries']]==[len(v&set(range(16))) for v in sets],'B0 overlap differs')
        stats=json.loads((parent/'routing/DATASET_STATS.json').read_text());packed=struct.pack('<1920f',*(stats['mean']+stats['variance']))
        si=read('routing/DATASET_STATS_IDENTITY.json')
        require(len(packed)==si['metadata_bytes']==7680 and hashlib.sha256(packed).hexdigest()==si['binary_sha256']==c['routing']['moment_binary_sha256'],'moment bytes differ')
        require(si['reestimated'] is False and si['query_sector_ID_bytes']==32,'metadata ownership differs')
    else:final=a;require(d['Gate6B']=='NOT_RUN','B reported without admission')
    for name,r,file in methods:
        agg=read(file);count=sum(q[name]['survivors'] for q in r)
        require(agg['total_survivors']==count and agg['mean_survivors']==count/32,'mean differs: '+name)
        require(agg['selected_sector_count']==16 and agg['nominal_sector_payload_bytes_per_object']==512,'sector budget differs')
        for i,q in enumerate(r):
            v=q[name];require(v['pairs']==n and v['false_rejections']==v['unsafe_partial_bounds']==0,'unsafe reported partial')
            require(v['hits']<=v['survivors']<=n and v['hits']==c['baseline']['expected_queries'][i]['hits'],'true hits differ')
            require(qr[i][name]==v['survivors'],'query count differs')
    for name in ('O2_over_B0',)+(('S1_over_B0',) if b_exists else ()):
        v=[Fraction(r[name.split('_over_')[0]],r['B0']) for r in qr];report=read('analysis/QUERY_DISTRIBUTION.json')['ratio_distributions'][name]
        for label,p in [('min',0),('p10',Fraction(1,10)),('median',Fraction(1,2)),('p90',Fraction(9,10)),('max',1)]:require(close(report[label],float(quantile(v,p))),'query quantile differs')
    for label in ['A']+(['B'] if b_exists else []):
        reg=read('evidence/'+label+'/REGISTRATION.json');closure=read('evidence/'+label+'/CLOSURE.json');geo=read('evidence/'+label+'/GEOMETRY.json')
        require(reg['contract_sha256']==sha(ROOT/'CONTRACT.json'),'contract registration differs')
        for name,digest in reg['source_sha256'].items():require(sha(ROOT/name)==digest,'measurement source differs: '+name)
        require(reg['Python_optimization_level']==closure['Python_optimization_level']==0,'optimized Python used')
        require(closure['all_input_source_parent_reference_hashes_unchanged'] and closure['population_processes']==1 and closure['query_count']==32,'closure incomplete')
        require(closure['GPU_starts']==closure['NCU_starts']==0 and closure['CPU_workers']==4,'resource scope differs')
        require(geo['row_bytes']==3840 and geo['row_stride_mod32']==0 and geo['CPU_payload_pointer_mod32']==12 and geo['device_allocation_tested'] is False,'conditional geometry differs')
        qual=read('evidence/'+label+'/QUALIFICATION.json');require(qual['passed'] and qual['pairs']==131072 and read('evidence/'+label+'/FIXTURES.json')['returncode']==0,'qualification failed')
    q=read('quality/EXACTNESS.json');require(q['false_rejections']==q['unsafe_partial_bounds']==q['A_full_score_bit_mismatches']==0,'quality summary differs')
    require(q['saved_partial_checks']==32*n*(3 if b_exists else 2),'proof population differs')
    require(d['final_diagnostic_gate']==final and d['Gate6A']==a and d['GPU']==d['NCU']=='NOT_RUN','decision scope differs')
    if (ROOT/'PUBLICATION_SET.json').exists():
        files=read('PUBLICATION_SET.json')['files'];actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        require(actual==set(files)|{'PUBLICATION_SET.json'},'publication inventory differs')
        for name,item in files.items():require((ROOT/name).stat().st_size==item['bytes'] and sha(ROOT/name)==item['sha256'],'publication bytes differ')
    print(f'PASS: scalar parents/sources, exact gates, conditional geometry/bytes and budgets; declared {q["saved_partial_checks"]} proof checks; {final}; zero GPU')


def raw_audit(a,b,cache,data,repo):
    import numpy as np
    c=read('CONTRACT.json');ids=c['workload']['query_ids'];n=c['workload']['N'];cutoff=float.fromhex(c['workload']['cutoff_hex']);checked=0
    refs=read('evidence/A/REGISTRATION.json')['reference_hashes']
    for qid in ids:
        p=cache/f'{qid}.f64';require(sha(p)==refs[p.name],'private full score differs');ref=np.memmap(p,mode='r',dtype='<f8',shape=(n,))
        for label,work,names in [('A',a,['B0','O2']),('B',b,['S1'])]:
            if work is None:continue
            row=next(r for r in read('evidence/'+label+'/QUERY_RESULTS.json') if r['query_id']==qid);manifest=read('evidence/'+label+'/RAW_MANIFEST.json')['files']
            for name in names:
                file=f'{qid}.{name}.f64';p=work/'raw'/file
                require(p.stat().st_size==manifest[file]['bytes']==n*8 and sha(p)==manifest[file]['sha256'],'private proof identity differs')
                v=np.memmap(p,mode='r',dtype='<f8',shape=(n,));require(np.isfinite(v).all() and (v>=0).all() and (v<=ref).all(),'unsafe saved partial')
                require(not np.any((v>cutoff)&(ref<=cutoff)),'false saved rejection')
                require(int((v<=cutoff).sum())==row[name]['survivors'],'saved count differs');checked+=n;v._mmap.close()
        ref._mmap.close()
    if data is not None and b is not None:
        require(sha(data)==c['workload']['data_sha256'],'database identity differs')
        stats=json.loads((repo/'artifacts/proof_per_byte_512_gate5_20261013/routing/DATASET_STATS.json').read_text())
        mu=np.asarray(stats['mean'],dtype='<f4').astype(np.float64);var=np.asarray(stats['variance'],dtype='<f4').astype(np.float64)
        x=np.memmap(data,mode='r',dtype='<f4',offset=12,shape=(n,960))
        for qid,s in zip(ids,read('routing/SECTOR_SELECTIONS.json')):
            delta=x[qid].astype(np.float64)-mu;terms=delta*delta+var;scores=np.zeros(120,dtype='<f8')
            for h in range(8):scores+=terms[h::8]
            ranked=np.argsort(-scores,kind='stable')[:16].tolist()
            require(ranked==s['ranked_sectors'] and sorted(ranked)==s['scan_sectors'],'independent query sector selection differs')
            require(hashlib.sha256(scores.tobytes()).hexdigest()==s['sector_scores_sha256'],'query priority bits differ')
        x._mmap.close();print('PASS: all32 query-only sector selections independently reconstructed from original queries and frozen moments')
    print(f'PASS: independent read-only raw audit, {checked} safe partials, no candidate rerun')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    for name in ('raw-a','raw-b','cache','data'):p.add_argument('--'+name,type=Path)
    args=p.parse_args();scalars(args.repo.resolve())
    if args.raw_a:
        require(args.cache is not None,'cache required');raw_audit(args.raw_a,args.raw_b,args.cache,args.data,args.repo.resolve())
