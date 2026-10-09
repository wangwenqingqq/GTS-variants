#!/usr/bin/env python3
"""Fail-closed exact-output binding and predeclared paired R/P, T/P, R/T tables."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import rtp
read=rtp.read;sha=rtp.sha;save=rtp.save

def paired(left,right,orders,l,r):
    x=np.asarray(left,float);y=np.asarray(right,float);assert x.shape==y.shape==(6,)
    assert np.isfinite(x).all() and np.isfinite(y).all() and (x>0).all() and (y>0).all()
    log=np.log(x/y);rng=np.random.default_rng(2026101002)
    samples=np.exp(log[rng.integers(0,6,(20000,6))].mean(axis=1));ci=np.quantile(samples,[.025,.975]).tolist()
    strata={}
    for first in (True,False):
        mask=np.asarray([o.index(l)<o.index(r) for o in orders])==first;assert mask.sum()==3
        strata[l+'_before_'+r if first else r+'_before_'+l]=float(np.exp(log[mask].mean()))
    ratio=float(np.exp(log.mean()));wins=int((x>y).sum())
    return dict(ratio=ratio,CI95=ci,wins=wins,raw_ratios=(x/y).tolist(),order_strata=strata,
        marginal_median_ratio=float(np.median(x)/np.median(y)),arithmetic_mean_ratio=float(np.mean(x)/np.mean(y)),
        confirmed_speedup=ci[0]>1 and wins>=5 and min(strata.values())>1,
        time_reduction_percent=100*(1-1/ratio),denominator='reference complete time / candidate complete time')

def binding(work,stage,a):
    reg=read(work/'REGISTERED.json');rows=read(work/'RAW_ROWS.json');assert reg['jobs']==rtp.jobs(stage) and len(rows)==len(reg['jobs'])
    assert reg['contract_sha256']==sha(rtp.HERE/'RTP_CONTRACT.json') and reg['binary_sha256']==sha(a.build/'bin/target')==rtp.CONTRACT['binary_sha256']
    assert reg['build_sha256']==sha(a.build/'BUILD.json') and reg['prepared_sha256']==sha(a.build/'PREPARED.json')
    assert reg['parent_source_sha256']==sha(rtp.HERE.parent/'build_distance_tiles/verify.py') and reg['guard_sha256']==sha(a.guard)
    if (work/'RESUME.json').exists():
        resume=read(work/'RESUME.json');assert stage=='bridge'
        assert resume['original_registration_sha256']==sha(work/'REGISTERED.json')
        assert resume['original_script_sha256']==reg['script_sha256']==sha(work/'EXECUTED.py')
        assert resume['corrected_script_sha256']==sha(work/'EXECUTED_RESUME.py')
    else:assert reg['script_sha256']==sha(work/'EXECUTED.py')
    assert reg['case_hashes']==read(a.cases/'CASES.json') and reg['data_sha256']==rtp.tiles.validate.TARGET_DATA_SHA256
    expected={j['label'] for j in reg['jobs']};assert {p.parent.name for p in (work/'guards').glob('*/receipt.json')}==expected
    reference=rtp.tiles.parent_binding(a.parent);assert reference==reg['reference']
    actual=[];guard_hashes={}
    for j,row in zip(reg['jobs'],rows):
        assert all(row[k]==v for k,v in j.items())
        checked=rtp.check_run(work,j,a.build,a.cases,a.parent,reference,a.library);assert checked==row
        command=read(work/(j['label']+'.command.json'));mode=rtp.CONTRACT['modes'][j['mode']]
        assert command['env']==dict(REGION_MODE=mode[0],BUILD_MAPPING=mode[1],KNN_MODE='FULL',TARGET_WARMUP='1',U10_OBSERVE='1',U10_TREE_AUDIT='0',TARGET_RESTORE_AUDIT='0')
        receipt=read(work/'guards'/j['label']/'receipt.json')
        assert receipt['command'][3:]==command['command']
        assert receipt['command'][1:3]==[f"--cpunodebind={reg['numa_node']}",f"--membind={reg['numa_node']}"]
        binary_index=command['command'].index(str(a.build/'bin/target'))
        expected_data=a.data if j['case'] in ('primary','million_prefix') else a.cases/j['case']/'data.f32bin'
        assert command['command'][binary_index+1]==str(expected_data)
        assert command['command'][binary_index+2]==str(a.cases/j['case']/'events.txt')
        for p in (work/'guards'/j['label']).iterdir():
            if p.is_file():guard_hashes[str(p.relative_to(work))]=sha(p)
        actual.append(checked)
    return dict(registration_sha256=sha(work/'REGISTERED.json'),raw_rows_sha256=sha(work/'RAW_ROWS.json'),guard_hashes=guard_hashes,rows=actual)

def main(a):
    outside=rtp.tiles.run.parent.base.outside_repo;out=outside(a.output);assert not out.exists()
    assert sha(a.data)==rtp.tiles.validate.TARGET_DATA_SHA256
    identities=read(a.cases/'CASES.json');assert all(sha(a.cases/k)==v for k,v in identities.items())
    bridge=binding(a.bridge,'bridge',a);primary=binding(a.work,'primary',a)
    br=read(a.bridge/'REGISTERED.json');pr=read(a.work/'REGISTERED.json')
    for k in br.keys()-{'stage','jobs','script_sha256','registered_unix'}:assert br[k]==pr[k],k
    clean=[]
    for row in primary['rows']:
        p=a.work/'outputs'/row['label'];s=read(str(p)+'.summary.json');scope=read(str(p)+'.scope.json');num=read(str(p)+'.numeric.json');region=read(str(p)+'.region.json');live=read(str(p)+'.unified.json')
        with Path(str(p)+'.ops.csv').open() as f:ops=list(csv.DictReader(f))
        r={k:row[k] for k in ('label','round','mode','order','trace_ms','setup_plus_trace_ms','initial_setup_ms','warmup_ms','final_release_ms','results','rebuilds','receipt_sha256','output_hashes')}
        r.update(parse_ms=scope['parse_ms'],context_ms=scope['context_ms'],cpu_user_s=s['cpu_user_s'],cpu_system_s=s['cpu_system_s'],
            sampled_device_peak_bytes=s['sampled_device_peak_bytes'],host_output_capacity_bytes=s['host_output_capacity_bytes'],
            ack={task:dict(sum_ms=sum(float(o['ack_ms']) for o in ops if int(o['flag'])==flag),
                 p50_p95_p99_ms=np.quantile([float(o['ack_ms']) for o in ops if int(o['flag'])==flag],[.5,.95,.99]).tolist())
                 for flag,task in enumerate(('insert','delete','range','knn'))},
            rebuild_inclusive_ms=sum(float(o['rebuild_ms']) for o in ops),inclusive_stages=s['stages'],
            numeric_refit=num,parallel_refresh=region.get('refresh_rows',[]),mirror_refresh=live.get('refresh_rows',[]))
        r['trace_residual_ms']=r['trace_ms']-r['final_release_ms']-sum(v['sum_ms'] for v in r['ack'].values())
        assert r['trace_residual_ms']>=-1e-6;clean.append(r)
    comparisons={}
    for scope in ('trace_ms','setup_plus_trace_ms'):
        comparisons[scope]={}
        for left,right in ('RP','TP','RT'):
            l=[next(r[scope] for r in clean if r['round']==i and r['mode']==left) for i in range(1,7)]
            r=[next(r[scope] for r in clean if r['round']==i and r['mode']==right) for i in range(1,7)]
            comparisons[scope][left+'/'+right]=paired(l,r,rtp.CONTRACT['orders'],left,right)
    distributions={scope:{m:dict(p10_median_p90_ms=np.quantile([r[scope] for r in clean if r['mode']==m],[.1,.5,.9]).tolist()) for m in 'RTP'} for scope in ('trace_ms','setup_plus_trace_ms')}
    result=dict(distributions=distributions,status='MEASURED_FIXED_SHORT_RTP',shape=rtp.CONTRACT['shape'],events=rtp.CONTRACT['events'],
        binary_sha256=rtp.CONTRACT['binary_sha256'],contract_sha256=sha(rtp.HERE/'RTP_CONTRACT.json'),rows=clean,comparisons=comparisons,
        binding=dict(bridge=bridge,primary=primary),new_primary_processes=18,new_GPU_qualifiers=5,cumulative_GPU_qualifiers=25,
        external_static_processes=0,limits=rtp.CONTRACT['limitations'],checker_sha256=sha(__file__),executed_driver_sha256=sha(a.work/'EXECUTED.py'),verification_helper_sha256=sha(rtp.__file__))
    save(out,result);print(json.dumps(comparisons,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','bridge','build','cases','parent','data','library','guard','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
