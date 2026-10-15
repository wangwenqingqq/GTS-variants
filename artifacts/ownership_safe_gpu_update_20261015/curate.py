"""Offline full-raw revalidation,process statistics and diagnostic custody;0 GPU starts."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,csv,importlib.util,json,subprocess,os,collections,re
from pathlib import Path
import numpy as np
from common import HERE,BASE,UPDATES,jobs,load,save,sha,module
from campaign import prepared,command
from logical_quality import table
import analyze,scalars
import postcheck
from timeline import parse,bind
from verify import ack_inventory

GUARD={'command.json','before.json','after.json','checks.json','receipt.json','stdout.log','stderr.log','gpu.csv'}
old_census=module('old_output_census',BASE/'audit_stage.py')
quality_fields=('passed','complete_queries','complete_queries_including_warmup','formal_queries','false_negatives','false_positives',
    'exact_native_squared_bits','internal_FP64_bit_checks','internal_FP64_bit_mismatches','max_native_scaled_error','max_native_distance_scaled_error',
    'actual_transition_witnesses','actual_mutation_witnesses','independent_full_maps','independent_final_maps','final_device_vector_bytes_compared',
    'query_checks','sanitizer_summary_zero','full_capacity_bit_cases','invalid_atomic_rejections','synthetic_D')

def names(job):
    label=job['label']
    if job['kind']=='shape':return {label+'.shape.csv',label+'.meta.json'}
    result=old_census.output_names(job)
    if job['kind']!='selftest' and job['update'] in UPDATES:
        result|={label+'.physical.csv',label+'.capacity.json'}
        if job['diagnostic']==2:result.add(label+'.ack_oracle.json')
    return result

def reports(job):
    return {job['label']+s for s in ('.nsys-rep','.sqlite')} if job.get('tool')=='nsys' else {job['label']+'.csv'} if job.get('tool')=='ncu' else set()

def linked_libraries(binary,environment):
    text=subprocess.check_output(['ldd',str(binary)],text=True,env={**os.environ,**environment});assert 'not found' not in text
    result={}
    for line in text.splitlines():
        parts=line.split()
        if '=>' in parts and len(parts)>2 and parts[2].startswith('/'):result[parts[0]]=sha(parts[2])
    return result

def portable_build(reg,w,parent):
    roots={str(w):'WORK',str(parent):'PARENT_WORK'};tokens=[t for cmd in reg['commands'].values() for t in cmd]
    cuda=Path(tokens[0]).parent.parent;roots[str(cuda)]='CUDA_ROOT';includes={};additional_searches={}
    for token in tokens:
        if token.startswith('-L'):
            path=Path(token[2:]);package=path.parent.name
            assert package in ('libcuvs','librmm','rapids_logger');roots[str(path.parent)]=package.upper()+'_ROOT'
            if package=='libcuvs':includes['LIBCUVS_ROOT']={str(p.relative_to(path.parent)):sha(p) for p in (path.parent/'include').rglob('*') if p.is_file()}
    for token in tokens:
        if not token.startswith('-I'):continue
        path=Path(token[2:])
        if any(str(path).startswith(k+'/') or str(path)==k for k in roots):continue
        if (path/'nvtx3/nvToolsExt.h').is_file():
            roots[str(path)]='NVTX_INCLUDE';includes['NVTX_INCLUDE']={str(p.relative_to(path)):sha(p) for p in (path/'nvtx3').rglob('*') if p.is_file()}
        elif (path/'dlpack/dlpack.h').is_file():
            roots[str(path)]='DLPACK_INCLUDE';includes['DLPACK_INCLUDE']={str(p.relative_to(path)):sha(p) for p in (path/'dlpack').rglob('*') if p.is_file()}
        else:
            name='ADDITIONAL_INCLUDE_'+str(len(additional_searches));roots[str(path)]=name
            additional_searches[name]=dict(exists_at_postprocessing=path.is_dir(),header_identity_not_snapshotted=True)
    if (cuda/'include/nvtx3/nvToolsExt.h').is_file():includes['CUDA_ROOT']={str(p.relative_to(cuda)):sha(p) for p in (cuda/'include/nvtx3').rglob('*') if p.is_file()}
    for i,path in enumerate(reg['environment']['LD_LIBRARY_PATH'].split(':')):
        if not any(path==k or path.startswith(k+'/') for k in roots):roots[path]='LD_LIBRARY_DIR_'+str(i)
    def clean(text):
        for prefix,name in sorted(roots.items(),key=lambda x:-len(x[0])):text=text.replace(prefix,'${'+name+'}')
        assert not any(part in text for part in ('/home/','/Users/','/tmp/','GPU-'))
        return text
    allowed={'LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PDX_MEANS','PYTHONDONTWRITEBYTECODE'}
    assert set(reg['environment'])==allowed
    return dict(commands={k:[clean(t) for t in v] for k,v in reg['commands'].items()},environment={k:clean(v) for k,v in reg['environment'].items()},
        variables=sorted(set(roots.values())),external_include_hashes=includes,additional_include_searches=additional_searches,
        scope='Exact executed flags and environment with installation roots replaced by variables;resolve shared objects by the recorded SONAME hashes.')

def process_scalar(job,checked,prefix):
    result=scalars.compact(job,checked)
    if job['kind']=='service':
        meta=checked['parent_quality']['metadata'];ops=table(str(prefix)+'.ops.csv')
        result['service_detail']={k:v for k,v in meta.items() if isinstance(v,(int,float,bool))}
        result['operator_detail']={name:dict(ACKs=len(a),mean_ACK_ms=float(np.mean(a)),p50_ACK_ms=float(np.quantile(a,.5)),p95_ACK_ms=float(np.quantile(a,.95)),total_ACK_ms=float(np.sum(a)))
            for code,name in enumerate(('D','I','Q')) for a in [[float(r['ack_ms']) for r in ops if int(r['kind'])==code]]}
    else:result['metadata']=checked['metadata']
    if 'physical_operators' in checked:
        rows=checked['physical_operators']
        result['physical']={name:dict(ACKs=len(selected),**{key:sum(int(r[key]) for r in selected) for key in rows[0] if key not in ('kind','rows')},rows=sum(int(r['rows']) for r in selected))
            for code,name in enumerate(('D','I')) if (selected:=[r for r in rows if int(r['kind'])==code])}
    return result

def ncu(path,job,prefix=None):
    text=Path(path).read_text();lines=text.splitlines();at=next(i for i,line in enumerate(lines) if line.startswith('"ID",'))
    rows=list(csv.DictReader(lines[at:]));assert rows
    expected={'dram__bytes_read.sum','dram__bytes_write.sum','lts__t_sectors_op_read.sum','lts__t_sectors_op_write.sum'}
    launches={}
    for row in rows:
        if row.get('Metric Name') not in expected:continue
        key=row['ID'];entry=launches.setdefault(key,dict(kernel=row['Kernel Name'],metrics={},exported={}))
        name=row['Metric Name'];assert name not in entry['metrics'];unit=row['Metric Unit']
        if row['Metric Value']=='n/a':assert unit=='';entry['metrics'][name]=None
        else:
            value=float(row['Metric Value'].replace(',',''));assert np.isfinite(value) and value>=0
            scale={'byte':1.,'Kbyte':1000.,'Mbyte':1e6,'Gbyte':1e9,'sector':1.}[unit];entry['metrics'][name]=value*scale
        entry['exported'][name]=dict(unit=unit,value=row['Metric Value'])
    assert launches and all(set(r['metrics'])==expected for r in launches.values())
    query=job['kind']=='service'
    assert all(('progressive_' if query else 'materialize_final') in r['kernel'] for r in launches.values())
    kernel_counts=collections.Counter(r['kernel'] for r in launches.values())
    if query:
        assert prefix is not None
        stages=table(str(prefix)+'.stages.csv');queries=table(str(prefix)+'.queries.csv')
        wanted={f'stage_{a}_{b}':sum(int(r['invocation'])>=8 and int(r['stage'])==i and int(r['input'])>0 for r in stages) for i,(a,b) in enumerate(((0,128),(128,256),(256,512),(512,960)),1)}
        wanted['fields']=sum(int(r['phase'])>=0 and int(r['count'])>0 for r in queries)
        assert sum(int(r['phase'])>=0 for r in queries)==160
        actual=collections.Counter()
        for kernel,count in kernel_counts.items():
            match=re.search(r'progressive_stage<\s*(\d+)\s*,\s*(\d+)\s*>',kernel)
            key=f'stage_{match[1]}_{match[2]}' if match else 'fields'
            if not match:assert 'progressive_fields' in kernel
            actual[key]+=count
        assert set(actual)<=set(wanted) and {k:actual[k] for k in wanted}==wanted,('NCU capture/validated nonempty-stage census mismatch',dict(actual),wanted)
    else:assert len(launches)==16;wanted={'materialize_final':16}
    total={name:None if any(r['metrics'][name] is None for r in launches.values()) else sum(r['metrics'][name] for r in launches.values()) for name in sorted(expected)}
    warning_lines=[line for line in lines[:at] if line.startswith('==WARNING==')]
    known=('==WARNING== Note: Running with uncontrolled GPU caches. Profiling results may be inconsistent.','==WARNING== Note: Running with unmodified GPU clocks. If not controlled otherwise, profiling results may be inconsistent.')
    assert set(warning_lines)<=set(known),'Unreviewed NCU warning'
    return dict(job=job,launches=len(launches),totals=total,per_query={k:None if v is None else v/160 for k,v in total.items()} if query else None,
        per_update_ACK={k:None if v is None else v/16 for k,v in total.items()} if not query else None,source_sha256=sha(path),
        scope='Selected application kernels only;launch counts bound to validated nonempty progressive-stage inputs and nonempty answer counts over160queries. Empty stages/fields are not launched. Update metrics exclude memcpy/H2D/CPU. NCU replay is not native latency.',
        kernel_counts=dict(kernel_counts),expected_launches_from_validated_outputs=wanted,warnings=['uncontrolled GPU caches' if 'caches' in line else 'unmodified GPU clocks' for line in warning_lines],
        unavailable_metrics=[k for k,v in total.items() if v is None],unavailable_is_not_zero=True,
        all_launches=list(launches.values()),cache_control='none',clock_control='none',unit_scaling='NVIDIA SI prefixes:K=1000,M=1000000,G=1000000000;original exported strings/units retained.')

def extensions(packed,shape_records,calibration):
    result=dict(shapes={},calibration={},service_detail={})
    for shape in ('random','localized','chain'):
        for d in (128,960):
            cell={}
            for u in UPDATES:
                records=[r for r in shape_records if r['job']['shape']==shape and r['job']['update']==u];assert len(records)==6
                metrics=[]
                for r in records:
                    selected=[s for s in r['samples'] if int(s['D'])==d];ack=np.array([float(s['ACK_ms']) for s in selected]);assert len(ack)==32
                    metrics.append(dict(mean_ACK_ms=float(ack.mean()),p50_ACK_ms=float(np.quantile(ack,.5)),p95_ACK_ms=float(np.quantile(ack,.95)),
                        native_moves=int(selected[0]['native_moves']),compiled_rows=int(selected[0]['compiled_rows'])))
                cell[u]={k:analyze.distribution([m[k] for m in metrics]) for k in metrics[0]}
            cell['comparisons']={f'{b}_over_{a}':analyze.compare(cell[a]['mean_ACK_ms']['process_values'],cell[b]['mean_ACK_ms']['process_values']) for a,b in (('NATIVE','WAVES'),('NATIVE','FINAL'),('WAVES','FINAL'))}
            result['shapes'][f'{shape}_D{d}']=cell
    for u in UPDATES:
        for b in (1,512):
            plain=[r['micro']['mean_ACK_ms'] for r in packed if r['job']['kind']=='micro' and r['job']['op']=='R' and r['job']['batch']==b and r['job']['update']==u]
            marked=[r['micro']['mean_ACK_ms'] for r in calibration if r['job']['batch']==b and r['job']['update']==u]
            result['calibration'][f'{u}_MARKED_over_PLAIN_R_{b}']=analyze.compare(plain,marked)
    for u in ('S1','CURRENT','NATIVE','WAVES','FINAL'):
        selected=[r for r in packed if r['job']['kind']=='service' and r['job']['update']==u];assert len(selected)==6
        result['service_detail'][u]=dict(metadata={k:analyze.distribution([r['service_detail'][k] for r in selected]) for k in selected[0]['service_detail']},
            operators={op:{k:analyze.distribution([r['operator_detail'][op][k] for r in selected]) for k in selected[0]['operator_detail'][op]} for op in ('D','I','Q')})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    w=a.work.resolve();root=w.parent;assert not a.out.exists();reg,ready=prepared(w)
    parent=Path(reg['parent']);parent_ready=load(parent/'READY.json')
    assert sha(w/'build/replay.so')==ready['replay_sha256']
    assert sha(parent/'build/replay.so')==parent_ready['replay_binary_sha256']
    replay_identity=dict(fresh=ready['replay_sha256'],parent=parent_ready['replay_binary_sha256'],both_verified_before_full_offline_revalidation=True)
    for name,expected in ready['libraries'].items():assert linked_libraries(w/'build'/name/'service',reg['environment'])==expected
    for name in ('S1','S2_STALE'):assert linked_libraries(parent/'build'/name/'service',reg['environment'])=={k:v['sha256'] for k,v in parent_ready['libraries'].items()}
    parent_registration=load(parent/'REGISTERED.json');reference=Path(parent_registration['reference']);portable_inputs={}
    for name,h in reg['inputs'].items():
        path=Path(name);assert sha(path)==h
        if path==Path(reg['data']):key='dataset/GIST1M.f32bin'
        elif path.is_relative_to(parent):key='parent/'+str(path.relative_to(parent))
        else:assert path.is_relative_to(reference);key='reference/'+str(path.relative_to(reference))
        assert key not in portable_inputs;portable_inputs[key]=dict(sha256=h,bytes=path.stat().st_size)
    spec=importlib.util.spec_from_file_location('qualified_CPU_validator',a.validator);validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    auth=load(root/'CONTINUATION_AUTHORIZATION.json');assert auth['corrected_validator_sha256']==sha(a.validator)
    admission=load(w/'QUALIFICATION_ADMISSION.json');assert admission['passed'] and admission['unique_qualified_targets']==42 and admission['prior_targets_reexecuted']==0
    old_result=load(w/'qualification/RESULTS.json');assert [r['status'] for r in old_result['rows']]==['passed']*15+['failed']+['not_executed']*26
    assert sha(w/'qualification/RESULTS.json')==admission['original_failure_sha256']
    second=load(root/'CONTINUATION_PRIMARY_AUTHORIZATION.json');primary_admission=load(w/'PRIMARY_ADMISSION.json')
    assert second['human_authorized'] and second['campaign_max_starts']==341 and second['prior_starts']==93 and second['same_gpu_required']
    assert sha(w/'primary/RESULTS.json')==second['original_primary_failure_sha256']==primary_admission['original_result_sha256']
    assert primary_admission['passed'] and primary_admission['unique_qualified_primary_targets']==192 and primary_admission['passed_targets_reexecuted']==0
    assert [r['status'] for r in load(w/'primary/RESULTS.json')['rows']]==['passed']*44+['failed']+['not_executed']*147
    schedule=[('qualification',jobs('qualification')[:16]),('qualification_recovery_01',jobs('qualification')[16:]),('screen',jobs('screen')),
        ('primary',jobs('primary')[:45]),('primary_recovery_02',jobs('primary')[44:])]+[(s,jobs(s)) for s in ('shapes','calibration','profile')]
    receipts=[];qualities=[];ledger=[];packed=[];full=[];shapes=[];calibration=[];traces={};ncus={};census={}
    for stage,expected in schedule:
        folder=w/stage;result=load(folder/'RESULTS.json');registered=load(folder/'REGISTERED.json')
        assert registered['executor_sha256']==sha(HERE/'campaign.py') and registered['contract_sha256']==sha(HERE/'CONTRACT.json')
        old_stage=stage in ('qualification','primary')
        if old_stage:assert not result['complete'] and registered['jobs']==jobs(stage)
        else:assert result['complete'] and registered['jobs']==expected
        labels=[j['label'] for j in expected]
        assert not any(p.is_symlink() for p in folder.rglob('*'))
        exact=old_census.exact_directory
        checked_labels=labels[:-1] if old_stage else labels
        exact(folder,{'REGISTERED.json','RESULTS.json'}|{l+s for l in labels for s in ('.command.json','.outer.log')}|{l+'.checked.json' for l in checked_labels},('guards','outputs','reports'))
        wanted_outputs=set().union(*(names(j) for j in expected[:-1] if stage=='primary')) if stage=='primary' else set().union(*(names(j) for j in expected))
        if stage=='primary':wanted_outputs|={p.name for p in (folder/'outputs').glob(expected[-1]['label']+'.*')}
        exact(folder/'guards',(),labels);exact(folder/'outputs',wanted_outputs);exact(folder/'reports',set().union(*(reports(j) for j in expected)))
        for index,job in enumerate(expected):
            row=result['rows'][index];label=job['label'];assert all(row[k]==v for k,v in job.items());g=folder/'guards'/label;prefix=folder/'outputs'/label
            cmd=command(job,w,reg,prefix);assert load(folder/(label+'.command.json'))==dict(command=cmd)
            ledger.append((stage,label,sha(folder/(label+'.command.json'))))
            receipt=load(g/'receipt.json')
            assert receipt['observer']=='two-sided-starttime-v1' and receipt['binary_sha256']==sha(cmd[0])
            assert load(g/'command.json')==receipt['command']==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
            assert {p.name for p in g.iterdir()}==GUARD
            if stage=='primary' and index==44:
                assert row['status']=='failed' and not receipt['runtime_valid'] and receipt['stop_reason']=='foreign GPU activity' and receipt['gpu']==reg['gpu']==second['gpu']
                assert any(c['foreign'] for c in load(g/'checks.json'))
                receipts.append(dict(stage=stage,label=label,original_status='failed',admitted=False,reason='foreign GPU activity',guard_files={p.name:sha(p) for p in g.iterdir()},
                    raw_outputs={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in prefix.parent.glob(prefix.name+'.*')}))
                continue
            assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['gpu']==reg['gpu']
            assert not load(g/'before.json')['apps'] and not load(g/'after.json')['apps'] and all(not c['foreign'] for c in load(g/'checks.json'))
            checked_path=root/'OFFLINE_REVIEW_R1'/(label+'.checked.json') if stage=='qualification' else folder/(label+'.checked.json')
            original=load(checked_path);physical_proof=None
            if job['kind']=='selftest':
                assert original['passed'] and original['query_checks']==400 and original['full_capacity_bit_cases']==180 and original['invalid_atomic_rejections']==6
            else:
                current=validator.check(prefix,job,w,reg);assert current==original,('Offline quality drift',stage,label)
                assert set(original['raw_outputs'])==names(job)
                if job['update'] in UPDATES and job['kind'] in ('micro','service'):physical_proof=postcheck.check(prefix,job)
                if job.get('diagnostic')==2 and job['update'] in UPDATES:
                    mutation=np.fromfile(str(prefix)+'.mutations.i32',dtype='<i4').reshape(-1,8)
                    assert ack_inventory(mutation,original['physical_operators'],job)==original['per_ACK_oracle']
            if job.get('tool') in ('memcheck','racecheck','synccheck'):
                text=(g/'stdout.log').read_text()+(g/'stderr.log').read_text();assert original['sanitizer_summary_zero'] and ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text)
            hashes={p.name:sha(p) for p in g.iterdir() if p.is_file()}
            if row['status']=='passed':
                assert hashes==row['guard_files'] and sha(g/'receipt.json')==row['guard_sha256']
                assert sha(folder/(label+'.checked.json'))==row['checked_sha256']
                for name,v in row['reports'].items():assert sha(folder/'reports'/name)==v['sha256'] and (folder/'reports'/name).stat().st_size==v['bytes']
            else:assert stage=='qualification' and index==15 and row['status']=='failed'
            data=original.get('parent_quality',original)
            qualities.append(dict(stage=stage,job=job,**{k:data[k] for k in quality_fields if k in data},strict_capacity=original.get('strict_capacity'),per_ACK_oracle=original.get('per_ACK_oracle'),physical_witness_proof=physical_proof))
            receipts.append(dict(stage=stage,label=label,original_status=row['status'],admitted=True,guard_files=hashes,checked_sha256=sha(checked_path),raw_outputs=original.get('raw_outputs',{})))
            if stage in ('primary','primary_recovery_02'):packed.append(process_scalar(job,original,prefix));full.append(dict(job=job,checked=original))
            if stage=='shapes':shapes.append(dict(job=job,samples=original['samples']))
            if stage=='calibration':calibration.append(scalars.compact(job,original))
            if stage=='profile':
                if job['tool']=='nsys':
                    trace=parse(folder/'reports'/(label+'.sqlite'),job['update']);physical=original['physical_operators']
                    ops=['D' if int(r['kind'])==0 else 'I' for r in original['operator_samples'] if int(r['kind'])<2] if job['kind']=='micro' else [('D','I','Q')[int(r['kind'])] for r in table(str(prefix)+'.ops.csv')]
                    bind(trace,physical,ops);trace['job']=job;trace['native_timing_not_replaced']=True
                    if job['kind']=='micro':trace['profiled_ACK']=analyze.micro(original,job)
                    else:trace['profiled_service']={k:original['parent_quality']['metadata'][k] for k in scalars.SERVICE_FIELDS}
                    traces[label]=trace
                else:ncus[label]=ncu(folder/'reports'/(label+'.csv'),job,prefix)
            print('REVALIDATED',stage,label,flush=True)
        census[stage]=dict(launch_attempts=len(expected),admitted_targets=len(expected)-int(stage=='primary'),source_derived_commands=True,exact_stage_entries=True)
    starts=[json.loads(line) for line in (w/'STARTS.jsonl').read_text().splitlines()]
    assert len(starts)==341 and [r['start'] for r in starts]==list(range(1,342))
    assert [(r['stage'],r['label'],r['command_sha256']) for r in starts]==ledger
    assert [r['job'] for r in packed]==jobs('primary')
    timing=analyze.run(full);assert timing==scalars.run(packed)
    assert sum(r['physical_witness_proof'] is not None for r in qualities)==262
    assert sha(w/'build/replay.so')==replay_identity['fresh'] and sha(parent/'build/replay.so')==replay_identity['parent']
    a.out.mkdir();[(a.out/d).mkdir() for d in ('evidence','results','timeline')]
    save(a.out/'evidence/PRIMARY_SCALARS.json',packed);save(a.out/'evidence/SHAPE_SCALARS.json',shapes);save(a.out/'evidence/CALIBRATION_SCALARS.json',calibration)
    save(a.out/'evidence/INPUT_IDENTITY.json',dict(files=portable_inputs,scope='Portable names and hashes;large data,reference matrices and cached vectors remain external.'))
    save(a.out/'evidence/BUILD.json',portable_build(reg,w,parent))
    save(a.out/'results/TIMING.json',timing);save(a.out/'results/EXTENSIONS.json',extensions(packed,shapes,calibration));save(a.out/'results/NCU.json',ncus)
    for label,trace in traces.items():
        rows=trace.pop('ranges')
        with (a.out/'timeline'/(label+'.csv')).open('x') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    save(a.out/'results/TIMELINES.json',traces)
    save(a.out/'evidence/QUALITY.json',dict(passed=True,unique_GPU_targets=340,records=qualities,concurrency_Graph_and_production_admitted=False))
    save(a.out/'evidence/RECEIPTS.json',receipts);save(a.out/'evidence/STAGE_CENSUS.json',census)
    save(a.out/'evidence/IDENTITY.json',dict(executed_sources=reg['sources'],generated=reg['generated'],binaries=ready['binaries'],parent_binaries=ready['parent_binaries'],libraries=ready['libraries'],replay_identity=replay_identity,STATIC=load(w/'STATIC.json'),
        registration_sha256=sha(w/'REGISTERED.json'),ready_sha256=sha(w/'READY.json'),analysis_freeze=load(w/'ANALYSIS_FREEZE.json'),
        continuation=auth,second_continuation={k:v for k,v in second.items() if k!='gpu'},qualification_admission=admission,primary_admission=primary_admission,
        postprocessing_sources={n:sha(HERE/n) for n in ('curate.py','timeline.py','scalars.py','verify.py','postcheck.py','test_evidence.py','report.py')},
        placement='One idle same-model SM120 GPU with matched NUMA;physical identifiers private;no settings changes.'))
    save(a.out/'evidence/EXECUTION.json',dict(complete=True,total_GPU_starts=341,max_GPU_starts=341,admitted_GPU_targets=340,passed_targets_rerun=0,invalid_attempts_replaced=1,original_validator_false_alarm_retained=True,original_isolation_failure_retained=True,automatic_retries=0,
        stage_attempt_counts={s:len(js) for s,js in schedule},admitted_stage_counts={s:len(js)-int(s=='primary') for s,js in schedule},
        stage_result_sha256={s:sha(w/s/'RESULTS.json') for s,_ in schedule},start_ledger_sha256=sha(w/'STARTS.jsonl')))
    assert (w/'campaign.lock').stat().st_size==0
    raw={str(p.relative_to(w)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(w.rglob('*')) if p.is_file() and p.name!='campaign.lock'}
    save(a.out/'evidence/RAW_MANIFEST.json',dict(scope='Complete private raw work tree except the empty advisory campaign.lock;hashes only,no coordinates or captures.',files=raw,excluded=dict(path='campaign.lock',bytes=0,reason='Runtime advisory lock,no semantic evidence')))
    admin=[p for folder in (root/'code_final',root/'OFFLINE_REVIEW_R1') for p in folder.rglob('*') if p.is_file()]
    admin+=[root/'audit_code/artifacts/ownership_safe_gpu_update_20261015/quality.py']
    active_stdout=Path('/proc/self/fd/1').resolve()
    admin+=[p for p in root.iterdir() if p.is_file() and p.resolve()!=active_stdout and (p.suffix in ('.json','.log','.py') or p.name in ('SOURCE_R1.tgz','SOURCE_FINAL.tgz'))]
    assert all(not p.is_symlink() for p in admin)
    save(a.out/'evidence/ADMIN_MANIFEST.json',dict(scope='Private source snapshots,controllers,offline original-target reviews and append-only administrative records;hashes only.',
        files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(set(admin))},
        omitted_live_postprocessor_stdout=active_stdout.name if active_stdout.is_relative_to(root) else None,
        separately_preserved_checkpoint=dict(file='STOPPED_93_RAW.tgz',bytes=(root/'STOPPED_93_RAW.tgz').stat().st_size,sha256=sha(root/'STOPPED_93_RAW.tgz'))))
    print('CURATED340 admitted targets/341 attempts;all raw revalidated;0 GPU starts',flush=True)

if __name__=='__main__':main()
