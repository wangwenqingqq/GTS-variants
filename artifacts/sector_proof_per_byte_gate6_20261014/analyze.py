#!/usr/bin/env python3
"""Read-only saved-array observer: exact counts, conditional bytes, four auxiliaries."""
import argparse
from fractions import Fraction
import hashlib
from pathlib import Path
import shutil

import numpy as np

from run import ROOT,PREVIOUS,read,save,require,sha,quality,distribution,gate_a,gate_b,exact_quantile


def aggregate(rows,name,n):
    total=sum(r[name]['survivors'] for r in rows)
    return {'status':'MEASURED_CPU_CERTIFICATE_DIAGNOSTIC','query_count':len(rows),'pairs':n*len(rows),
            'total_survivors':total,'mean_survivors':total/len(rows),'reject_fraction':1-total/(n*len(rows)),
            'selected_sector_count':16,'nominal_sector_payload_bytes_per_object':512,
            'queries':[{'query_id':r['query_id'],**r[name]} for r in rows]}


def analyze(args):
    c=read(ROOT/'CONTRACT.json');w=c['workload'];n=w['N'];cutoff=float.fromhex(w['cutoff_hex'])
    ar=read(args.stage_a/'RESULTS.json');arows=read(args.stage_a/'QUERY_RESULTS.json')
    require(ar['complete'] and [r['query_id'] for r in arows]==w['query_ids'],'A incomplete')
    b0=sum(r['B0']['survivors'] for r in arows);o2=sum(r['O2']['survivors'] for r in arows)
    require(b0==c['baseline']['expected_total_survivors'],'B0 aggregate differs')
    agate='UNCLASSIFIED' if ar['numerical_boundary_pairs'] else gate_a(o2,b0)
    require(agate==ar['gate'],'A gate differs');b=args.stage_b
    require((b is not None)==(agate=='STRONG_SECTOR_HEADROOM'),'B execution does not follow A gate')
    brows=read(b/'QUERY_RESULTS.json') if b else [];br=read(b/'RESULTS.json') if b else None
    if b:require(br['complete'] and [r['query_id'] for r in brows]==w['query_ids'],'B incomplete')
    out=args.output.resolve();out.mkdir()
    for name in ['CONTRACT.json','probe.cpp','run.py','native_check.py','analyze.py','prior_art/TRIAGE.md','prior_art/TRIAGE_SOURCES.json','evidence/CLARIFICATIONS.json']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    receipts=['REGISTRATION','INPUT_CHECK','BUILD','FIXTURES','GEOMETRY','QUALIFICATION','START','QUERY_RESULTS','RAW_MANIFEST','RESULTS','CLOSURE']
    for label,work in [('A',args.stage_a),('B',b)]:
        if work:
            for name in receipts:save(out/'evidence'/label/(name+'.json'),read(work/(name+'.json')))
    base=aggregate(arows,'B0',n);base['exact_parent_count_parity']=True
    oracle=aggregate(arows,'O2',n);oracle.update(ratio_to_B0=o2/b0,gate=agate,deployable=False,actual_diagnostic_source_bytes_per_object=3840,selector_cost_priced=False,numerical_boundary_pairs=ar['numerical_boundary_pairs'])
    save(out/'baseline/B0_FIRST16_SECTORS.json',base);save(out/'oracle/O2_PAIR_TOP16_SECTORS.json',oracle)
    previous=read(PREVIOUS/'routing/C1_MOMENT_SCORE.json')
    save(out/'baseline/C1_SCATTERED_REFERENCE.json',{'remeasured':False,'sector_gate_eligible':False,'status':'historical information-only reference, not a deployable upper bound',
         'nominal_selected_coordinate_bytes':512,'total_survivors':previous['total_survivors'],'mean_survivors':previous['mean_survivors'],'queries':previous['queries'],
         'source_json_sha256':sha(PREVIOUS/'routing/C1_MOMENT_SCORE.json')})
    if b:
        total=sum(r['S1']['survivors'] for r in brows);candidate=aggregate(brows,'S1',n)
        ratios=[Fraction(r['S1']['survivors'],e['survivors']) for r,e in zip(brows,c['baseline']['expected_queries'])]
        p90=exact_quantile(ratios,Fraction(9,10));ft=32*512000000+3328*total
        final=gate_b(ft,c['byte_model']['strong_baseline_total_bytes_all32'],p90)
        require(final==br['gate'] and ft==br['fallback_total_bytes'],'B gate or byte total differs')
        candidate.update(ratio_to_B0=total/b0,gate=final,headroom_realization=(b0-total)/(b0-o2),
                         per_query_ratio_distribution=distribution(list(map(float,ratios))))
        save(out/'routing/S1_SECTOR_MOMENT.json',candidate)
        selections=read(b/'SECTOR_SELECTIONS.json');save(out/'routing/SECTOR_SELECTIONS.json',selections)
        save(out/'routing/DATASET_STATS_IDENTITY.json',read(b/'DATASET_STATS_IDENTITY.json'))
        by=[{'query_id':r['query_id'],'survivors':r['S1']['survivors'],'first_stage_bytes':512000000,
             'fallback_source_bytes':3328*r['S1']['survivors'],'modeled_coordinate_bytes':512000000+3328*r['S1']['survivors']} for r in brows]
        save(out/'cost/FULL_FALLBACK_BYTES.json',{'scope':'conditional source-coordinate model, not measured physical traffic or complete-search execution',
             'selected_coordinates_retained_without_reread_assumption':True,'retention_recomputation_spill_cost':'UNKNOWN_NOT_PRICED',
             'total_bytes_all32':ft,'mean_bytes':ft/32,'strong_baseline_total_bytes_all32':c['byte_model']['strong_baseline_total_bytes_all32'],
             'strong_baseline_mean_bytes':1014828776,'ratio_to_strong_baseline':ft/c['byte_model']['strong_baseline_total_bytes_all32'],
             'GO_mean_ceiling_exact':'4059315104/5','S1_mean_survivor_GO_ceiling_exact':'46853597/520',
             'gate':final,'queries':by})
        sets=[set(r['scan_sectors']) for r in selections];overlap=[]
        matrix=[[len(x&y)/16 for y in sets] for x in sets]
        for i in range(32):
            require(len(sets[i])==16,'sector budget differs')
            for j in range(i+1,32):
                s=len(sets[i]&sets[j]);overlap.append({'query_i':w['query_ids'][i],'query_j':w['query_ids'][j],
                     'intersection':s,'fraction_of16':s/16,'Jaccard':s/(32-s)})
        save(out/'analysis/SECTOR_OVERLAP.json',{'query_pairs':overlap,'pair_count':496,'matrix_fraction':matrix,
             'unique_selected_sets':len({tuple(sorted(s)) for s in sets}),
             'intersection_distribution':distribution([r['intersection'] for r in overlap]),
             'fraction_distribution':distribution([r['fraction_of16'] for r in overlap]),
             'Jaccard_distribution':distribution([r['Jaccard'] for r in overlap])})
        both=[{'query_id':qid,'intersection':len(s&set(range(16))),'fraction_of16':len(s&set(range(16)))/16} for qid,s in zip(w['query_ids'],sets)]
        save(out/'analysis/B0_OVERLAP.json',{'queries':both,'intersection_distribution':distribution([r['intersection'] for r in both])})
    else:
        final=agate;candidate={'status':'NOT_RUN','reason':'A did not pass STRONG_SECTOR_HEADROOM'}
        for name in ('routing/S1_SECTOR_MOMENT.json','routing/SECTOR_SELECTIONS.json','routing/DATASET_STATS_IDENTITY.json','cost/FULL_FALLBACK_BYTES.json','analysis/SECTOR_OVERLAP.json','analysis/B0_OVERLAP.json'):save(out/name,candidate)
    qr=[]
    for i,r in enumerate(arows):
        v={'query_index':i,'query_id':r['query_id'],'B0':r['B0']['survivors'],'O2':r['O2']['survivors'],
           'C1_scattered_reference':previous['queries'][i]['survivors'],'O2_over_B0':r['O2']['survivors']/r['B0']['survivors']}
        if b:v.update(S1=brows[i]['S1']['survivors'],S1_over_B0=brows[i]['S1']['survivors']/r['B0']['survivors'])
        qr.append(v)
    distributions={'O2_over_B0':distribution([r['O2_over_B0'] for r in qr])}
    if b:distributions['S1_over_B0']=distribution([r['S1_over_B0'] for r in qr])
    save(out/'analysis/QUERY_DISTRIBUTION.json',{'queries':qr,'ratio_distributions':distributions,'quantiles':'linear, equal query weight'})
    manifests={label:read(work/'RAW_MANIFEST.json')['files'] for label,work in [('A',args.stage_a),('B',b)] if work}
    refs=read(args.stage_a/'REGISTRATION.json')['reference_hashes'];checks=0;zeros=0
    fractions={'B0':[],**({'S1':[]} if b else {})};margins={g:[] for g in ('nonhit_rejected','nonhit_survived','hits')};cr=[];mr=[]
    for i,qid in enumerate(w['query_ids']):
        p=args.cache/f'{qid}.f64';require(sha(p)==refs[p.name],'frozen full-score file differs')
        ref=np.memmap(p,mode='r',dtype='<f8',shape=(n,));positive=ref>0;hits=ref<=cutoff
        zero=int((~positive).sum());zeros+=zero;crow={'query_id':qid,'excluded_zero_full_distances':zero};mrow={'query_id':qid}
        for label,work,names in [('A',args.stage_a,['B0','O2']),('B',b,['S1'])]:
            if work is None:continue
            for name in names:
                file=f'{qid}.{name}.f64';p=work/'raw'/file;entry=manifests[label][file]
                require(p.stat().st_size==entry['bytes']==n*8 and sha(p)==entry['sha256'],'saved proof differs')
                part=np.memmap(p,mode='r',dtype='<f8',shape=(n,));expected=arows[i][name] if label=='A' else brows[i][name]
                require(quality(part,ref,cutoff)==expected,'saved quality/count differs');checks+=n
                if name in fractions:
                    v=part[positive]/ref[positive];fractions[name].append(v);crow[name]=distribution(v)
                if name=='S1':
                    for group,mask in [('nonhit_rejected',(~hits)&(part>cutoff)),('nonhit_survived',(~hits)&(part<=cutoff)),('hits',hits)]:
                        v=part[mask]/cutoff;margins[group].append(v);mrow[group]=distribution(v)
                part._mmap.close()
        ref._mmap.close();cr.append(crow);mr.append(mrow)
    save(out/'analysis/CONTRIBUTION_CONCENTRATION.json',{'metric':'selected original-order partial / frozen full, full>0 only',
         'excluded_zero_full_distances':zeros,'pooled':{name:distribution(np.concatenate(v)) for name,v in fractions.items()},'queries':cr,'S1_status':'MEASURED' if b else 'NOT_RUN'})
    save(out/'analysis/MARGIN.json',{'metric':'S1 partial/cutoff, grouped by true hit and strict certificate outcome',
         'pooled':{g:distribution(np.concatenate(v)) for g,v in margins.items()} if b else candidate,'queries':mr,'S1_status':'MEASURED' if b else 'NOT_RUN'})
    save(out/'quality/EXACTNESS.json',{'distinct_query_object_pairs':32*n,'A_full_score_bit_comparisons':32*n,'A_full_score_bit_mismatches':0,
         'saved_partial_checks':checks,'false_rejections':0,'unsafe_partial_bounds':0,'exact_B0_parent_parity':True,
         'oracle_numerical_boundary_pairs':ar['numerical_boundary_pairs'],'complete_search_claim':False})
    prior='REQUIRED_NOT_YET_COMPLETED' if final=='GO_SECTOR_PROOF_PER_BYTE' else 'NOT_TRIGGERED'
    save(out/'evidence/DECISION.json',{'Gate6A':agate,'Gate6B':final if b else 'NOT_RUN','final_diagnostic_gate':final,
         'GPU':'NOT_RUN','NCU':'NOT_RUN','dedicated_sector_prior_art_gate':prior,
         'S1_ratio_to_B0':candidate.get('ratio_to_B0'),'headroom_realization':candidate.get('headroom_realization')})
    save(out/'evidence/OBSERVATION_ORDER.json',{'Gate6A_query_ids':w['query_ids'],'Gate6B_query_ids':w['query_ids'] if b else [],'population_processes':2 if b else 1,'performance_claim':False})
    save(out/'evidence/OFFLINE_AUDIT.json',{'passed':True,'saved_partial_checks':checks,'hashes_and_all_saved_partials_against_frozen_scores':True,'candidate_rerun':False,'new_GPU_starts':0})
    print({'Gate6A':agate,'Gate6B':final if b else 'NOT_RUN','B0_mean':base['mean_survivors'],'O2_mean':oracle['mean_survivors'],'S1_mean':candidate.get('mean_survivors'),'saved_partial_checks':checks})


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('stage-a','cache','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage-b',type=Path);analyze(p.parse_args())
