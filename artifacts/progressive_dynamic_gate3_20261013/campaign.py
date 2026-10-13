"""Append-only, first-failure-stop fresh-process campaign; conditional B admission."""
import argparse,fcntl,json,os,subprocess,sys,time,traceback
from pathlib import Path
from prepare import HERE,ART,read,save,sha,sources,library_hashes
from quality import check
from analyze import summary,classify,gate_b
STAGES=('qualification','A','B','B_probes')
def jobs(stage):
    if stage=='qualification':
        return [dict(label=m+'_fixtures',mode=m,fixture=True) for m in ('D0','D1')]+[dict(label=m+'_'+tool,mode=m,fixture=True,tool=tool) for m in ('D0','D1') for tool in ('memcheck','racecheck','synccheck')]+[dict(label=m+'_A_dry',mode=m,workload='A',dry=True) for m in ('D0','D1')]
    if stage=='B_probes':return [dict(label='D1_B_dry',mode='D1',workload='B',dry=True)]
    return [dict(label=f'r{r}_{m}',mode=m,workload=stage,round=r,order='forward' if r%2 else 'reverse') for r in range(1,7 if stage=='A' else 4) for m in (('D0','D1') if r%2 else ('D1','D0'))]
def prepared(w):
    reg=read(w/'REGISTERED.json');ready=read(w/'READY.json');assert ready['passed'] and ready['registration_sha256']==sha(w/'REGISTERED.json') and reg['contract_sha256']==sha(HERE/'CONTRACT.json')
    assert sources()==reg['sources']==ready['sources'] and reg['dependency_preflight_sha256']==sha(w/'DEPENDENCY_PREFLIGHT.json') and read(w/'DEPENDENCY_PREFLIGHT.json')['passed']
    assert sha(reg['data'])==reg['data_sha256']
    for m,h in ready['binaries'].items():
        assert sha(w/'build'/m)==h and library_hashes(w/'build'/m,{**os.environ,**reg['environment']})[0]==ready['libraries']
    for p,h in ready['inputs'].items():assert sha(w/p)==h
    for p,h in reg['generated_sources'].items():assert sha(w/'build'/p)==h
    for p,h in reg['static_libraries'].items():assert sha(p)==h
    for p,h in reg['stage_reference_hashes'].items():assert sha(p)==h
    assert sha(w/'pool32.txt')==ready['probe_pool_sha256'] and sha(w/'build/oracle.so')==ready['oracle_sha256']
    if reg.get('recovery'):
        r=reg['recovery'];prior=Path(r['prior_work']);assert r['human_approved'] and r['prior_starts']==1 and r['max_total_starts']==30 and sha(prior/'REGISTERED.json')==r['prior_registration_sha256'] and sha(prior/'STARTS.jsonl')==r['prior_ledger_sha256'] and sha(prior/'qualification/RESULTS.json')==r['prior_failure_sha256']
    static=read(w/'build/STATIC.json');assert static['passed'] and static['no_GPU_starts'] and static['registration_sha256']==sha(w/'REGISTERED.json') and static['static_tool_sha256']==sha(HERE/'static.py')
    expected={**ready['binaries'],'old_D0':reg['old_strengthened_sha256'],'Gate2':reg['Gate2_BINARY_sha256']}
    for m,h in expected.items():
        assert static['records'][m]['container_sha256']==h
        for suffix,key in (('.sass.txt','sass_dump_sha256'),('.resources.txt','resources_sha256')):assert sha(w/'build'/(m+suffix))==static['records'][m][key]
    return reg
def command(job,w,reg,prefix):
    fx=job.get('fixture',False);trace=w/'fixtures/trace' if fx else w/'inputs'/job['workload'];data=w/'fixtures/data.f32bin' if fx else Path(reg['data'])
    cmd=[str(w/'build'/job['mode']),str(data),str(trace),str(1. if fx else reg['radius']),str(prefix),'/dev/null' if fx else str(w/'pool32.txt'),str(int(job.get('dry',False)))]
    if job.get('tool'):cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',job['tool'],'--error-exitcode','97',*cmd]
    return cmd
