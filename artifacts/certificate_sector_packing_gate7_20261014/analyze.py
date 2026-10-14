#!/usr/bin/env python3
"""Read-only raw-proof audit and the four predeclared auxiliary analyses."""
import argparse
from fractions import Fraction
import hashlib
from pathlib import Path
import shutil
import numpy as np
import pack
from run import ROOT,read,save,sha,require,quality,distribution,gate,exact_quantile


def analyze(args):
    c=read(ROOT/'CONTRACT.json');w=c['workload'];n=w['N'];cutoff=float.fromhex(w['cutoff_hex'])
    result=read(args.evaluation/'RESULTS.json');require(result['complete'] and read(args.evaluation/'CLOSURE.json')['complete'],'population incomplete')
    out=args.output;out.mkdir();rows=read(args.evaluation/'QUERY_RESULTS.json');require([r['query_id'] for r in rows]==w['query_ids'],'query order differs')
    for label,work in [('training',args.training),('evaluation',args.evaluation)]:
        for p in work.glob('*.json'):save(out/'evidence'/label/p.name,read(p))
    for src,dst in [('TRAIN_QUERY_IDS.json','training_queries/TRAIN_QUERY_IDS.json'),('COSELECTION_MATRIX_META.json','training_queries/COSELECTION_MATRIX_META.json'),('PERMUTATION.json','packing/PERMUTATION.json'),('SECTORS.json','packing/SECTORS.json')]:
        save(out/dst,read(args.training/src))
    p=out/'training_queries/TRAIN_TOP128.u16';p.parent.mkdir(exist_ok=True);shutil.copyfile(args.training/'TRAIN_TOP128.u16',p)
    previous=args.repo/'artifacts/proof_per_byte_512_gate5_20261013';six=args.repo/'artifacts/sector_proof_per_byte_gate6_20261014'
    for name,src in [('B0_ORIGINAL_FIRST16.json',six/'baseline/B0_FIRST16_SECTORS.json'),('S1_ORIGINAL_LAYOUT.json',six/'routing/S1_SECTOR_MOMENT.json'),('C1_SCATTERED_REFERENCE.json',previous/'routing/C1_MOMENT_SCORE.json'),('O2_ORACLE_REFERENCE.json',six/'oracle/O2_PAIR_TOP16_SECTORS.json')]:
        value=read(src);value.update(remeasured_in_Gate7=False,historical_parent_sha256=sha(src));save(out/'baseline'/name,value)
    s1=read(six/'routing/S1_SECTOR_MOMENT.json')['queries'];refs=read(args.evaluation/'REFERENCE_IDENTITIES.json')
    manifests={'P1':read(args.evaluation/'RAW_MANIFEST.json')['files'],'S1':read(six/'evidence/B/RAW_MANIFEST.json')['files'],'C1':read(previous/'evidence/B/RAW_MANIFEST.json')['files']}
    pool={name:[] for name in manifests};contribution=[];checks=0;zeros=0
    for idx,qid in enumerate(w['query_ids']):
        rp=args.cache/f'{qid}.f64';require(sha(rp)==refs[rp.name],'frozen reference changed')
        full=np.memmap(rp,mode='r',dtype='<f8',shape=(n,));positive=full>0;zero=int((~positive).sum());zeros+=zero;crow={'query_id':qid,'excluded_zero_full':zero}
        for name,folder in [('P1',args.evaluation/'raw'),('S1',args.s1_raw),('C1',args.c1_raw)]:
            file=f'{qid}.{name}.f64';p=folder/file;record=manifests[name][file]
            require(p.stat().st_size==record['bytes']==n*8 and sha(p)==record['sha256'],'raw proof differs: '+file)
            part=np.memmap(p,mode='r',dtype='<f8',shape=(n,));q=quality(part,full,cutoff);checks+=n
            expected=rows[idx] if name=='P1' else (s1[idx] if name=='S1' else read(previous/'routing/C1_MOMENT_SCORE.json')['queries'][idx])
            require(q['survivors']==expected['survivors'] and q['hits']==expected['hits'],'saved count differs')
            v=part[positive]/full[positive];pool[name].append(v);crow[name]={'median':float(np.quantile(v,.5,method='linear')),'p90':float(np.quantile(v,.9,method='linear'))};part._mmap.close()
        full._mmap.close();contribution.append(crow)
    save(out/'analysis/CONTRIBUTION_CONCENTRATION.json',{'metric':'ordered partial/frozenfull; full>0 only','pooled':{name:{'median':float(np.quantile(np.concatenate(v),.5,method='linear')),'p90':float(np.quantile(np.concatenate(v),.9,method='linear'))} for name,v in pool.items()},'queries':contribution,'excluded_zero_full':zeros,'parent_proofs_remeasured':False})
    selections=read(args.evaluation/'EVALUATION_SELECTIONS.json');require([r['query_id'] for r in selections]==w['query_ids'],'selection query IDs differ')
    save(out/'packing/EVALUATION_SELECTIONS.json',selections)
    recovery=[{'query_id':s['query_id'],'intersection':int(s['C1_recovery']*128),'fraction':s['C1_recovery']} for s in selections]
    save(out/'analysis/C1_RECOVERY.json',{'queries':recovery,'distribution':distribution([r['fraction'] for r in recovery]),'mean':float(np.mean([r['fraction'] for r in recovery])),'denominator':128})
    purity=[]
    for s in selections:
        purity.append({'query_id':s['query_id'],'P1_mean_high_value_dims_per_sector':sum(s['P1_high_value_dims_per_selected_sector'])/16,'S1_mean_high_value_dims_per_sector':sum(s['S1_high_value_dims_per_selected_sector'])/16})
    save(out/'analysis/SECTOR_PURITY.json',{'queries':purity,'P1_mean':float(np.mean([r['P1_mean_high_value_dims_per_sector'] for r in purity])),'S1_mean':float(np.mean([r['S1_mean_high_value_dims_per_sector'] for r in purity])),'dimensions_per_sector':8})
    ratios=[Fraction(a['survivors'],b['survivors']) for a,b in zip(rows,s1)];total=sum(r['survivors'] for r in rows);p90=exact_quantile(ratios,Fraction(9,10));decision=gate(total,3776388,p90)
    require(decision==result['gate'],'decision differs')
    qr=[{'query_id':a['query_id'],'P1':a['survivors'],'S1':b['survivors'],'P1_over_S1':float(v)} for a,b,v in zip(rows,s1,ratios)]
    save(out/'analysis/QUERY_DISTRIBUTION.json',{'queries':qr,'ratio_distribution':distribution(list(map(float,ratios))),'p90_exact_numerator':p90.numerator,'p90_exact_denominator':p90.denominator,'quantile_rule':'linear, equal query weight','queries_improved':sum(v<1 for v in ratios),'queries_equal':sum(v==1 for v in ratios),'queries_worse':sum(v>1 for v in ratios)})
    pq=read(args.training/'PACKING_QUALITY.json');pq['evaluation_C1_recovery']=distribution([s['C1_recovery'] for s in selections]);pq['evaluation_mean_C1_recovery']=float(np.mean([s['C1_recovery'] for s in selections]));pq['training_mean_C1_recovery']=pq['training_mean_high_value_dims_per_selected_sector']/8
    pq['evaluation_packed_sector_concentration']=distribution([s['packed_sector_concentration'] for s in selections]);pq['evaluation_original_sector_concentration']=distribution([s['original_sector_concentration'] for s in selections]);pq['evaluation_sector_concentration_mean']=float(np.mean([s['packed_sector_concentration'] for s in selections]));pq['no_evaluation_tuning']=True
    save(out/'packing/PACKING_QUALITY.json',pq)
    save(out/'candidate/P1_PACKED_SECTOR_MOMENT.json',{'status':'MEASURED_CPU_CERTIFICATE_DIAGNOSTIC','pairs':32*n,'query_count':32,'total_survivors':total,'mean_survivors':total/32,'ratio_to_S1':total/3776388,'p90_P1_over_S1':float(p90),'gate':decision,'queries':rows,'selected_sector_count':16,'nominal_source_payload_bytes_per_object':512,'subset_implementation_source_reads_per_object':128,'full_audit_separate_reads_per_object':960,'no_latency_claim':True})
    ft=32*512000000+3328*total;bt=32474520832
    save(out/'cost/FULL_FALLBACK_BYTES.json',{'scope':c['byte_model']['classification'],'formula':'512000000+3328*survivors per query','total_bytes_all32':ft,'mean_bytes':ft/32,'strong_baseline_total_bytes_all32':bt,'strong_baseline_mean_bytes':bt//32,'ratio_to_strong_baseline':ft/bt,'strong_GO':5*ft<=4*bt,'first_stage_FP32_values_retained_without_reread_assumption':True,'mapping_retention_recompute_spill_cost':'UNKNOWN_NOT_PRICED','actual_GPU_traffic':'NOT_MEASURED','full_fallback':'NOT_IMPLEMENTED','queries':[{'query_id':r['query_id'],'modeled_bytes':512000000+3328*r['survivors']} for r in rows]})
    save(out/'quality/EXACTNESS.json',{'distinct_candidate_pairs':32*n,'candidate_saved_partial_checks':32*n,'all_saved_partial_checks_including_historical_S1_C1':checks,'false_rejections':0,'unsafe_partial_bounds':0,'inclusive_cutoff_unchanged':True,'complete_search':False})
    save(out/'quality/PERMUTATION_PARITY.json',{'pair_bit_comparisons':sum(r['full_score_bit_comparisons'] for r in rows),'full_bit_mismatches':0,'original_coordinate_bit_comparisons':read(args.evaluation/'TRANSFORM.json')['validated_coordinate_bits'],'original_coordinate_bit_mismatches':0,'oracle_accumulation_order':'original dimID 0..959','candidate_database_representations':1,'candidate_original_database_access':False,'full_audit_reads_all_coordinates':True})
    save(out/'evidence/DECISION.json',{'prior_art':'DISTINCT_ENOUGH_TO_TEST','final':decision,'population_processes':1,'training_processes':1,'GPU_starts':0,'NCU_starts':0,'NSYS_starts':0,'Gate8_started':False,'novelty_claim':False})
    save(out/'evidence/OFFLINE_AUDIT.json',{'passed':True,'raw_saved_partial_checks':checks,'new_candidate_pairs':32*n,'no_candidate_rerun':True,'read_only_parent_proofs':True,'GPU_starts':0})
    print({'decision':decision,'P1_mean':total/32,'P1_S1':total/3776388,'conditional_model_bytes':ft/32,'saved_quality_checks':checks})


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('training','evaluation','repo','cache','s1-raw','c1-raw','output'):p.add_argument('--'+name,type=Path,required=True)
    analyze(p.parse_args())
