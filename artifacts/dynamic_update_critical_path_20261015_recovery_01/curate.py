"""Revalidate the completed fresh run; publish scalars,never private raw captures."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from common import HERE, REPO, load, save, sha, jobs
from campaign import prepared, STAGES
from quality import check, table
from audit_stage import census
from primary import compact, expand, analyze_compact
from analyze import run
from timeline import parse


def public_quality(job,checked):
    data=checked.get('parent_quality',checked)
    fields=('passed','complete_queries','complete_queries_including_warmup','formal_queries','false_negatives','false_positives',
        'exact_native_squared_bits','internal_FP64_bit_checks','internal_FP64_bit_mismatches','max_native_scaled_error','max_native_distance_scaled_error',
        'actual_transition_witnesses','actual_mutation_witnesses','independent_full_maps','independent_final_maps','final_device_vector_bytes_compared',
        'iterations','stream_slots','query_checks','empty_answers','full_hit_FP64_bit_checks','pointer_churn_epochs','max_batch','sanitizer_summary_zero')
    result=dict(job=job,**{key:data[key] for key in fields if key in data})
    if job['kind']=='copy':result['all_destination_bytes_compared']=checked['metadata']['all_destination_bytes_compared']
    return result


def bind_ranges(trace,expected):
    assert len(trace['ranges'])==len(expected),'Trace/operator ledger length mismatch'
    updates=0
    for actual,wanted in zip(trace['ranges'],expected):
        assert actual['operator']==wanted['operator'],'Trace/operator order mismatch'
        if actual['operator']=='Q':continue
        for field in ('copy_API_calls','sync_API_calls','H2D_activity_bytes','D2D_activity_bytes'):
            assert actual[field]==wanted[field],('Per-ACK trace accounting mismatch',actual['index'],field)
        assert actual['other_copy_activity_bytes']==actual['kernels']==actual['launch_API_calls']==actual['other_API_calls']==0
        updates+=1
    return updates


def traced_accounting(trace,job,checked,prefix):
    operators=trace['operators'];profile={}
    if job['kind']=='micro':
        rows=checked['operator_samples'];op=job['op'];kind={'I':1,'D':0,'R':2}[op];selected=[r for r in rows if int(r['kind'])==kind]
        native=[r for r in rows if int(r['kind'])<2]
        expected=[dict(operator='D' if int(r['kind'])==0 else 'I',copy_API_calls=int(r['copy_calls']),sync_API_calls=int(r['sync_calls']),
            H2D_activity_bytes=int(r['H2D_bytes']),D2D_activity_bytes=int(r['D2D_bytes'])) for r in native]
        trace['expected_update_binding']=dict(per_ACKs=bind_ranges(trace,expected),source='Independently validated native operator ledger;exact chronological API/payload counts')
        for name,code in (('D',0),('I',1)):
            wanted=[r for r in native if int(r['kind'])==code]
            if not wanted:assert name not in operators;continue
            assert operators[name]['ranges']==len(wanted)
            t=operators[name]['totals'];assert t['copy_API_calls']==sum(int(r['copy_calls']) for r in wanted) and t['sync_API_calls']==len(wanted)
            assert t['H2D_activity_bytes']==sum(int(r['H2D_bytes']) for r in wanted)
            assert t['D2D_activity_bytes']==sum(int(r['D2D_bytes']) for r in wanted) and t['other_copy_activity_bytes']==0
        assert set(operators)==({'I','D'} if op=='R' else {op})
        profile=dict(operator=op,batch=job['batch'],ACKs=len(selected),point_updates=job['K']*(2 if op=='R' else 1),
            total_ACK_ns=sum(float(r['ack_ms'])*1e6 for r in selected),mean_ACK_ms=float(np.mean([float(r['ack_ms']) for r in selected])),
            metadata=checked['metadata'])
    elif job['kind']=='service':
        rows=table(str(prefix)+'.ops.csv');meta=checked['parent_quality']['metadata']
        mutation_path=Path(str(prefix)+'.mutations.i32');mutations=np.fromfile(mutation_path,dtype='<i4').reshape(-1,8);at=0;expected=[]
        for row in rows:
            code=int(row['kind']);name=('D','I','Q')[code]
            if name=='Q':expected.append(dict(operator=name));continue
            count=int(row['rows']);witness=mutations[at:at+count];assert len(witness)==count and (witness[:,0]==code).all()
            copies=int((witness[:,5]>=0).sum()) if name=='D' else 1
            expected.append(dict(operator=name,copy_API_calls=copies,sync_API_calls=1,H2D_activity_bytes=count*3840 if name=='I' else 0,
                D2D_activity_bytes=copies*3840 if name=='D' else 0));at+=count
        assert at==len(mutations)
        trace['expected_update_binding']=dict(per_ACKs=bind_ranges(trace,expected),mutation_witnesses=len(mutations),mutation_sha256=sha(mutation_path),
            source='Independent ownership-replayed mutations,exact chronological per-ACK phase/API/payload checks')
        for name,kind in (('D',0),('I',1),('Q',2)):
            selected=[r for r in rows if int(r['kind'])==kind];assert operators[name]['ranges']==len(selected)
            profile[name]=dict(ACKs=len(selected),total_ACK_ns=sum(float(r['ack_ms'])*1e6 for r in selected),
                rows=sum(int(r['rows']) for r in selected))
        assert operators['D']['totals']['sync_API_calls']==profile['D']['ACKs'] and operators['I']['totals']['sync_API_calls']==profile['I']['ACKs']
        assert operators['I']['totals']['copy_API_calls']==profile['I']['ACKs']
        assert operators['I']['totals']['H2D_activity_bytes']==meta['insert_H2D_request_bytes']
        assert operators['D']['totals']['D2D_activity_bytes']==meta['swap_D2D_request_bytes']
        assert meta['swap_D2D_request_bytes']%3840==0 and operators['D']['totals']['copy_API_calls']==meta['swap_D2D_request_bytes']//3840
        profile['metadata']={key:meta[key] for key in ('service_ms','events_ms','release_ms','query_ms','update_ms_including_statistics','other_ms','cpu_events_user_s','cpu_events_system_s')}
    else:
        for name,kind in (('H2D',0),('D2D',1)):
            rows=[r for r in checked['samples'] if int(r['kind'])==kind];assert operators[name]['ranges']==len(rows)==16
            t=operators[name]['totals'];assert t['copy_API_calls']==t['sync_API_calls']==16 and t[name+'_activity_bytes']==16*(1<<30)
            profile[name]=dict(ACKs=16,total_ACK_ns=sum(float(r['ack_ms'])*1e6 for r in rows))
    return profile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--refused-record',type=Path,required=True);a=parser.parse_args()
    w=a.work.resolve();out=a.out.resolve();assert not out.exists();reg,ready=prepared(w);c=load(HERE/'CONTRACT.json');amend=load(HERE/'PLACEMENT_RECOVERY.json')
    assert amend['human_authorized'] and amend['cumulative_max_starts']==209 and amend['fresh_work_max_starts']==124 and amend['base_contract_sha256']==sha(HERE/'CONTRACT.json')
    frozen=load(w/'ANALYSIS_FREEZE.json');assert frozen['before_primary'] and frozen['analyzer_sha256']==sha(HERE/'analyze.py') and frozen['contract_sha256']==sha(HERE/'CONTRACT.json')
    for path,h in reg['inputs'].items():assert sha(path)==h
    records=[];qualities=[];primary=[];primary_full=[];traces={};stage_census={};ledger=[]
    for stage in STAGES:
        result=load(w/stage/'RESULTS.json');expected=jobs(stage);registered=load(w/stage/'REGISTERED.json')
        assert result['complete'] and registered['jobs']==expected and registered['executor_sha256']==sha(HERE/'campaign.py') and registered['contract_sha256']==sha(HERE/'CONTRACT.json')
        stage_census[stage]=census(w,stage,expected,result['rows'],reg)
        for job,row in zip(expected,result['rows']):
            label=job['label'];assert row['status']=='passed' and all(row[key]==value for key,value in job.items());g=w/stage/'guards'/label
            receipt=load(g/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['gpu']==reg['gpu']
            assert receipt['observer']=='two-sided-starttime-v1'
            assert receipt['binary_sha256']==sha(load(w/stage/(label+'.command.json'))['command'][0]) and sha(g/'receipt.json')==row['guard_sha256']
            for name,h in row['guard_files'].items():assert sha(g/name)==h
            for name,r in row['reports'].items():assert sha(w/stage/'reports'/name)==r['sha256'] and (w/stage/'reports'/name).stat().st_size==r['bytes']
            assert not load(g/'before.json')['apps'] and not load(g/'after.json')['apps'] and all(not x['foreign'] for x in load(g/'checks.json'))
            original=load(w/stage/(label+'.checked.json'));assert sha(w/stage/(label+'.checked.json'))==row['checked_sha256']
            if job['kind']=='selftest':assert original['passed'] and original['query_checks']==400 and original['iterations']==100 and original['stream_slots']==2
            else:
                current=check(w/stage/'outputs'/label,job,w,reg);assert current==original,('Offline quality drift',label)
            if job.get('tool') in ('memcheck','racecheck','synccheck'):
                text=(g/'stdout.log').read_text()+(g/'stderr.log').read_text();assert original['sanitizer_summary_zero'] and ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text)
            qualities.append(public_quality(job,original));records.append(dict(stage=stage,label=label,checked_sha256=row['checked_sha256'],guard_sha256=row['guard_sha256'],guard_files=row['guard_files'],reports=row['reports'],raw_outputs=original.get('raw_outputs',{})))
            ledger.append((stage,label,sha(w/stage/(label+'.command.json'))))
            if stage=='primary':
                packed=compact(job,original);primary.append(packed);primary_full.append(dict(job=job,**original))
                assert expand(packed)['job']==job
            if stage=='timeline':
                trace=parse(w/stage/'reports'/(label+'.sqlite'));trace['profiled_ACK']=traced_accounting(trace,job,original,w/stage/'outputs'/label)
                trace['job']=job;traces[label]=trace
            print('VERIFIED',stage,label,flush=True)
    starts=[json.loads(line) for line in (w/'STARTS.jsonl').read_text().splitlines()]
    assert len(starts)==124 and [r['start'] for r in starts]==list(range(1,125))
    assert [(r['stage'],r['label'],r['command_sha256']) for r in starts]==ledger
    root=w.parent;refused=load(a.refused_record);assert refused['guard_starts']==1 and refused['CUDA_targets_started']==0
    assert len((root/'work_r2_final/STARTS.jsonl').read_text().splitlines())==1 and not list((root/'work_r2').glob('STARTS*'))
    for name,h in load(root/'TOOLS_BEFORE_NSYS_R2.json')['files'].items():assert sha(name)==h
    timing=analyze_compact(primary);assert timing==run(primary_full)
    out.mkdir();[(out/name).mkdir() for name in ('evidence','results','timeline')]
    with (out/'evidence/PRIMARY_SCALARS.json').open('x') as f:json.dump(primary,f,separators=(',',':'));f.write('\n')
    save(out/'results/TIMING.json',timing)
    save(out/'evidence/QUALITY.json',dict(passed=True,GPU_processes=124,nonselftest_processes=116,selftests=8,records=qualities,
        no_concurrency_Graph_or_production_admission=True,scope='Every target answer/field,actual occurrence replay,full final maps and every final device-vector byte;small-N sanitizer scope explicitly limited.'))
    save(out/'evidence/RECEIPTS.json',records);save(out/'evidence/STAGE_CENSUS.json',stage_census)
    trace_summary={}
    for label,trace in traces.items():
        rows=trace.pop('ranges')
        with (out/'timeline'/(label+'.csv')).open('x') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        trace_summary[label]=trace
    save(out/'results/TIMELINES.json',trace_summary)
    save(out/'evidence/IDENTITY.json',dict(contract_sha256=sha(HERE/'CONTRACT.json'),placement_amendment_sha256=sha(HERE/'PLACEMENT_RECOVERY.json'),
        executed_sources=reg['sources'],generated=reg['generated'],binaries=ready['binaries'],parent_binaries=ready['parent_binaries'],libraries=ready['libraries'],
        registration_sha256=sha(w/'REGISTERED.json'),ready_sha256=sha(w/'READY.json'),STATIC=load(w/'STATIC.json'),analysis_freeze=frozen,
        postprocessing_sources={name:sha(HERE/name) for name in ('curate.py','audit_stage.py','primary.py','timeline.py')},
        data_sha256=c['data_sha256'],mean_sha256=c['means_sha256'],qids=c['qids'],radius=c['radius'],placement='One idle same-model GPU with matched NUMA;physical identifiers private;no settings changed.'))
    save(out/'evidence/EXECUTION.json',dict(complete=True,accepted_fresh_GPU_processes=124,stage_counts=dict(qualification=29,primary=84,timeline=11),
        R1_preserved_starts=84,R2_refused_admission_starts=1,R2_total_admission_attempts=125,total_campaign_starts=209,max_campaign_starts=209,
        refused_attempt_CUDA_targets=0,automatic_retries=0,all_fresh_two_sided_isolation_valid=True,start_ledger_sha256=sha(w/'STARTS.jsonl'),
        refused_attempt_record_sha256=sha(a.refused_record),pre_GPU_revision_record_sha256=sha(root/'PRE_GPU_REVISION_R2.json'),
        stage_results_sha256={s:sha(w/s/'RESULTS.json') for s in STAGES}))
    raw={str(p.relative_to(w)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(w.rglob('*')) if p.is_file() and p.name!='campaign.lock'}
    save(out/'evidence/RAW_MANIFEST.json',dict(scope='External private raw work tree,all guards/answers and original NSYS captures;hashes only.',files=raw))
    print('CURATED124/124;209 total preserved attempts;exact scalar reconstruction;all raw outputs revalidated;no R1 headline reuse',flush=True)


if __name__=='__main__':main()
