"""Scalar interpretation of frozen counters, launch geometry and fresh-process ACKs."""
import argparse
import csv
import json
from pathlib import Path
import importlib.util
import numpy as np
from prepare import read, save, sha, HERE

spec=importlib.util.spec_from_file_location('exact_scan_forensic',HERE.parent/'exact_scan_breakdown_20261011/forensic.py')
forensic=importlib.util.module_from_spec(spec);spec.loader.exec_module(forensic)
selected=forensic.selected

def distribution(values):
    a=np.asarray(values,float)
    assert a.shape==(6,) and np.isfinite(a).all() and (a>0).all()
    lo,mid,hi=np.quantile(a,[.1,.5,.9])
    return dict(median=float(mid),p10=float(lo),p90=float(hi),process_values=a.tolist())

def counters(base,sass):
    rows=list(csv.reader(base.read_text().splitlines()));assert len(rows)==3
    headers,units,values=rows;assert len(headers)==len(units)==len(values)
    raw={k:dict(unit=u,value=v) for k,u,v in zip(headers,units,values)}
    number=lambda k:float(raw[k]['value'].replace(',',''))
    assert raw['Kernel Name']['value']=='pairwise_matrix_kernel'
    assert raw['gpu__time_duration.avg']['unit'] in ('ns','nsecond')
    seconds=number('gpu__time_duration.avg')/1e9;dram=number('dram__bytes.sum')
    add,mul,fma=[number('smsp__sass_thread_inst_executed_op_'+op+'_pred_on.sum') for op in ('fadd','fmul','ffma')]
    fp64=[number('smsp__sass_thread_inst_executed_op_'+op+'_pred_on.sum') for op in ('dadd','dmul','dfma')]
    normal,identity=selected(sass.read_text())
    return dict(kernel_ms=seconds*1000,DRAM_bytes=dram,DRAM_read_bytes=number('dram__bytes_op_read.sum'),DRAM_write_bytes=number('dram__bytes_op_write.sum'),DRAM_GBs=dram/seconds/1e9,L2_bytes=number('lts__t_bytes.sum'),FP32_FADD=add,FP32_FMUL=mul,FP32_FFMA=fma,executed_FP32_proxy=add+mul+2*fma,FP64_counters=fp64,SM_throughput_percent=number('sm__throughput.avg.pct_of_peak_sustained_elapsed'),occupancy_percent=number('sm__warps_active.avg.pct_of_peak_sustained_active'),geometry=dict(runtime_function=raw['Kernel Name']['value'],grid=[int(number('launch__grid_dim_'+v)) for v in 'xyz'],block=[int(number('launch__block_dim_'+v)) for v in 'xyz'],registers_per_thread=number('launch__registers_per_thread'),allocated_registers_per_thread=number('launch__registers_per_thread_allocated'),shared_static_bytes=number('launch__shared_mem_per_block_static'),shared_dynamic_bytes=number('launch__shared_mem_per_block_dynamic'),shared_driver_bytes=number('launch__shared_mem_per_block_driver'),stack_bytes=number('launch__stack_size'),**identity),raw_base_csv_sha256=sha(base),raw_selected_export_sha256=sha(sass),scope='one complete selected native distance launch, same-NCU duration; main-kernel counters only, not complete output ACK')

def fit(rows,contract):
    bs=np.array(contract['models']['fit_B']);U=contract['workload']['useful_ops_per_query']
    y=np.array([rows[str(b)]['executed_FP32_proxy'] for b in bs]);inflation=y/(U*bs)
    models={}
    for T in contract['models']['M1_tiles']:
        expected=np.ceil(bs/T)*T*U;error=np.abs(y-expected)/expected
        models['T'+str(T)]=dict(T=T,expected_work=expected.tolist(),relative_errors=error.tolist(),median_relative_error=float(np.median(error)),max_relative_error=float(error.max()))
    c=float(inflation.mean());error=np.abs(inflation-c)/c
    models['M0']=dict(c=c,relative_errors=error.tolist(),median_relative_error=float(np.median(error)))
    native=[rows[str(b)]['geometry'] for b in bs]
    same64=len({g['normalized_sha256'] for g in native})==1 and len({tuple(g['block']) for g in native})==1 and len({tuple(g['grid']) for g in native})==1
    g64,g128=rows['64']['geometry'],rows['128']['geometry']
    axes=[i for i in range(3) if g128['grid'][i]==2*g64['grid'][i] and all(g128['grid'][j]==g64['grid'][j] for j in range(3) if j!=i)]
    geometry=same64 and bool(axes) and g64['normalized_sha256']==g128['normalized_sha256']
    f_ratio=(rows['64']['executed_FP32_proxy']/64)/rows['1']['executed_FP32_proxy'];d_ratio=(rows['64']['DRAM_bytes']/64)/rows['1']['DRAM_bytes']
    separation=abs(float(np.log2(f_ratio)-np.log2(d_ratio)));decoupled=separation>=1
    i64=rows['64']['executed_FP32_proxy']/(64*U);i1=rows['1']['executed_FP32_proxy']/U
    reject=(i64/i1>=.8 and models['M0']['median_relative_error']<=.15) or (models['T64']['median_relative_error']>.30 and i64/i1>=.5)
    confirm=models['T64']['median_relative_error']<=.15 and i64<=1.5 and geometry and decoupled
    decision='CONFIRM_PADDING' if confirm else 'REJECT_PADDING' if reject else 'PARTIAL_PADDING'
    return dict(models=models,B64_inflation=i64,B64_B1_inflation_ratio=i64/i1,geometry_support=dict(passed=geometry,same_function_block_grid_B1_through_B64=same64,doubled_query_axis_candidates=axes,B128_same_function=g64['normalized_sha256']==g128['normalized_sha256'],scope='independent discrete launch-geometry support among the four frozen tile candidates; not direct recovered source constant'),traffic=dict(FP32_per_query_normalized_B64=f_ratio,DRAM_per_query_normalized_B64=d_ratio,separation_log2=separation,passed_decoupling_gate=decoupled,caveat='shared database reuse can decrease both per-query proxies together; failed decoupling is not evidence of no arithmetic padding'),decision=decision)

