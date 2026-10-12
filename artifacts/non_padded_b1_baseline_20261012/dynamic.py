"""One conditional E_ADAPT integration pair; not a sustained performance campaign."""
import argparse,csv,difflib,fcntl,json,os,subprocess,sys,time,traceback
from pathlib import Path
from prepare import HERE,ART,read,save,sha,sources
from campaign import prepared,previous_stage

DEPENDENCIES=('external_closure/pe_e.cu','external_closure/pe_common.hpp',
 'external_closure/pe_check.py','external_closure/pe_trace.py','external_closure/qualify.py',
 'rebuild_tree_baselines/cpu.py','unified_target_workflow/validate.py')
def hashes():
    return {**sources(),**{str((ART/p).relative_to(ART.parent)):sha(ART/p) for p in DEPENDENCIES},
            str((HERE/'dynamic.py').relative_to(ART.parent)):sha(HERE/'dynamic.py')}
def payloads(prefix):
    return {str(p):sha(p) for p in Path(prefix).parent.glob(Path(prefix).name+'.*') if p.is_file()}
def libraries(binary,env):
    text=subprocess.check_output(['ldd',str(binary)],env=env,text=True);assert 'not found' not in text
    result={}
    for line in text.splitlines():
        v=line.split()
        if '=>' in v and len(v)>2 and v[2].startswith('/'):result[v[0]]={'sha256':sha(v[2])}
    return result
