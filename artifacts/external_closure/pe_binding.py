#!/usr/bin/env python3
"""Independent offline chain binding, including the failed checker and all raw jobs."""
import json
from pathlib import Path
import numpy as np
from qualify import cpu
from pe_check import check
from pe_trace import warm_events
from pe_campaign import CONTRACT,jobs
read=lambda p:json.loads(Path(p).read_text())
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
HERE=Path(__file__).resolve().parent

def validate_target(events):
    content=Path(events).read_bytes()
    assert cpu.sha(events)=='5f440b3f5442499cd404fcb4821be95cf5cb4d04af63f7b6ead4bd10fec5ef96','target336 event identity'
    ops=np.loadtxt(events,skiprows=1,dtype=int,ndmin=2)
    assert int(content.splitlines()[0])==len(ops)==336
    assert [int((ops[:,0]==i).sum()) for i in range(4)]==[40,40,128,128]

def bind(a):
    w=a.work;original=read(w/'REGISTERED.json');reg=read(w/'RECOVERY.json')
    assert reg['original_registration_sha256']==cpu.sha(w/'REGISTERED.json') and reg['original_failure_sha256']==cpu.sha(w/'qualification/RESULTS.json')
    assert original['qualification_jobs']==jobs('qualification') and original['primary_jobs']==jobs('primary') and reg['recovery_jobs']==jobs('qualification')[1:]
    assert reg['contract_sha256']==original['contract_sha256']==cpu.sha(HERE/'PE_CONTRACT.json')
    assert reg['data_sha256']==original['data_sha256']==cpu.sha(a.data)==cpu.validate.TARGET_DATA_SHA256
    for registration,source in ((original,a.first_source),(reg,a.executed_source)):
        assert all(cpu.sha(source/p)==v for p,v in registration['source_hashes'].items()),'executed source identity'
    assert reg['binaries']==original['binaries']
    assert cpu.sha(a.p_build/'BUILD.json')==reg['p_build_sha256'] and cpu.sha(a.e_build/'BUILD.json')==reg['e_build_sha256']
    assert cpu.sha(a.p_build/'bin/target')==reg['binaries']['P'] and cpu.sha(a.e_build/'scan')==reg['binaries']['E']
    prepared=read(a.p_build/'PREPARED.json');assert all(cpu.sha(a.p_build/'source'/p)==v for p,v in prepared['sources'].items())
    ebuild=read(a.e_build/'REGISTERED.json');assert read(a.e_build/'BUILD.json')['registration_sha256']==cpu.sha(a.e_build/'REGISTERED.json')
    archive=next(Path(v) for v in ebuild['command'] if v.endswith('/libfaiss.a'));assert cpu.sha(archive)==ebuild['dependencies']['libfaiss.a']
    assert reg['cases']==original['cases'] and all(cpu.sha(w/'cases'/p)==v for p,v in reg['cases'].items())
    validate_target(w/'cases/target/events.txt')
    gold=next(r for r in read(HERE/'evidence/RTP_RESULTS.json')['rows'] if r['label']=='round_1_P')['output_hashes']
    assert reg['reference']==original['reference']==gold and all(cpu.sha(a.reference.parent/p)==v for p,v in gold.items())
    bindings=[];initial=read(w/'qualification/RESULTS.json');assert not initial['complete']
    assert [r['label'] for r in initial['rows']]==[j['label'] for j in jobs('qualification')]
    assert initial['rows'][0]['status']=='failed' and initial['rows'][0]['guard_exit']==0 and all(r['status']=='not_executed_after_stop' for r in initial['rows'][1:])
    for stage,expected in (('qualification',jobs('qualification')[:1]),('recovery',jobs('qualification')[1:]),('primary',jobs('primary'))):
        folder=w/stage;rows=read(folder/'RESULTS.json')['rows'];sr=read(folder/'REGISTERED.json')
        assert sr['parent_sha256']==cpu.sha(w/('REGISTERED.json' if stage=='qualification' else 'RECOVERY.json'))
        assert sr['jobs']==(jobs('qualification') if stage=='qualification' else expected)
        if stage!='qualification':assert read(folder/'RESULTS.json')['complete'] and len(rows)==len(expected)
        assert {p.parent.name for p in (folder/'guards').glob('*/receipt.json')}=={j['label'] for j in expected},'exact actual process inventory'
        assert {p.name for p in (folder/'guards').iterdir()}=={j['label'] for j in expected}
        for j,row in zip(expected,rows):
            assert all(row[k]==v for k,v in j.items())
            if stage!='qualification':assert row['status']=='passed'
            guard=folder/'guards'/j['label'];receipt=read(guard/'receipt.json');command=read(folder/(j['label']+'.command.json'))
            assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['gpu']==reg['gpu']
            assert not read(guard/'before.json')['apps'] and not read(guard/'after.json')['apps'] and all(not s['foreign'] for s in read(guard/'checks.json'))
            assert receipt['command']==read(guard/'command.json')==['numactl',f"--cpunodebind={reg['numa_node']}",f"--membind={reg['numa_node']}",*command['command']]
            c=w/'cases'/j['case'];data=a.data if j['case']=='target' else c/'data.f32bin';p=folder/'outputs'/j['label']
            binary=a.p_build/'bin/target' if j['method']=='P' else a.e_build/'scan'
            cmd=[str(binary),str(data),str(c/'events.txt'),'2',str(CONTRACT['shape']['radius']),str(p),'8'] if j['method']=='P' else [str(binary),str(data),str(c/'trace'),str(CONTRACT['shape']['radius']),str(p)]
            if j['tool']:
                actual=command['command'];assert Path(actual[0]).name=='compute-sanitizer' and actual[1:5]==['--tool',j['tool'],'--error-exitcode','97'];cmd=actual[:5]+cmd
                logs=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs
            assert cmd==command['command'] and receipt['binary_sha256']==cpu.sha(cmd[0])
            env=command['env'];assert env==dict(LD_LIBRARY_PATH=ebuild['environment']['LD_LIBRARY_PATH'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',REGION_MODE='PAR_STRONG',BUILD_MAPPING='TILED',KNN_MODE='FULL',TARGET_WARMUP='1',U10_OBSERVE='1',PE_TRACE=str(c/'trace'))
            warm=np.loadtxt(c/'warmup.events',skiprows=1,dtype=int,ndmin=2);assert warm.tolist()==[list(x) for x in warm_events()]
            ref=a.reference if j['case']=='target' else None
            checked={'measured':check(data,c/'events.txt',c/'trace',p,j['method'],ref), 'warmup':check(data,c/'warmup.events',str(c/'trace')+'.warmup',str(p)+'.warmup',j['method'],str(ref)+'.warmup' if ref else None)}
            assert checked['warmup']['queries']==8
            if j['case']=='target':assert checked['measured']['queries']==256 and checked['measured']['final_live']==1000000
            if stage=='qualification':assert {'measured':checked['measured'],'.warmup':checked['warmup']}==reg['first_sample_offline_recheck']
            else:
                assert checked==read(str(p)+'.quality.json') and cpu.sha(str(p)+'.quality.json')==row['quality_sha256'] and cpu.sha(guard/'receipt.json')==row['receipt_sha256']
            bindings.append(dict(stage=stage,label=j['label'],method=j['method'],full_quality=True,receipt_sha256=cpu.sha(guard/'receipt.json'),output_hashes={f.name:cpu.sha(f) for f in folder.glob('outputs/'+j['label']+'.*') if f.is_file()}))
    return dict(passed=True,qualification_processes=11,formal_processes=12,all23_runtime_receipts_bound=True,all_warmup_and_measured_payloads_rechecked=True,target_336_identity=True,first_checker_failure_retained=True,rows=bindings,
        registration_sha256=cpu.sha(w/'REGISTERED.json'),recovery_sha256=cpu.sha(w/'RECOVERY.json'),checker_sha256=cpu.sha(HERE/'pe_check.py'),binding_sha256=cpu.sha(__file__))
