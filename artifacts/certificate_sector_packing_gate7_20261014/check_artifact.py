#!/usr/bin/env python3
"""Independent release checks; no GPU or new population execution."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent


def need(ok,message):
    if not ok:raise AssertionError(message)


def read(p):return json.loads(Path(p).read_text())


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def quantile(v,p):
    v=sorted(v);r=(len(v)-1)*p;lo=int(r);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(r-lo)


def decision(t,s,p):
    if 10*t<=7*s:return 'GO_PACKING_INFORMATION' if p<=Fraction(4,5) else 'UNCLASSIFIED'
    return 'CONDITIONAL_PACKING' if 20*t<=17*s else 'NO_GO_PACKING'


def close(a,b):return math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-14)


def scalar(repo):
    need(decision(70,100,Fraction(4,5))=='GO_PACKING_INFORMATION','GO boundary')
    need(decision(70,100,Fraction(81,100))=='UNCLASSIFIED','grey-zone boundary')
    need(decision(71,100,0)==decision(85,100,0)=='CONDITIONAL_PACKING' and decision(86,100,0)=='NO_GO_PACKING','conditional/NO_GO boundary')
    c=read(ROOT/'CONTRACT.json');ids=c['workload']['query_ids'];n=c['workload']['N']
    for p,digest in c['parent_files'].items():need(sha(repo/p)==digest,'parent differs: '+p)
    need(c['prior_art']['verdict']=='DISTINCT_ENOUGH_TO_TEST','admission missing')
    for label in ('training','evaluation'):
        reg=read(ROOT/f'evidence/{label}/REGISTRATION.json');closure=read(ROOT/f'evidence/{label}/CLOSURE.json')
        need(closure['complete'] and closure['unchanged_sources_data_parents'],'closure incomplete')
        for p,digest in reg['source_sha256'].items():need(sha(ROOT/p)==digest,'registered source differs: '+p)
        need(reg['GPU_starts']==reg['NCU_starts']==0 and reg['CPU_workers']==4 and reg['nice']>=10 and reg['Python_optimization_level']==0,'execution scope differs')
    admission=read(ROOT/'evidence/ADMISSION.json');training_reg=read(ROOT/'evidence/training/REGISTRATION.json')
    need(admission['registered_utc']<training_reg['started_utc'] and admission['prior_art_document_sha256']==sha(ROOT/'prior_art/PRIOR_ART_PACKING.md') and admission['SOURCES_sha256']==sha(ROOT/'prior_art/SOURCES.json'),'pre-training admission identity/order differs')
    need(not admission['any_training_ids_generated'] and not admission['any_population_started'],'admission performed late')
    t=read(ROOT/'training_queries/TRAIN_QUERY_IDS.json');topfile=ROOT/'training_queries/TRAIN_TOP128.u16'
    need(len(t['query_ids'])==len(set(t['query_ids']))==1024 and not(set(t['query_ids'])&set(ids)) and all(0<=j<n for j in t['query_ids']),'train/eval ownership')
    need(t['seed']==2026101401 and t['eval_overlap']==t['duplicates']==0,'training freeze differs')
    data=topfile.read_bytes();need(len(data)==1024*128*2,'top128 size differs');flat=struct.unpack('<131072H',data)
    w=[[0]*960 for _ in range(960)]
    for offset in range(0,len(flat),128):
        dims=flat[offset:offset+128];need(len(set(dims))==128 and max(dims)<960,'training top128 invalid')
        for i in dims:
            row=w[i]
            for j in dims:row[j]+=1
    wm=read(ROOT/'training_queries/COSELECTION_MATRIX_META.json')
    blob=b''.join(struct.pack('<960H',*row) for row in w)
    need(hashlib.sha256(blob).hexdigest()==wm['sha256'] and len(blob)==wm['bytes']==1843200,'W reconstruction differs')
    need(sum(map(sum,w))==wm['total_entries_sum']==1024*128*128 and sum(w[i][i] for i in range(960))==wm['diagonal_sum']==1024*128,'W count geometry differs')
    degree=list(map(sum,w));pool=set(range(960));actual=[]
    while pool:
        seed=max(pool,key=lambda i:(degree[i],-i));group=[seed];pool.remove(seed)
        while len(group)<8:
            j=max(pool,key=lambda x:(sum(w[x][g] for g in group),degree[x],-x));group.append(j);pool.remove(j)
        actual.extend(group)
    pp=read(ROOT/'packing/PERMUTATION.json');pi=pp['pi'];groups=read(ROOT/'packing/SECTORS.json')['groups']
    need(pi==actual and sorted(pi)==list(range(960)) and groups==[pi[i:i+8] for i in range(0,960,8)],'independent fixed greedy differs')
    need(pp['training_ids_sha256']==sha(ROOT/'training_queries/TRAIN_QUERY_IDS.json') and pp['training_top128_sha256']==sha(topfile) and pp['W_sha256']==wm['sha256'],'training->packing hashes differ')
    freeze=read(ROOT/'evidence/training/PERMUTATION_FROZEN.json');start=read(ROOT/'evidence/evaluation/START.json')
    need(freeze['permutation_sha256']==sha(ROOT/'packing/PERMUTATION.json')==start['permutation_sha256'] and freeze['sectors_sha256']==sha(ROOT/'packing/SECTORS.json'),'packing freeze changed')
    need(freeze['evaluation_queries_read']==freeze['evaluation_outcomes_read']==0 and not freeze['second_algorithm'] and freeze['frozen_utc']<start['started_utc'],'eval leakage/order')
    need(read(ROOT/'evidence/evaluation/FIXTURES.json')['returncode']==0 and read(ROOT/'evidence/evaluation/QUALIFICATION.json')['passed'],'qualification failed')
    rows=read(ROOT/'evidence/evaluation/QUERY_RESULTS.json');s1=read(ROOT/'baseline/S1_ORIGINAL_LAYOUT.json');cand=read(ROOT/'candidate/P1_PACKED_SECTOR_MOMENT.json')
    need([r['query_id'] for r in rows]==ids and len(rows)==32,'candidate query order differs')
    total=sum(r['survivors'] for r in rows);s=sum(r['survivors'] for r in s1['queries']);need(s==s1['total_survivors']==3776388,'S1 primary differs')
    ratios=[Fraction(a['survivors'],b['survivors']) for a,b in zip(rows,s1['queries'])];p90=quantile(ratios,Fraction(9,10));label=decision(total,s,p90)
    result=read(ROOT/'evidence/evaluation/RESULTS.json');d=read(ROOT/'evidence/DECISION.json');cost=read(ROOT/'cost/FULL_FALLBACK_BYTES.json')
    need(result['gate']==cand['gate']==d['final']==label and cand['total_survivors']==result['total_survivors']==total and cand['mean_survivors']==total/32,'candidate aggregate/gate differs')
    need(Fraction(result['p90_exact_numerator'],result['p90_exact_denominator'])==p90 and close(cand['p90_P1_over_S1'],float(p90)),'exact p90 differs')
    need(cost['total_bytes_all32']==32*512000000+3328*total and cost['mean_bytes']==cost['total_bytes_all32']/32,'byte model differs')
    need(cost['strong_baseline_total_bytes_all32']==32474520832 and cost['strong_GO']==(5*cost['total_bytes_all32']<=4*32474520832),'strong byte gate differs')
    need(cand['selected_sector_count']==16 and cand['nominal_source_payload_bytes_per_object']==512 and cand['subset_implementation_source_reads_per_object']==128 and cand['full_audit_separate_reads_per_object']==960,'subset/full audit scope conflated')
    for a,b in zip(rows,s1['queries']):need(a['pairs']==a['full_score_bit_comparisons']==n and a['false_rejections']==a['unsafe_partial_bounds']==a['full_score_bit_mismatches']==0 and a['hits']==b['hits']<=a['survivors']<=n,'quality row differs')
    q=read(ROOT/'quality/EXACTNESS.json');par=read(ROOT/'quality/PERMUTATION_PARITY.json');trans=read(ROOT/'evidence/evaluation/TRANSFORM.json')
    need(q['distinct_candidate_pairs']==q['candidate_saved_partial_checks']==par['pair_bit_comparisons']==32000000 and q['all_saved_partial_checks_including_historical_S1_C1']==96000000,'quality populations differ')
    need(trans['validated_coordinate_bits']==par['original_coordinate_bit_comparisons']==960000000 and trans['mismatches']==par['full_bit_mismatches']==par['original_coordinate_bit_mismatches']==0,'transform/oracle differs')
    need(trans['CPU_payload_pointer_mod32']==trans['row_stride_mod32']==0 and par['candidate_database_representations']==1 and not par['candidate_original_database_access'],'single representation/geometry differs')
    ev=read(ROOT/'packing/EVALUATION_SELECTIONS.json');recovery=read(ROOT/'analysis/C1_RECOVERY.json');purity=read(ROOT/'analysis/SECTOR_PURITY.json');oldsectors=read(repo/'artifacts/sector_proof_per_byte_gate6_20261014/routing/SECTOR_SELECTIONS.json')
    for i,(e,old) in enumerate(zip(ev,oldsectors)):
        need(e['query_id']==old['query_id']==ids[i] and len(e['scan_sectors'])==len(set(e['scan_sectors']))==16 and e['scan_sectors']==sorted(e['scan_sectors']),'selection ownership differs')
        selected=sorted(j for sector in e['scan_sectors'] for j in groups[sector]);c1=set(e['C1_top128']);need(len(c1)==128 and selected==e['selected_original_dims'],'C1/selected dimensions differ')
        good=len(c1&set(selected));need(e['C1_recovery']==recovery['queries'][i]['fraction']==good/128,'C1 recovery differs')
        p=[len(c1&set(groups[sector])) for sector in e['scan_sectors']];b=[len(c1&set(range(8*z,8*z+8))) for z in old['scan_sectors']]
        need(p==e['P1_high_value_dims_per_selected_sector'] and b==e['S1_high_value_dims_per_selected_sector'],'sector purity differs')
        need(purity['queries'][i]['P1_mean_high_value_dims_per_sector']==sum(p)/16 and purity['queries'][i]['S1_mean_high_value_dims_per_sector']==sum(b)/16,'per-query purity differs')
    need(close(recovery['mean'],sum(e['C1_recovery'] for e in ev)/32) and close(purity['P1_mean'],sum(e['P1_mean_high_value_dims_per_sector'] for e in purity['queries'])/32) and close(purity['S1_mean'],sum(e['S1_mean_high_value_dims_per_sector'] for e in purity['queries'])/32),'recovery/purity means differ')
    qr=read(ROOT/'analysis/QUERY_DISTRIBUTION.json')
    for label1,p1 in [('min',0),('p10',Fraction(1,10)),('median',Fraction(1,2)),('p90',Fraction(9,10)),('max',1)]:need(close(qr['ratio_distribution'][label1],float(quantile(ratios,p1))),'query quantile differs')
    need(qr['queries_improved']==sum(r<1 for r in ratios) and qr['queries_equal']==sum(r==1 for r in ratios) and qr['queries_worse']==sum(r>1 for r in ratios),'query win counts differ')
    need(d['GPU_starts']==d['NCU_starts']==d['NSYS_starts']==0 and not d['Gate8_started'] and not d['novelty_claim'],'no-GPU/claim boundary differs')
    manifest=ROOT/'PUBLICATION_SET.json'
    if manifest.exists():
        m=read(manifest)
        for p,record in m['files'].items():need((ROOT/p).stat().st_size==record['bytes'] and sha(ROOT/p)==record['sha256'],'publication file differs: '+p)
        actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLICATION_SET.json'}
        need(actual==set(m['files']),'publication whitelist differs')
    print(json.dumps({'passed':True,'decision':label,'P1_total':total,'P1_mean':total/32,'W_and_permutation_independently_reconstructed':True,'GPU_starts':0},sort_keys=True))


def input_scores(repo,data):
    """Read-only original input audit; no pair distances or candidate execution."""
    c=read(ROOT/'CONTRACT.json');need(sha(data)==c['workload']['data_sha256'],'data identity differs')
    stats=read(repo/'artifacts/proof_per_byte_512_gate5_20261013/routing/DATASET_STATS.json')
    mu,var=stats['mean'],stats['variance'];top=struct.unpack('<131072H',(ROOT/'training_queries/TRAIN_TOP128.u16').read_bytes())
    train=read(ROOT/'training_queries/TRAIN_QUERY_IDS.json')['query_ids'];pi=read(ROOT/'packing/PERMUTATION.json')['pi'];groups=[pi[i:i+8] for i in range(0,960,8)]
    evaluation=read(ROOT/'packing/EVALUATION_SELECTIONS.json');selections=[]
    with data.open('rb') as f:
        need(struct.unpack('<iii',f.read(12))==(960,1000000,2),'data header differs')
        def scores(qid):
            f.seek(12+qid*3840);q=struct.unpack('<960f',f.read(3840));out=[]
            for j in range(960):delta=q[j]-mu[j];out.append(delta*delta+var[j])
            return out
        for i,qid in enumerate(train):
            s=scores(qid);actual=sorted(range(960),key=lambda j:(-s[j],j))[:128]
            need(actual==list(top[i*128:(i+1)*128]),'independent training score order differs')
        for e in evaluation:
            s=scores(e['query_id']);actual=sorted(range(960),key=lambda j:(-s[j],j))[:128]
            need(actual==e['C1_top128'],'independent eval C1 order differs');sums=[]
            for g in groups:
                v=0.
                for j in g:v=v+s[j]
                sums.append(v)
            chosen=sorted(range(120),key=lambda j:(-sums[j],j))[:16]
            need(chosen==e['ranked_sectors'] and hashlib.sha256(struct.pack('<120d',*sums)).hexdigest()==e['sector_scores_sha256'],'independent packed sector scores/selection differ')
            selections.append(sorted(chosen))
    print(json.dumps({'read_only_input_scores_passed':True,'train_rows':1024,'eval_rows':32,'new_population_pairs':0,'GPU_starts':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT.parent.parent);p.add_argument('--data',type=Path);args=p.parse_args();scalar(args.repo)
    if args.data:input_scores(args.repo,args.data)