def prepare(a):
    w=a.work.resolve();reg=prepared(w)
    for stage in ('qualification','primary','ncu'):previous_stage(w,stage)
    verdict=read(a.analysis/'BASELINE_TIMING.json')
    assert verdict['decision']=='BASELINE_FIXED_MEMORY_LIMIT' and verdict['static_baseline_direction_pass']
    assert len((w/'STARTS.jsonl').read_text().splitlines())==29
    old=read(a.legacy_build/'REGISTERED.json');b=read(a.legacy_build/'BUILD.json');binary=a.legacy_build/'scan'
    assert b['registration_sha256']==sha(a.legacy_build/'REGISTERED.json')
    assert b['binary_sha256']==sha(binary)=='3625babbafc9bd428ebd61e339c9651f663c7e651fdeedc8d965ba40979c6594'
    for name in ('pe_e.cu','pe_common.hpp'):assert sha(ART/'external_closure'/name)==old['source'][name]
    for name,h in old['dependencies'].items():
        matches=[v for v in old['command'] if v.endswith('/'+name)];assert len(matches)==1 and sha(matches[0])==h
    binding=read(str(a.trace)+'.binding.json')
    assert binding['N']==1000000 and binding['D']==960 and binding['data_sha256']==reg['data_sha256']
    assert binding['events_sha256']==sha(a.events)
    for suffix,key in (('','main'),('.warmup','.warmup')):
        for tail,h in binding['files'][key].items():assert sha(str(a.trace)+suffix+tail)==h
    quality=read(str(a.reference)+'.quality.json')
    assert quality['measured']['passed'] and quality['warmup']['passed']
    for suffix,key in (('','measured'),('.warmup','warmup')):
        for tail,h in quality[key]['payload_hashes'].items():assert sha(str(a.reference)+suffix+tail)==h
    counts={};max_live=1000000;inserts=0
    for suffix in ('','.warmup'):
        rows=[tuple(map(int,s.split())) for s in Path(str(a.trace)+suffix+'.logical').read_text().splitlines()[1:]]
        n=1000000;c={str(f):sum(flag==f for flag,_ in rows) for f in range(4)}
        for f,_ in rows:n+=(f==0)-(f==1);max_live=max(max_live,n);assert n>0
        counts[suffix or 'measured']=c;inserts=max(inserts,c['0'])
    assert sum(counts['measured'].values())==336 and counts['.warmup']['2']+counts['.warmup']['3']==8
    p=w/'dynamic';p.mkdir(exist_ok=False);(p/'build').mkdir()
    # Only the host contract ceiling changes; the qualified device kernel is byte-identical.
    original=(HERE/'b1_distance.cuh').read_text();bound='x->dl_tensor.shape[0]>1000000'
    assert original.count(bound)==1
    header=original.replace(bound,'x->dl_tensor.shape[0]>'+str(1000000+inserts))
    (p/'build/dynamic_b1.cuh').write_text(header)
    base=(ART/'external_closure/range_service.cu').read_text();call='cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));';assert base.count(call)==1
    adapter='#include "'+str(p/'build/dynamic_b1.cuh')+'"\n'+base.replace(call,call.replace('cuvsPairwiseDistance','b1PairwiseDistance'))
    (p/'build/candidate_range.cuh').write_text(adapter)
    source=(ART/'external_closure/pe_e.cu').read_text();assert source.count('"range_service.cu"')==source.count('"pe_common.hpp"')==1
    generated=source.replace('"range_service.cu"','"'+str(p/'build/candidate_range.cuh')+'"').replace('"pe_common.hpp"','"'+str(ART/'external_closure/pe_common.hpp')+'"')
    src=p/'build/candidate.cu';src.write_text(generated)
    command=[str(src) if v.endswith('/pe_e.cu') else str(p/'build/candidate') if v==str(binary) else v for v in old['command']]
    assert str(src) in command and str(p/'build/candidate') in command
    env={**reg['environment']};oldlibs=libraries(binary,{**os.environ,**env})
    for lib,v in reg['libraries'].items():assert oldlibs[lib]==v
    registration=dict(before_GPU=True,static_decision_sha256=sha(a.analysis/'BASELINE_TIMING.json'),
        source_hashes=hashes(),work=str(w),environment=env,gpu=reg['gpu'],numa=reg['numa'],
        data=reg['data'],data_sha256=reg['data_sha256'],trace=str(a.trace),events=str(a.events),
        warm_events=str(a.events.parent/'warmup.events'),reference=str(a.reference),
        input_hashes={**payloads(a.trace),**payloads(a.reference),str(a.events):sha(a.events),str(a.events.parent/'warmup.events'):sha(a.events.parent/'warmup.events')},
        native_binary=str(binary),native_sha256=sha(binary),libraries=oldlibs,
        legacy_registration_sha256=sha(a.legacy_build/'REGISTERED.json'),command=command,
        generated_sources={str(t):sha(t) for t in (src,p/'build/candidate_range.cuh',p/'build/dynamic_b1.cuh')},
        radius=reg['radius'],capacity=1000000+inserts,max_live=max_live,event_counts=counts,
        jobs=['old','strengthened'],max_additional_starts=2,registered_unix=time.time(),
        scope='one old/new process pair; inherited trace_ms includes release; query/update ACKs unchanged; no CI or sustained claim',
        unchanged='kNN, norm maintenance, insertion, swap deletion, bookkeeping, outputs, timers, setup, release; device kernel unchanged',
        stop='first failure; retain failed/unexecuted jobs; no retry')
    save(p/'REGISTERED.json',registration)
    diff=''.join(difflib.unified_diff(original.splitlines(True),header.splitlines(True),fromfile='b1_distance.cuh',tofile='dynamic_b1.cuh'))
    diff+=''.join(difflib.unified_diff(base.splitlines(True),adapter.splitlines(True),fromfile='range_service.cu',tofile='candidate_range.cuh'))
    diff+=''.join(difflib.unified_diff(source.splitlines(True),generated.splitlines(True),fromfile='pe_e.cu',tofile='candidate.cu'))
    (p/'build/ADAPTER_DIFF.patch').write_text(diff)
    with (p/'build/compile.log').open('x') as log:subprocess.run(command,env={**os.environ,**env},stdout=log,stderr=log,check=True)
    assert libraries(p/'build/candidate',{**os.environ,**env})==oldlibs
    save(p/'build/BUILD.json',dict(binary_sha256=sha(p/'build/candidate'),libraries=oldlibs,registration_sha256=sha(p/'REGISTERED.json')))
    save(p/'READY.json',dict(passed=True,source_hashes=hashes(),registration_sha256=sha(p/'REGISTERED.json'),build_sha256=sha(p/'build/BUILD.json')))
    print(json.dumps(dict(prepared=True,counts=counts,capacity=registration['capacity'],max_live=max_live,no_GPU_launch=True)),flush=True)
