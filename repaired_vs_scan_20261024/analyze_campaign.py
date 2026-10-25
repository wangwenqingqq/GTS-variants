"""Decision-grade paired log-t summaries; only one complete eligible GPU epoch."""
import csv,hashlib,json,math,statistics,sys
from pathlib import Path
T5=2.5705818366

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def percentile(v,p):
    v=sorted(v);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1);return v[lo]+(v[hi]-v[lo])*(i-lo)
def paired(a,b):
    assert len(a)==len(b)==6 and all(math.isfinite(x) and x>0 for x in a+b)
    z=[math.log(x/y) for x,y in zip(a,b)];m=statistics.mean(z);half=T5*statistics.stdev(z)/math.sqrt(6)
    return {'paired_geomean':math.exp(m),'CI95':[math.exp(m-half),math.exp(m+half)],'round_ratios':[x/y for x,y in zip(a,b)],'numerator_faster_rounds':sum(x<y for x,y in zip(a,b))}

def summarize(epoch,out):
    epoch=Path(epoch);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    quality_mode=(epoch/'TIMING_COMPLETE.json').exists()
    assert ((epoch/'TIMING_COMPLETE.json').exists() if quality_mode else (epoch/'COMPLETE.json').exists()) and not (epoch/'INVALID_EPOCH.json').exists() and not (epoch/'FAILED.json').exists()
    complete=json.loads((epoch/('TIMING_COMPLETE.json' if quality_mode else 'COMPLETE.json')).read_text());gpu=complete['gpu_uuid'];assert complete['rounds']==6
    for name in (['FULL_QUALITY.json','GATES_PASS.json','COUNT_COLLECTED.json','frozen_inputs_verified.json','TIMING_SCHEDULE.json'] if quality_mode else ['FULL_PASS.json','GATES_PASS.json','COUNT_PASS.json','frozen_inputs_verified.json','TIMING_SCHEDULE.json']):
        assert (epoch/name).exists(),name
    schedules=json.loads((epoch/'TIMING_SCHEDULE.json').read_text());assert len(schedules)==18
    frozen_inputs=json.loads((epoch/'frozen_inputs_verified.json').read_text())
    full_quality=json.loads((epoch/'FULL_QUALITY.json').read_text()) if quality_mode else None
    root=epoch.parent.parent
    result={'experiment':'repaired_vs_scan_20261024','state':complete.get('state','complete_same_GPU_six_round_matrix'),'gpu_uuid':gpu,'rounds':6,'cases':[],'receipts':{}}
    raw=[]
    for case in schedules:
        kind,k,q=case['kind'],case['k'],case['Q'];arms='ARS' if kind=='words' else 'ARSX';process={a:[] for a in arms};samples={a:[] for a in arms};setups={a:[] for a in arms};native={};counts={};timed=case.get('timed_arms',arms);status=case.get('quality',{a:'pass' for a in arms})
        for arm in arms:
            label=f'full_{kind}_k{k}_q{q}_{arm}'
            r=(root/full_quality['evidence'][label]['path']) if quality_mode else epoch/label
            receipt=json.loads((r/'receipt.json').read_text());assert receipt['gpu_uuid']==gpu and receipt['exit_code'] in (0,20,21) and (receipt['exit_code']==0)==(status[arm]=='pass')
            if status[arm]=='pass':assert receipt['valid']
            native[arm]=sha(r/'result.native.bin')
            c=epoch/f'count_{kind}_k{k}_q{q}_{arm}';cr=json.loads((c/'receipt.json').read_text());assert cr['instrumented'] and cr['gpu_uuid']==gpu and cr['exit_code'] in (0,20,21) and (cr['exit_code']==0)==(status[arm]=='pass')
            if status[arm]=='pass':assert cr['valid']
            counts[arm]=json.loads((c/'result.work.json').read_text());counts[arm]['output_quality']=status[arm]
            if arm!='X':
                z=counts[arm];den=z['launched_scan_threads'] if arm=='S' else z['launched_leaf_threads'];num=z['active_scan_threads'] if arm=='S' else z['active_leaf_threads'];z['effective_payload_thread_fraction']=num/den if den else None;z['total_distance_calls']=z['node_distance_calls']+z['leaf_distance_calls']+z['scan_distance_calls']
        assert native['A']==native['R'],(kind,k,q)
        assert counts['A']['node_distance_calls']==counts['R']['node_distance_calls']
        assert counts['A']['leaf_distance_calls']==counts['R']['leaf_distance_calls']
        assert counts['A']['dp_cells']==counts['R']['dp_cells'] and counts['A']['coordinates']==counts['R']['coordinates']
        radius=None
        for g,order in enumerate(case['orders']):
            for arm in order:
                if arm not in timed:continue
                label=f'time_g{g}_{kind}_k{k}_q{q}_{arm}';r=epoch/label;rec=json.loads((r/'receipt.json').read_text());assert rec['valid'] and rec['gpu_uuid']==gpu and rec['exit_code']==0 and not rec['instrumented'] and rec['reps']==3 and rec['warmups']==3 and not rec['dump']
                assert (rec['label'],rec['kind'],rec['Q'],rec['k'],rec['arm'])==(label,kind,q,k,arm)
                assert rec['oracle_sha256']==frozen_inputs['fixtures/'+kind+'.oracle']
                assert rec['binary_sha256']==complete['binary_hashes'][Path(rec['command'][0]).name]
                for name,digest in rec['result_files'].items():assert Path(name).name==name and sha(r/name)==digest
                assert json.loads((r/'before.json').read_text())['idle'] and json.loads((r/'after.json').read_text())['idle']
                assert all(not x['foreign'] for x in json.loads((r/'checks.json').read_text()))
                meta=json.loads((r/'result.json').read_text());assert meta['correct'];radius=meta['radius'];setups[arm].append(meta)
                rows=list(csv.DictReader((r/'result.csv').open()));assert [int(x['iteration']) for x in rows]==[0,1,2]
                ms=[float(x['batch_ms']) for x in rows];assert all(x>0 and math.isfinite(x) for x in ms)
                process[arm].append(statistics.median(ms));samples[arm].extend(ms)
                for j,t in enumerate(ms):raw.append({'dataset':kind,'target_index':k,'Q':q,'round':g,'order':order,'arm':arm,'iteration':j,'batch_ms':t})
                result['receipts'][label]=sha(r/'receipt.json')
        ratios={f'R/{a}':paired(process['R'],process[a]) for a in arms if a!='R' and 'R' in timed and a in timed}
        for a in arms:
            if a=='R' or 'R/'+a not in ratios:continue
            split={str(before):[math.log(process['R'][g]/process[a][g]) for g,order in enumerate(case['orders']) if (order.index('R')<order.index(a))==before] for before in (True,False)}
            assert all(len(v)==3 for v in split.values())
            ratios['R/'+a]['order_split_geomean']={label:math.exp(statistics.mean(v)) for label,v in split.items()}
        rows={a:({'status':status[a],'process_medians_ms':process[a],'median_process_median_ms':statistics.median(process[a]),'marginal_p10_median_p90_ms':[percentile(samples[a],.1),statistics.median(samples[a]),percentile(samples[a],.9)],'mean_process_median_ms':statistics.mean(process[a]),'setup_build_capture_first_warmup':setups[a]} if a in timed else {'status':status[a],'median_process_median_ms':None,'process_medians_ms':[]}) for a in arms}
        result['cases'].append({'dataset':kind,'target':[10,100,1000][k],'radius':radius,'Q':q,'arms':rows,'quality_eligible':case.get('eligible',True),'ratios':ratios,'work_counts':counts,'native_ordered_output_sha256':native})
    rs=[c['ratios']['R/S']['paired_geomean'] for c in result['cases'] if 'R/S' in c['ratios']];ra=[c['ratios']['R/A']['paired_geomean'] for c in result['cases'] if 'R/A' in c['ratios']];rx=[c['ratios']['R/X']['paired_geomean'] for c in result['cases'] if 'R/X' in c['ratios']]
    eligible=sum(c['quality_eligible'] for c in result['cases']);system=eligible==18 and all(v<=1 for v in rs) and any(v<=.5 for v in rs)
    result['decision']={'eligible_cases':eligible,'quality_failed_cases':18-eligible,'system_paper_candidate_point_rule':system,'R_slower_than_S_cases':sum(v>1 for v in rs),'R_improves_A_cases':sum(v<1 for v in ra),'low_dimensional_close_all_cases_point_rule':len(rx)==9 and all(v>=5 for v in rx),'low_dimensional_cases_R_over_X_at_least_5':sum(v>=5 for v in rx),'mixed_low_dimensional_result':any(v>=5 for v in rx) and any(v<5 for v in rx),'no_new_algorithmic_novelty_claim':True,'incomplete_quality_is_not_universal_mechanism_rejection':True}
    (out/'RESULTS_COMPLETE.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'raw_samples.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(raw[0]),lineterminator='\n');w.writeheader();w.writerows(raw)
    print('COMPLETE',gpu,len(result['cases']),'cases',len(raw),'retained samples',result['decision'])
if __name__=='__main__':summarize(*sys.argv[1:])