def guard_identity(stage,job,w,reg):
    root=w/stage;g=root/'guards'/job['label'];r=read(g/'receipt.json');cmd=command(job,w,reg,root/'outputs'/job['label']);want=['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
    assert read(root/(job['label']+'.command.json'))==dict(command=cmd) and read(g/'command.json')==want and r['command']==want and r['gpu']==reg['gpu'] and r['binary_sha256']==sha(cmd[0])
    assert r['runtime_valid'] and r['exit_code']==0 and r['stop_reason'] is None and r['observer']=='two-sided-starttime-v1'
    for label in ('before','after'):
        snapshot=read(g/(label+'.json'));assert not snapshot['apps'] and snapshot['device'].split(',')[1].strip()==reg['gpu']
def previous(w,stage,reg):
    root=w/stage;registration=read(root/'REGISTERED.json');result=read(root/'RESULTS.json');expected=jobs(stage)
    assert result['complete'] and result['registration_sha256']==sha(root/'REGISTERED.json') and registration['jobs']==expected and registration['sources']==sources() and registration['ready_sha256']==sha(w/'READY.json') and registration['static_sha256']==sha(w/'build/STATIC.json')
    assert len(result['rows'])==len(expected)
    for row,job in zip(result['rows'],expected):
        assert {k:row[k] for k in job}==job and row['status']=='passed';guard_identity(stage,job,w,reg)
        checked=read(root/(job['label']+'.checked.json'));assert checked['passed'] and checked['job']==job and sha(root/(job['label']+'.checked.json'))==row['checked_sha256']
        for p,h in row['guard_hashes'].items():assert sha(root/'guards'/job['label']/p)==h
        for p,h in checked['output_hashes'].items():assert sha(root/'outputs'/p)==h
    return result
def stats(w,stage):
    pairs=[];metrics=['trace_ms','events_ms','release_ms','ack_sum_ms','range_ms','knn_ms','insert_ms','delete_ms']
    for r in range(1,7 if stage=='A' else 4):
        p={}
        for m in ('D0','D1'):
            c=read(w/stage/(f'r{r}_{m}.checked.json'));assert c['passed'];v=c['measured'];meta=v['meta'];ops=v['op_totals_ms']
            p[m]={k:meta[k] for k in metrics[:3]};p[m].update(ack_sum_ms=sum(ops.values()),range_ms=ops['2'],knn_ms=ops['3'],insert_ms=ops['0'],delete_ms=ops['1'])
        pairs.append(p)
    summaries={metric:summary([{m:p[m][metric] for m in ('D0','D1')} for p in pairs]) for metric in metrics}
    t=summaries['trace_ms'];decision=classify(t['ratio'],summaries['range_ms']['ratio'],summaries['insert_ms']['ratio'],summaries['delete_ms']['ratio'],t['paired_CI95'][1],t['wins']) if stage=='A' else ('PASS_UPDATE_HEAVY' if gate_b(summaries['range_ms']['ratio'],summaries['insert_ms']['ratio'],summaries['delete_ms']['ratio']) else 'FAIL_UPDATE_HEAVY')
    return dict(stage=stage,decision=decision,paired_processes=pairs,metrics=summaries,denominator='events_ms+release_ms;offline export/validation explicitly excluded')
def run(a):
    w=a.work.resolve();reg=prepared(w);assert a.gpu==reg['gpu'] and a.numa==reg['numa']
    for old in STAGES[:STAGES.index(a.stage)]:previous(w,old,reg)
    if a.stage in ('B','B_probes'):assert stats(w,'A')['decision']=='GO_DYNAMIC_PROGRESSIVE','B is conditional;gray/failure stops'
    if a.stage=='B_probes':assert stats(w,'B')['decision']=='PASS_UPDATE_HEAVY','B failure stops full admission'
    root=w/a.stage;root.mkdir();(root/'outputs').mkdir();(root/'guards').mkdir()
    registration=dict(before_GPU=True,jobs=jobs(a.stage),sources=sources(),ready_sha256=sha(w/'READY.json'),static_sha256=sha(w/'build/STATIC.json'),gpu=a.gpu,numa=a.numa,registered_unix=time.time());save(root/'REGISTERED.json',registration);rows=[]
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in registration['jobs']:
            row={**job,'status':'not_executed'};rows.append(row)
            try:
                assert sources()==reg['sources'];ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0;prior_starts=reg.get('recovery',{}).get('prior_starts',0);assert count+prior_starts<reg.get('recovery',{}).get('max_total_starts',29)
                prefix=root/'outputs'/job['label'];cmd=command(job,w,reg,prefix);save(root/(job['label']+'.command.json'),dict(command=cmd))
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,global_start=count+1+prior_starts,stage=a.stage,label=job['label'],command_sha256=sha(root/(job['label']+'.command.json')),started_unix=time.time()))+'\n')
                guard=[sys.executable,str(ART/'external_closure/static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(root/'guards'/job['label']),'--',*cmd]
                with (root/(job['label']+'.outer.log')).open('x') as log:subprocess.run(guard,env={**os.environ,**reg['environment'],'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=log,check=True)
                guard_identity(a.stage,job,w,reg);checked=check(prefix,job,w,reg)
                if job.get('tool'):
                    logs=''.join((root/'guards'/job['label']/n).read_text() for n in ('stdout.log','stderr.log'));assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs;checked['sanitizer_summary_zero']=True
                save(root/(job['label']+'.checked.json'),checked);row.update(status='passed',guard_hashes={p.name:sha(p) for p in (root/'guards'/job['label']).iterdir() if p.is_file()},checked_sha256=sha(root/(job['label']+'.checked.json')))
                save(root/'PROGRESS.json',dict(rows=rows));print('PASSED',a.stage,job['label'],'events+release_ms',checked['measured']['meta']['trace_ms'],flush=True)
            except Exception:
                row.update(status='failed',error=traceback.format_exc());rows.extend({**j,'status':'not_executed'} for j in registration['jobs'][len(rows):]);save(root/'RESULTS.json',dict(complete=False,rows=rows,registration_sha256=sha(root/'REGISTERED.json'),stop='first failure;no automatic retry'));raise
    save(root/'RESULTS.json',dict(complete=True,rows=rows,registration_sha256=sha(root/'REGISTERED.json')))
    if a.stage in ('A','B'):
        result=stats(w,a.stage);save(root/'STATS.json',result);print('DECISION',result['decision'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);run(p.parse_args())
