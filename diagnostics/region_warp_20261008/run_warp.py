#!/usr/bin/env python3
"""One frozen five-mode mapping experiment, reusing the parent runner/oracle."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE.parent / 'region_exec_20261008'))
import run_region as r
from finish_closure import compare_work

MODES = ('PAR_STRONG', 'SPLIT_SERIAL', 'FUSED_SERIAL', 'SPLIT_WARP', 'FUSED_WARP')
ORDERS = ((0,1,2,3,4),(4,3,2,1,0),(1,3,0,4,2),(2,4,0,3,1),(2,0,4,1,3),(3,1,4,0,2))
PAIRS = ((1,3),(2,4),(3,4),(0,4),(0,3),(1,2))


def locked(a, label, command, signature):
    target = a.dest / 'runs' / label
    assert not target.exists(), 'retain every previous attempt'
    registration = dict(command=command, source_sha256=r.sha(a.dest/'SOURCE.json'), controller_sha256=r.sha(__file__))
    (a.dest/'registrations').mkdir(exist_ok=True)
    r.save(a.dest/'registrations'/(label+'.json'), registration)
    subprocess.run([sys.executable, str(a.raw/'run_locked.py'), '--gpu', a.gpu,
                    '--output', str(target), '--timeout-seconds', '1200', '--', *command],
                   check=True, stdout=subprocess.DEVNULL)
    receipt = r.read(target/'receipt.json'); assert receipt['runtime_valid']
    text = (target/'stdout.log').read_text() + (target/'stderr.log').read_text()
    assert signature in text, text[-2000:]
    return dict(label=label, passed=True, receipt_sha256=r.sha(target/'receipt.json'),
                stdout_sha256=r.sha(target/'stdout.log'), stderr_sha256=r.sha(target/'stderr.log'),
                registration_sha256=r.sha(a.dest/'registrations'/(label+'.json')))


def prepare(a):
    r.prepare(a)
    source = r.read(a.dest/'SOURCE.json')
    for name, flags in (('test_warp', []), ('micro_warp', ['-DREGION_WARP_MICRO'])):
        command = ['/usr/local/cuda/bin/nvcc', '-std=c++17', '-O3', '-arch=sm_120', '-lineinfo',
                   '-I'+str(a.dest/'native_timed/source/include'), str(CODE/'test_warp.cu'), *flags,
                   '--ptxas-options=-v', '-o', str(a.dest/'native_timed'/name)]
        with (a.dest/('BUILD_'+name+'.log')).open('w') as stream:
            subprocess.run(command, check=True, stdout=stream, stderr=subprocess.STDOUT)
        source[name+'_binary_sha256'] = r.sha(a.dest/'native_timed'/name)
        source[name+'_build'] = command
    source.update(warp_test_source_sha256=r.sha(CODE/'test_warp.cu'),
                  warp_controller_sha256=r.sha(__file__), design_sha256=r.sha(CODE/'DESIGN.md'))
    r.save(a.dest/'SOURCE.json', source)
    with (a.dest/'RESOURCES.txt').open('w') as stream:
        subprocess.run(['/usr/local/cuda/bin/cuobjdump', '--dump-resource-usage',
                        str(a.dest/'native_timed/region_exec')], check=True, stdout=stream)


def qualify(a):
    assert not (a.dest/'VALIDATION.json').exists()
    source = r.read(a.dest/'SOURCE.json')
    assert source['warp_controller_sha256']==r.sha(__file__)
    checks = []
    for binary, mapping in (('test_region','SERIAL'),('test_region','WARP'),('test_warp',None)):
        key = 'structural_binary_sha256' if binary=='test_region' else 'test_warp_binary_sha256'
        assert r.sha(a.dest/'native_timed'/binary)==source[key]
        for tool in (None,'memcheck','racecheck','synccheck'):
            cmd = [str(a.dest/'native_timed'/binary)] + (['--warp'] if mapping=='WARP' else [])
            if tool:cmd = ['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','77',*cmd]
            label = '_'.join(str(x) for x in (binary,mapping,tool))
            signature = ('STRUCTURAL_PASS: 9 topologies x6 states x2 modes' if binary=='test_region' else 'WARP_BOUNDARY_PASS:')
            row = locked(a,label,cmd,signature)
            text=(a.dest/'runs'/label/'stdout.log').read_text()+(a.dest/'runs'/label/'stderr.log').read_text()
            if tool:assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in text
            if mapping:assert 'mapping='+mapping in text
            checks.append(row);r.save(a.dest/'VALIDATION_PROGRESS.json',checks)
    sys.path.insert(0,str(a.helpers));from u_life_bridge import small_cases
    mixed = []
    for case in small_cases(a):
        reference = r.run(a,'boundary_'+case.name+'_NATIVE',case,'NATIVE',audit=True)
        for mode in MODES:
            row=r.run(a,'boundary_'+case.name+'_'+mode,case,mode,audit=True)
            assert r.equal_output(reference,row);mixed.append(row)
        for mode in MODES[3:]:
            for tool in ('memcheck','racecheck','synccheck'):
                mixed.append(r.run(a,'sanitize_'+case.name+'_'+mode+'_'+tool,case,mode,tool=tool))
    full=[];case=a.dest/'native'/str(r.SEED)
    for mode in MODES:
        full.append(r.run(a,'full_work_'+mode,case,mode,observe=False,counters=True))
        r.save(a.dest/'FULL_WORK_ROWS.json',full)
    assert all(r.equal_output(full[0],row) for row in full[1:])
    paths=[a.dest/'runs'/('full_work_'+m)/'stdout.log' for m in MODES]
    work=compare_work(paths[:3],10000)
    other=compare_work([paths[0],paths[3],paths[4]],10000)
    assert work['normalized_work_stream_sha256']==other['normalized_work_stream_sha256']
    assert work['normalized_work_stream_sha256']=='0500611520cfd9e548b10a30ce6ea62b6309f905753638ae9b36c7daf10d445f'
    work.update(modes=list(MODES),separate_from_primary=True)
    r.save(a.dest/'FULL_WORK.json',work)
    r.save(a.dest/'VALIDATION.json',dict(passed=True,structural=checks,mixed=mixed,
                                      full_work_sha256=r.sha(a.dest/'FULL_WORK.json'),
                                      source_sha256=r.sha(a.dest/'SOURCE.json')))
    print('QUALIFICATION COMPLETE',flush=True)


def micro(a):
    binary=a.dest/'native_timed/micro_warp'
    assert r.sha(binary)==r.read(a.dest/'SOURCE.json')['micro_warp_binary_sha256']
    row=locked(a,'micro', [str(binary)], 'MICRO_PASS:')
    text=(a.dest/'runs/micro/stdout.log').read_text()
    values=json.loads(next(x[len('MICRO_ROWS '):] for x in text.splitlines() if x.startswith('MICRO_ROWS ')))
    assert len(values)==6
    row.update(scope='one process, six direction-balanced CUDA-event batches; 512 launches each; 8x20 bounded micro only',
               raw=values,geometric_serial_over_warp=float(np.exp(np.log([x['serial_ms']/x['warp_ms'] for x in values]).mean())))
    r.save(a.dest/'MICRO.json',row);print(json.dumps(row),flush=True)


def campaign(a):
    assert r.read(a.dest/'VALIDATION.json')['passed']
    admission=r.read(a.dest/'ADMISSION.json')
    assert admission['decision']=='continue', 'explicit opportunity/mechanism decision required'
    for name in ('SOURCE.json','VALIDATION.json','LEAF_DISTRIBUTION.json','MICRO.json'):
        assert admission['evidence_sha256'][name]==r.sha(a.dest/name), 'admission evidence changed'
    assert not (a.dest/'REGISTERED.json').exists(), 'one registered campaign only'
    source=r.read(a.dest/'SOURCE.json');assert source['warp_controller_sha256']==r.sha(__file__)
    for i,j in itertools.combinations(range(5),2):assert sum(o.index(i)<o.index(j) for o in ORDERS)==3
    case=a.dest/'native'/str(r.SEED)
    r.save(a.dest/'REGISTERED.json',dict(seed=r.SEED,modes=list(MODES),orders=[[MODES[m] for m in o] for o in ORDERS],
           primary_processes=30,observer_processes=60,source_sha256=r.sha(a.dest/'SOURCE.json'),
           admission_sha256=r.sha(a.dest/'ADMISSION.json'),
           controller_sha256=r.sha(__file__),runner_sha256=r.sha(a.raw/'run_locked.py'),
           oracle_adapter_sha256=r.sha(a.raw/'u10_native.py'),
           input_sha256={s:r.sha(case/s) for s in ('data.txt','events.txt','expected.json')},
           bootstrap_seed=202610081022,bootstrap_resamples=20000,
           scope='12000-event Host-ready/ACK trace; setup+trace separate; no history denominator',
           comparisons=[MODES[i]+'/'+MODES[j] for i,j in PAIRS],expansion='none; no automatic replacement or seed/budget sweep'))
    cost=[];qualification=[]
    for mode in MODES:
        ratios=[];same=True
        for round in range(1,7):
            pair={}
            for on in ([True,False] if round%2 else [False,True]):
                pair[on]=r.run(a,f'cost_{mode}_r{round}_{"on" if on else "off"}',case,mode,on)
                cost.append(pair[on]);r.save(a.dest/'COST_ROWS.json',cost)
            same &= r.equal_output(pair[True],pair[False])
            ratios.append(pair[True]['summary']['trace_ms']/pair[False]['summary']['trace_ms'])
        estimate=r.paired(ratios)
        q=dict(mode=mode,output_equal=same,**estimate,admitted=same and estimate['CI95'][1]<=1.03)
        qualification.append(q);r.save(a.dest/'COST_QUALIFICATION.json',qualification);print('OBSERVER',json.dumps(q),flush=True)
    observed=all(q['admitted'] for q in qualification)
    r.save(a.dest/'FORMAL_TIMER.json',dict(observe=observed,tails_admitted=observed,qualification_sha256=r.sha(a.dest/'COST_QUALIFICATION.json')))
    rows=[];reference=None
    for round,order in enumerate(ORDERS,1):
        for m in order:
            row=r.run(a,f'formal_r{round}_{MODES[m]}',case,MODES[m],observe=observed);row['round']=round
            if reference is None:reference=row
            assert r.equal_output(reference,row)
            rows.append(row);r.save(a.dest/'FORMAL_ROWS.json',rows)
    result=dict(formal_processes=30,observer_admitted=observed,modes={},comparisons={})
    by_mode={m:[x for x in rows if x['mode']==m] for m in MODES}
    for mode,xs in by_mode.items():
        result['modes'][mode]={key:dict(raw=[x['summary'][key] if key=='trace_ms' else x['region'][key] for x in xs],
                                      median=float(np.median([x['summary'][key] if key=='trace_ms' else x['region'][key] for x in xs])))
                               for key in ('trace_ms','setup_plus_trace_ms')}
    for i,j in PAIRS:
        left,right=MODES[i],MODES[j];stats={};order=[o.index(i)<o.index(j) for o in ORDERS]
        for key in ('trace_ms','setup_plus_trace_ms'):
            ratios=[(x['summary'][key]/y['summary'][key] if key=='trace_ms' else x['region'][key]/y['region'][key]) for x,y in zip(by_mode[left],by_mode[right])]
            stats[key]=r.paired(ratios,order)
        result['comparisons'][left+'/'+right]=stats
    r.save(a.dest/'RESULTS.json',result);r.save(a.dest/'COMPLETE.json',dict(state='completed',formal_processes=30,tails_admitted=observed))
    print('CAMPAIGN COMPLETE',json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('prepare','qualify','micro','campaign'))
    for name in ('raw','workflow','dest','u0','helpers'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gpu',required=True);a=p.parse_args();a.dest.mkdir(parents=True,exist_ok=True)
    globals()[a.phase](a)
