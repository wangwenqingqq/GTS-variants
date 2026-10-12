"""Explicit reference-ownership correction; retain the stopped run, never rerun it."""
import argparse,csv,fcntl,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from dynamic import hashes,payloads
from prepare import ART,HERE,read,save,sha

def normalize_reference(trace,reference,output):
    """Convert already-logical occurrence IDs to the inherited checker's live ranks."""
    header,*lines=Path(str(trace)+'.logical').read_text().splitlines();events,n,d=map(int,header.split())
    ops=[tuple(map(int,s.split())) for s in lines];assert len(ops)==events
    size=n+sum(f==0 for f,_ in ops);alive=np.zeros(size,bool);alive[:n]=True
    raw=np.fromfile(str(reference)+'.ids.i32',dtype='<i4');converted=np.empty_like(raw)
    with Path(str(reference)+'.queries.csv').open() as f:rows=list(csv.DictReader(f))
    qi=at=0
    for step,(flag,oid) in enumerate(ops):
        if flag==0:assert 0<=oid<size and not alive[oid];alive[oid]=True
        elif flag==1:assert 0<=oid<size and alive[oid];alive[oid]=False
        else:
            row=rows[qi];qi+=1;assert int(row['step'])==step and int(row['offset'])==at
            z=int(row['count']);actual=raw[at:at+z];live=np.flatnonzero(alive)
            assert len(actual)==z and np.all((actual>=0)&(actual<size)) and np.all(alive[actual])
            ranks=np.searchsorted(live,actual);assert np.array_equal(live[ranks],actual)
            converted[at:at+z]=ranks;at+=z
    assert qi==len(rows) and at==len(raw)
    output=Path(output);assert not list(output.parent.glob(output.name+'.*'))
    converted.tofile(str(output)+'.ids.i32')
    for suffix in ('.dist.f32','.queries.csv'):shutil.copyfile(str(reference)+suffix,str(output)+suffix)
    return dict(queries=qi,items=len(raw),logical_to_live_rank_only=True,all_round_trips_equal=True,
                hashes=payloads(output),original_hashes={s:sha(str(reference)+s) for s in ('.ids.i32','.dist.f32','.queries.csv')})
def audit(w):
    p=w/'dynamic';reg=read(p/'REGISTERED.json');assert read(p/'RESULTS.json')['complete'] is False
    assert read(p/'RESULTS.json')['rows'][0]['status']=='failed' and len((w/'STARTS.jsonl').read_text().splitlines())==30
    assert hashes()==reg['source_hashes'];q=p/'recovery';q.mkdir(exist_ok=False);(q/'reference').mkdir()
    refs={}
    for suffix in ('','.warmup'):
        refs[suffix or 'measured']=normalize_reference(reg['trace']+suffix,reg['reference']+suffix,q/'reference'/('rank'+suffix))
    sys.path.insert(0,str(ART/'external_closure'));from pe_check import check
    prefix=p/'outputs/old';measured=check(reg['data'],reg['events'],reg['trace'],prefix,'E',q/'reference/rank')
    warm=check(reg['data'],reg['warm_events'],reg['trace']+'.warmup',str(prefix)+'.warmup','E',q/'reference/rank.warmup')
    assert read(p/'guards/old/receipt.json')['runtime_valid']
    checked=dict(passed=True,measured=measured,warmup=warm,meta=read(str(prefix)+'.pe.json'),
                 ops=list(csv.DictReader(open(str(prefix)+'.ops.csv'))),output_hashes=payloads(prefix))
    save(q/'old.offline_checked.json',checked)
    save(q/'AUDIT.json',dict(passed=True,no_GPU_launch=True,original_failure_preserved=True,
        issue='P_target IDs already encode stable logical occurrences (pe_p::delivered); inherited checker interprets supplied reference IDs as live ranks',
        correction='CPU-only logical-ID to live-rank normalization; exact bijection, no membership/field/timing change',
        reference_conversion=refs,old_offline_checked_sha256=sha(q/'old.offline_checked.json'),
        original_results_sha256=sha(p/'RESULTS.json'),original_register_sha256=sha(p/'REGISTERED.json'),
        stopped_old_output_hashes=payloads(prefix),source_hashes=hashes(),recovery_source_sha256=sha(HERE/'recover.py')))
    print(json.dumps(dict(offline_pass=True,queries=measured['queries'],warmup=warm['queries'],no_GPU_launch=True)),flush=True)
