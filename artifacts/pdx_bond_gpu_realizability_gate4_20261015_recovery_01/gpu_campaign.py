"""Bounded single-candidate GPU campaign; preserve every launch and failed row."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
import numpy as np
from gpu_prepare import HERE,load,save,sha


def legacy(repo, name):
    root=repo/'artifacts/progressive_gpu_gate2_20261013'
    sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('legacy_'+name,root/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def schedule(stage):
    if stage=='qualification':
        jobs=[{'label':'fixtures','mode':'candidate','kind':'fixtures'},
              {'label':'bounded','mode':'candidate','N':4096,'diag':2},
              {'label':'target_keeper','mode':'keeper','N':1000000,'diag':2},
              {'label':'target_candidate','mode':'candidate','N':1000000,'diag':2}]
        jobs += [{'label':kind+'_'+tool,'mode':'candidate','kind':'fixtures','tool':tool} if kind=='fixtures'
                 else {'label':kind+'_'+tool,'mode':'candidate','N':4096,'diag':2,'tool':tool}
                 for kind in ('fixtures','bounded') for tool in ('memcheck','racecheck','synccheck')]
        return jobs
    if stage=='primary':
        return [{'label':f'r{r}_{m}','mode':m,'N':1000000,'round':r,'order':'forward' if r%2 else 'reverse'}
                for r in range(1,7) for m in (('keeper','candidate') if r%2 else ('candidate','keeper'))]
    if stage=='ncu':return [{'label':m,'mode':m,'N':1000000,'diag':1,'tool':'ncu'} for m in ('keeper','candidate')]
    assert stage=='breakdown'
    return [{'label':m,'mode':m,'N':1000000,'diag':3} for m in ('keeper','candidate')]


def quality(prefix, job, w, reg, base):
    checked=base.p1_quality(prefix,job,reg)
    table=base.table(str(prefix)+'.stages.csv');assert len(table)==160
    cpu=load(Path(reg['cpu'])/'RESULTS.json')
    old=load(w/'GPU_PARENT.json');expected={}
    if job['mode']=='keeper':
        manifest=load(Path(reg['repo'])/'artifacts/exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json')['files']
    for i,q in enumerate(reg['q32']):
        if job['mode']=='candidate':
            p=Path(reg['cpu'])/'raw'/f'q{i:02}_safe.bin';h=cpu['records'][i]['raw'][p.name]['sha256']
        else:
            p=Path(old['gate1_directory'])/'raw'/f'{q}.required.u16';h=manifest[p.name]['sha256']
        assert sha(p)==h
        dims=np.memmap(p,'<u2',mode='r')[:job['N']]
        full=np.memmap(Path(reg['reference'])/f'{q}.f64','<f8',mode='r')[:job['N']]
        expected[q]=([np.flatnonzero(dims>s).astype('<i4') if s<960 else np.flatnonzero(full<=reg['radius']**2).astype('<i4')
                      for s in (128,256,512,960)],full)
    counts=[];replay=[];authority_checked=0
    for i in range(40):
        q=reg['q32'][i if i<8 else i-8];active=job['N'];cs=[];rs=[]
        wants,full=expected[q]
        for s in range(4):
            row=table[i*4+s];want=wants[s]
            assert int(row['invocation'])==i and int(row['stage'])==s+1
            assert int(row['input'])==active and int(row['output'])==len(want)
            if job.get('diag')==2:
                base.checkpoint_ids(str(prefix)+f'.checkpoint.{i}.{s+1}.i32',want)
            cs.append(len(want));rs.append(int(row['replay_coordinates']));active=len(want)
        if job.get('diag')==2:
            p=Path(str(prefix)+f'.authority.{i}.f64');assert p.stat().st_size==len(wants[3])*8
            got=np.fromfile(p,'<f8');assert np.array_equal(got.view('<u8'),np.asarray(full[wants[3]]).view('<u8'))
            authority_checked+=len(got)
        counts.append(cs);replay.append(rs)
    checked.update(mode=job['mode'],checkpoint_counts=counts,
        complete_checkpoint_IDs_checked=job.get('diag')==2,internal_ordered_FP64_scores_checked=authority_checked,
        internal_FP64_bit_mismatches=0 if job.get('diag')==2 else None,
        replay_coordinates=replay if job.get('diag')==2 else None)
    checked['output_hashes']={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()}
    return checked


def static(w, reg):
    old=legacy(Path(reg['repo']),'static_evidence');records={};selected={}
    for name in ('keeper','candidate'):
        binary=w/'build'/name;sass=w/'build'/f'{name}.sass.txt';resource=w/'build'/f'{name}.resources.txt'
        with sass.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-sass',str(binary)],stdout=f,check=True)
        with resource.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-resource-usage',str(binary)],stdout=f,check=True)
        functions={k:v for k,v in old.functions(sass.read_text()).items() if 'progressive_stage' in k or 'progressive_fields' in k}
        assert len(functions)==5
        selected[name]={k:{'normalized_sass_sha256':__import__('hashlib').sha256(v.encode()).hexdigest(),
                          'opcode_counts':dict(old.opcodes(v))} for k,v in functions.items()}
        for k,v in selected[name].items():
            assert not any(op in v['opcode_counts'] for op in ('HMMA','QMMA','IMMA','DMMA'))
            if 'progressive_stage' in k:assert all(v['opcode_counts'].get(op,0)>0 for op in ('DADD','DMUL','FFMA'))
        resources={}
        for m in re.finditer(r' Function (\S+):\n\s*([^\n]+)',resource.read_text()):
            if 'progressive_stage' in m[1] or 'progressive_fields' in m[1]:resources[m[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',m[2])}
        assert len(resources)==5
        records[name]={'binary_sha256':sha(binary),'sass_dump_sha256':sha(sass),'resource_sha256':sha(resource),'resources':resources}
    original=Path(reg['parent'])/'build/candidate'
    dump=subprocess.check_output(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-sass',str(original)],text=True)
    functions={k:v for k,v in old.functions(dump).items() if 'progressive_stage' in k or 'progressive_fields' in k}
    assert {k:__import__('hashlib').sha256(v.encode()).hexdigest() for k,v in functions.items()}=={
        k:v['normalized_sass_sha256'] for k,v in selected['keeper'].items()},'keeper device code drift'
    save(w/'STATIC.json',{'passed':True,'no_GPU_starts':True,'keeper_device_functions_equal_parent':True,'records':records,'selected_functions':selected})


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    p.add_argument('--stage',choices=('static','qualification','primary','ncu','breakdown'),required=True)
    a=p.parse_args();w=a.work.resolve();reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');c=load(HERE/'GPU_CONTRACT.json')
    assert sha(w/'REGISTERED.json')==ready['registration_sha256']
    assert all(sha(Path(n))==h for n,h in reg['input_sources'].items())
    assert all(sha(Path(n))==h for n,h in reg['generated_sources'].items())
    assert all(sha(w/'build'/n)==h for n,h in ready['binaries'].items())
    assert all(sha(Path(reg['repo'])/n)==h for n,h in c['parents'].items())
    if a.stage=='static':static(w,reg);return
    assert c['decision_priority_approved'] and load(w/'STATIC.json')['passed']
    stages=('qualification','primary','ncu','breakdown')
    for previous in stages[:stages.index(a.stage)]:assert load(w/previous/'RESULTS.json')['complete']
    base=legacy(Path(reg['repo']),'campaign')
    stage=w/a.stage;stage.mkdir()
    for name in ('outputs','guards','reports'):(stage/name).mkdir()
    jobs=schedule(a.stage);save(stage/'REGISTERED.json',{'before_GPU':True,'jobs':jobs,'contract_sha256':sha(HERE/'GPU_CONTRACT.json')})
    rows=[];env={**os.environ,**reg['environment'],'PYTHONDONTWRITEBYTECODE':'1'}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in jobs:
            row={**job,'status':'not_executed'};rows.append(row)
            try:
                assert all(sha(Path(n))==h for n,h in reg['input_sources'].items())
                assert sha(reg['data'])==c['data_sha256']
                assert sha(Path(reg['cpu'])/'raw/global_means.f32')==c['global_means_sha256']
                assert all(sha(Path(reg['reference'])/n)==h for n,h in reg['reference_hashes'].items())
                prefix=stage/'outputs'/job['label'];report=stage/'reports'/job['label'];binary=w/'build'/job['mode']
                assert sha(binary)==ready['binaries'][job['mode']]
                if job.get('kind')=='fixtures':cmd=[str(binary),'--fixtures']
                else:cmd=[str(binary),reg['data'],str(w/'pool32.txt'),str(job['N']),'1',str(reg['radius']),str(prefix),str(job.get('diag',0))]
                if job.get('tool') in ('memcheck','racecheck','synccheck'):
                    cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',job['tool'],'--error-exitcode','97',*cmd]
                if job.get('tool')=='ncu':
                    cmd=['sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],'LD_LIBRARY_PATH='+env['LD_LIBRARY_PATH'],
                        '/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled',
                        '--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(c['NCU_metrics']),'-o',str(report),*cmd]
                save(stage/(job['label']+'.command.json'),{'command':cmd})
                ledger=w/'STARTS.jsonl';starts=len(ledger.read_text().splitlines()) if ledger.exists() else 0
                assert starts<c['max_GPU_starts']
                with ledger.open('a') as f:f.write(json.dumps({'start':starts+1,'stage':a.stage,'label':job['label'],'command_sha256':sha(stage/(job['label']+'.command.json'))})+'\n')
                guard=[sys.executable,str(Path(reg['repo'])/'artifacts/external_closure/static_guard.py'),
                    '--gpu',reg['gpu'],'--numa-node',str(reg['numa']),'--output',str(stage/'guards'/job['label']),'--',*cmd]
                with (stage/(job['label']+'.outer.log')).open('x') as log:subprocess.run(guard,env=env,stdout=log,stderr=log,check=True)
                g=stage/'guards'/job['label'];receipt=load(g/'receipt.json')
                assert receipt['runtime_valid'] and receipt['observer']=='two-sided-starttime-v1' and receipt['gpu']==reg['gpu']
                assert load(g/'command.json')==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
                for n in ('before','after'):assert not load(g/(n+'.json'))['apps']
                if job.get('kind')=='fixtures':
                    lines=(g/'stdout.log').read_text().splitlines();checked=next(json.loads(s) for s in reversed(lines) if s.startswith('{'))
                    assert checked['passed'] and checked['iterations']==100 and checked['stream_slots']==2 and all(checked['stage_rejects'])
                else:checked=quality(prefix,job,w,reg,base)
                if job.get('tool') in ('memcheck','racecheck','synccheck'):
                    logs=(g/'stdout.log').read_text()+(g/'stderr.log').read_text()
                    assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs
                    checked['sanitizer_summary_zero']=True
                if job.get('tool')=='ncu':
                    with Path(str(report)+'.base.csv').open('x') as f:
                        subprocess.run(['/usr/local/bin/ncu','--import',str(report)+'.ncu-rep','--page','raw','--csv','--print-units','base'],env=env,stdout=f,check=True)
                save(stage/(job['label']+'.checked.json'),checked)
                row.update(status='passed',checked_sha256=sha(stage/(job['label']+'.checked.json')),
                    guard_sha256=sha(g/'receipt.json'),guard_files={p.name:sha(p) for p in g.iterdir() if p.is_file()},
                    reports={p.name:sha(p) for p in (stage/'reports').glob(job['label']+'*') if p.is_file()})
                print('PASSED',a.stage,job['label'],flush=True)
            except BaseException:
                row.update(status='failed',error=traceback.format_exc())
                save(stage/'RESULTS.json',{'complete':False,'rows':rows,'stop':'first failure;no automatic retry'})
                raise
        save(stage/'RESULTS.json',{'complete':True,'rows':rows})


if __name__=='__main__':main()
