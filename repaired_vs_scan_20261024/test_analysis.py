"""Synthetic CPU-only estimator/eligibility test; never a benchmark observation."""
import csv,hashlib,json,math,tempfile
from pathlib import Path
from analyze_campaign import summarize
from campaign_quality_support_v4 import THREE,FOUR

def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    with tempfile.TemporaryDirectory(prefix='analysis_test_',dir=Path(__file__).resolve().parent) as t:
        root=Path(t);epoch=root/'runs/epoch';epoch.mkdir(parents=True);gpu='SYNTHETIC-NOT-A-GPU';bins={a:'hash-'+a for a in 'ARSX'};full={};schedule=[]
        write(epoch/'TIMING_COMPLETE.json',{'gpu_uuid':gpu,'rounds':6,'binary_hashes':bins,'state':'synthetic_test_only'})
        for fn in ['GATES_PASS.json','COUNT_COLLECTED.json']:write(epoch/fn,{})
        write(epoch/'frozen_inputs_verified.json',{'fixtures/words.oracle':'oracle-words','fixtures/tloc.oracle':'oracle-tloc'})
        for kind in ['words','tloc']:
            for k in range(3):
                for q in [1,32,1024]:
                    arms='ARS' if kind=='words' else 'ARSX';failed=kind=='tloc' and k==2 and q==1024;quality={a:('correctness_failed' if failed and a!='X' else 'pass') for a in arms};timed='X' if failed else arms
                    case={'kind':kind,'k':k,'Q':q,'orders':THREE if kind=='words' else FOUR,'quality':quality,'eligible':not failed,'timed_arms':timed};schedule.append(case)
                    for a in arms:
                        label=f'full_{kind}_k{k}_q{q}_{a}';r=epoch/label;r.mkdir();(r/'result.native.bin').write_bytes(b'synthetic equal A/R bytes')
                        rec={'valid':quality[a]=='pass','gpu_uuid':gpu,'exit_code':0 if quality[a]=='pass' else 20};write(r/'receipt.json',rec);full[label]={'path':str(r.relative_to(root))}
                        c=epoch/f'count_{kind}_k{k}_q{q}_{a}';c.mkdir();write(c/'receipt.json',{**rec,'instrumented':True})
                        counts={'node_distance_calls':1,'leaf_distance_calls':2,'dp_cells':3,'coordinates':4,'candidate_leaves':5,'active_leaf_threads':6,'launched_leaf_threads':8,'scan_distance_calls':7,'active_scan_threads':8,'launched_scan_threads':8} if a!='X' else {'native_point_predicate_tests':4,'coordinates':8,'effective_thread_fraction':None}
                        write(c/'result.work.json',counts)
                    for g,order in enumerate(case['orders']):
                        for a in order:
                            if a not in timed:continue
                            label=f'time_g{g}_{kind}_k{k}_q{q}_{a}';r=epoch/label;r.mkdir()
                            data={'A':[9,10,100],'R':[1,2,3],'S':[.5,1,1.5],'X':[.4,.5,.6]}[a]
                            if a=='A':data=[v*2**g for v in data]
                            with (r/'result.csv').open('w') as f:
                                w=csv.writer(f);w.writerow(['iteration','batch_ms']);w.writerows(enumerate(data))
                            write(r/'result.json',{'correct':True,'radius':k+1})
                            for name in ['before.json','after.json']:write(r/name,{'idle':True})
                            write(r/'checks.json',[{'foreign':[]}])
                            write(r/'receipt.json',{'label':label,'kind':kind,'Q':q,'k':k,'arm':a,'valid':True,'gpu_uuid':gpu,'exit_code':0,'instrumented':False,'reps':3,'warmups':3,'dump':False,'oracle_sha256':'oracle-'+kind,'binary_sha256':bins[a],'command':['/bin/'+a],'result_files':{p.name:sha(p) for p in r.glob('result*')}})
        write(epoch/'FULL_QUALITY.json',{'evidence':full});write(epoch/'TIMING_SCHEDULE.json',schedule)
        out=root/'summary';summarize(epoch,out);r=json.loads((out/'RESULTS_COMPLETE.json').read_text())
        assert r['decision']['eligible_cases']==17 and r['decision']['quality_failed_cases']==1
        assert len(list(csv.DictReader((out/'raw_samples.csv').open())))==1080
        for c in r['cases']:
            if c['quality_eligible']:
                assert c['ratios']['R/S']['paired_geomean']==2 and c['ratios']['R/S']['CI95']==[2,2]
                assert abs(c['ratios']['R/A']['paired_geomean']-.2/2**2.5)<1e-14
            else:
                assert c['ratios']=={} and c['arms']['R']['median_process_median_ms'] is None and c['arms']['X']['median_process_median_ms']==.5
        p=epoch/'time_g0_words_k0_q1_A/receipt.json';rec=json.loads(p.read_text());rec['Q']=32;write(p,rec)
        try:summarize(epoch,root/'bad_summary')
        except AssertionError:pass
        else:raise AssertionError('wrong-workload timing receipt accepted')
    print('PASS synthetic full-matrix process medians/log-t, raw samples, failed-arm exclusion and identity binding; no GPU calls')
if __name__=='__main__':main()