def resume(w):
    p=w/'dynamic';q=p/'recovery';reg=read(p/'REGISTERED.json');audit=read(q/'AUDIT.json');assert audit['passed']
    assert audit['source_hashes']==reg['source_hashes']==hashes() and audit['recovery_source_sha256']==sha(HERE/'recover.py')
    assert audit['original_results_sha256']==sha(p/'RESULTS.json') and audit['original_register_sha256']==sha(p/'REGISTERED.json')
    assert audit['old_offline_checked_sha256']==sha(q/'old.offline_checked.json')
    for path,h in {**audit['stopped_old_output_hashes'],**reg['input_hashes'],**reg['generated_sources']}.items():assert sha(path)==h
    for v in audit['reference_conversion'].values():
        for path,h in v['hashes'].items():assert sha(path)==h
    build=read(p/'build/BUILD.json');assert sha(p/'build/candidate')==build['binary_sha256']
    assert sha(reg['data'])==reg['data_sha256']
    qreg=dict(before_execution=True,human_authorized_recovery=True,only_remaining_job='strengthened',
        original_attempt_preserved=True,old_not_rerun=True,query_and_timing_unchanged=True,
        audit_sha256=sha(q/'AUDIT.json'),source_hashes=hashes(),recovery_source_sha256=sha(HERE/'recover.py'),registered_unix=time.time())
    save(q/'REGISTERED.json',qreg);(q/'outputs').mkdir();(q/'guards').mkdir();prefix=q/'outputs/strengthened'
    cmd=[str(p/'build/candidate'),reg['data'],reg['trace'],str(reg['radius']),str(prefix)]
    save(q/'strengthened.command.json',dict(command=cmd))
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);ledger=w/'STARTS.jsonl';assert len(ledger.read_text().splitlines())==30
        with ledger.open('a') as f:f.write(json.dumps(dict(start=31,stage='dynamic_recovery',label='strengthened',command_sha256=sha(q/'strengthened.command.json'),registered_unix=time.time()))+'\n')
        try:
            guard=[sys.executable,str(ART/'external_closure/static_guard.py'),'--gpu',reg['gpu'],'--numa-node',str(reg['numa']),'--output',str(q/'guards/strengthened'),'--',*cmd]
            with (q/'strengthened.outer.log').open('x') as log:subprocess.run(guard,env={**os.environ,**reg['environment']},stdout=log,stderr=log,check=True)
            receipt=q/'guards/strengthened/receipt.json';assert read(receipt)['runtime_valid']
            sys.path.insert(0,str(ART/'external_closure'));from pe_check import check
            measured=check(reg['data'],reg['events'],reg['trace'],prefix,'E',q/'reference/rank')
            warm=check(reg['data'],reg['warm_events'],reg['trace']+'.warmup',str(prefix)+'.warmup','E',q/'reference/rank.warmup')
            checked=dict(passed=True,measured=measured,warmup=warm,meta=read(str(prefix)+'.pe.json'),
                ops=list(csv.DictReader(open(str(prefix)+'.ops.csv'))),output_hashes=payloads(prefix))
            save(q/'strengthened.checked.json',checked)
            save(q/'RESULTS.json',dict(complete=True,passed=True,registration_sha256=sha(q/'REGISTERED.json'),
                 checked_sha256=sha(q/'strengthened.checked.json'),guard_sha256=sha(receipt),old_offline_checked_sha256=sha(q/'old.offline_checked.json')))
            print(json.dumps(dict(passed=True,trace_ms=checked['meta']['trace_ms'],queries=measured['queries'],total_starts=31)),flush=True)
        except Exception as e:
            save(q/'RESULTS.json',dict(complete=False,passed=False,error=str(e),registration_sha256=sha(q/'REGISTERED.json')));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('audit','resume'));p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();(audit if a.stage=='audit' else resume)(a.work.resolve())