def run(a):
    w=a.work.resolve();p=w/'dynamic';reg=read(p/'REGISTERED.json');ready=read(p/'READY.json');build=read(p/'build/BUILD.json')
    assert ready['passed'] and reg['source_hashes']==ready['source_hashes']==hashes()
    assert ready['registration_sha256']==build['registration_sha256']==sha(p/'REGISTERED.json') and ready['build_sha256']==sha(p/'build/BUILD.json')
    assert sha(p/'build/candidate')==build['binary_sha256'] and sha(reg['native_binary'])==reg['native_sha256']
    assert sha(reg['data'])==reg['data_sha256']
    for path,h in {**reg['input_hashes'],**reg['generated_sources']}.items():assert sha(path)==h
    prepared(w)
    for stage in ('qualification','primary','ncu'):previous_stage(w,stage)
    assert a.gpu==reg['gpu'] and a.numa==reg['numa']
    for name in ('outputs','guards'):(p/name).mkdir()
    sys.path.insert(0,str(ART/'external_closure'));from pe_check import check
    rows=[]
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for label in reg['jobs']:
            row=dict(label=label,status='not_executed');rows.append(row)
            try:
                assert hashes()==reg['source_hashes']
                ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines());assert count==29+len(rows)-1 and count<31
                prefix=p/'outputs'/label;cmd=[reg['native_binary'] if label=='old' else str(p/'build/candidate'),reg['data'],reg['trace'],str(reg['radius']),str(prefix)]
                save(p/(label+'.command.json'),dict(command=cmd))
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,stage='dynamic',label=label,command_sha256=sha(p/(label+'.command.json')),registered_unix=time.time()))+'\n')
                guard=[sys.executable,str(ART/'external_closure/static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(p/'guards'/label),'--',*cmd]
                with (p/(label+'.outer.log')).open('x') as log:subprocess.run(guard,env={**os.environ,**reg['environment']},stdout=log,stderr=log,check=True)
                receipt=p/'guards'/label/'receipt.json';assert read(receipt)['runtime_valid']
                measured=check(reg['data'],reg['events'],reg['trace'],prefix,'E',reg['reference'])
                warm=check(reg['data'],reg['warm_events'],reg['trace']+'.warmup',str(prefix)+'.warmup','E',reg['reference']+'.warmup')
                meta=read(str(prefix)+'.pe.json')
                with Path(str(prefix)+'.ops.csv').open() as f:ops=list(csv.DictReader(f))
                checked=dict(passed=True,measured=measured,warmup=warm,meta=meta,ops=ops,output_hashes=payloads(prefix))
                save(p/(label+'.checked.json'),checked);row.update(status='passed',checked_sha256=sha(p/(label+'.checked.json')),guard_sha256=sha(receipt))
                print(json.dumps(dict(label=label,status='passed',trace_ms=meta['trace_ms'],queries=measured['queries'])),flush=True)
            except Exception as e:
                row.update(status='failed',error=str(e));save(p/'RESULTS.json',dict(complete=False,rows=rows,registration_sha256=sha(p/'REGISTERED.json')));traceback.print_exc();raise
            save(p/'RESULTS.json',dict(complete=len(rows)==2,rows=rows,registration_sha256=sha(p/'REGISTERED.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','run'));p.add_argument('--work',type=Path,required=True)
    for n in ('legacy-build','trace','events','reference','analysis'):p.add_argument('--'+n,type=Path)
    p.add_argument('--gpu');p.add_argument('--numa',type=int);a=p.parse_args()
    if a.stage=='prepare':prepare(a)
    else:run(a)