def analyze(a):
    w=a.work;c=read(HERE/'CONTRACT.json');out=a.output;out.mkdir(exist_ok=False)
    timing={};keeper=[]
    for job in read(w/'keeper/RESULTS.json')['rows']:
        assert job['status']=='passed';q=read(w/'keeper'/(job['label']+'.checked.json'));keeper.append(q['mean_invocation_ms'])
    for B in c['workload']['B']:
        checks=[read(w/'primary'/(f'r{r}_B{B}.checked.json')) for r in range(1,7)]
        timing[str(B)]=dict(B=B,invocation_ms=distribution([v['mean_invocation_ms'] for v in checks]),query_ms=distribution([v['mean_query_ms'] for v in checks]),pass_ms=distribution([v['pass_ms'] for v in checks]),queries_per_second=distribution([1000/v['mean_query_ms'] for v in checks]),mean_hits=[v['mean_measured_hits'] for v in checks],pool='original32' if B<=32 else 'registered128',vs_repeated_single=None)
    rng=np.random.default_rng(2026101212);k=np.array(keeper);b=np.array(timing['1']['invocation_ms']['process_values']);bootstrap=[]
    for _ in range(20000):bootstrap.append(float(np.mean(b[rng.integers(0,6,6)])/np.mean(k[rng.integers(0,6,6)])))
    ci=np.quantile(bootstrap,[.025,.975]);historical=timing['1']['invocation_ms']['median']/3.354495015625
    stability=dict(same_campaign_original_keeper=distribution(keeper),B1_keeper_unpaired_mean_ratio=float(b.mean()/k.mean()),ratio_ci95=ci.tolist(),historical_median_ratio=historical,scope='stability/reproduction gate, not genuinely paired performance comparison',passed=bool(ci[0]>=.8 and ci[1]<=1.2 and .8<=historical<=1.2))
    work={}
    for B in c['workload']['B']:
        stem=w/'ncu/reports'/f'B{B}';v=counters(Path(str(stem)+'.base.csv'),Path(str(stem)+'.sass.txt'));v.update(B=B,useful_ops=c['workload']['useful_ops_per_query']*B,inflation=v['executed_FP32_proxy']/(c['workload']['useful_ops_per_query']*B),inflation_times_B=v['executed_FP32_proxy']/c['workload']['useful_ops_per_query'],DRAM_bytes_per_query=v['DRAM_bytes']/B);work[str(B)]=v
    prior=read(HERE.parent/'exact_scan_breakdown_20261011/evidence/METRICS.json')['metrics']['full']
    stable_counters=all(abs(work['1'][new]/prior[old]-1)<=.01 for new,old in (('FP32_FADD','FP32_pred_on_add'),('FP32_FFMA','FP32_pred_on_fma')))
    prior_hash=read(HERE.parent/'exact_scan_breakdown_20261011/evidence/METRICS.json')['selected_function_identity']['full']['normalized_sha256']
    stability.update(counter_reproduction=stable_counters,selected_function_identity_reproduced=work['1']['geometry']['normalized_sha256']==prior_hash)
    stability['passed']=bool(stability['passed'] and stable_counters and stability['selected_function_identity_reproduced'])
    result=fit(work,c);result.update(B1_reproduction=stability,final_decision_valid=stability['passed'],scope='diagnostic only; no new mechanism, native keeper promotion or E2E improvement')
    save(out/'BATCH_SCALING.json',timing);save(out/'EXECUTED_WORK.json',work);save(out/'TILE_MODEL_FIT.json',result)
    save(out/'FUNCTION_IDENTITY.json',dict(rows={b:v['geometry'] for b,v in work.items()},function_switch_B=[int(b) for i,b in enumerate(work) if i>0 and work[b]['geometry']['normalized_sha256']!=work[list(work)[i-1]]['geometry']['normalized_sha256']],module_boundary='full runtime/JIT cubin image unavailable; exact shared library ELF hashes and raw report/function-text hashes retained; vendor SASS excluded from public artifact'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);analyze(p.parse_args())
