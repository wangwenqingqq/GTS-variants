"""Prospective process-level estimators and the plan's unchanged point gates."""
import argparse,csv,json,math,random,statistics
from pathlib import Path

def percentile(values,p):
    s=sorted(values);i=(len(s)-1)*p;lo=int(i);return s[lo]+(s[min(lo+1,len(s)-1)]-s[lo])*(i-lo)
def geometric(v):return math.exp(statistics.mean(math.log(x) for x in v))
def classify(inflation,recovery,n1,r0):
    if any(not math.isfinite(x) for x in (inflation,recovery,n1,r0)) or min(n1,r0)<=0:return 'UNCLASSIFIED'
    if inflation>2 or recovery<.30:return 'BASELINE_NOT_FIXED'
    if inflation<=1.5 and recovery>=.70 and n1<=1.15*r0:return 'BASELINE_FIXED_MEMORY_LIMIT'
    if inflation<=1.5 and n1>1.15*r0 and (n1-r0)/n1>=.20:return 'BASELINE_FIXED_RESIDUAL_COMPUTE'
    return 'UNCLASSIFIED'
def load(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def metric_record(path):
    with Path(path).open() as f:rows=list(csv.reader(f))
    assert len(rows)==3
    assert len(rows[0])==len(rows[1])==len(rows[2])
    units=dict(zip(rows[0],rows[1]));data=dict(zip(rows[0],rows[2]));record={}
    for k,v in data.items():
        if k.startswith(('gpu__','dram__','sm__','smsp__','launch__','lts__')) and v:
            try:value=float(v.replace(',',''))
            except ValueError:
                assert k.startswith('launch__') and units[k]=='','non-numeric performance metric'
                value=v # LaunchStats enum fields are retained, not treated as numeric counters.
            record[k]={'value':value,'unit':units[k]}
    duration=record['gpu__time_duration.avg'];factors={'nsecond':1e-9,'usecond':1e-6,'msecond':1e-3,'second':1.,'ns':1e-9,'us':1e-6,'ms':1e-3,'s':1.}
    assert duration['unit'] in factors,('unknown NCU duration unit',duration)
    seconds=duration['value']*factors[duration['unit']]
    for k in ('dram__bytes.sum','dram__bytes_op_read.sum','dram__bytes_op_write.sum'):assert record[k]['unit']=='byte'
    fadd=record['smsp__sass_thread_inst_executed_op_fadd_pred_on.sum']['value']
    fmul=record['smsp__sass_thread_inst_executed_op_fmul_pred_on.sum']['value']
    ffma=record['smsp__sass_thread_inst_executed_op_ffma_pred_on.sum']['value']
    return dict(kernel=data['Kernel Name'],diagnostic_only=True,capture_count=1,metrics=record,
        kernel_ms=seconds*1000,DRAM_GBs=record['dram__bytes.sum']['value']/seconds/1e9,
        read_GBs=record['dram__bytes_op_read.sum']['value']/seconds/1e9,
        executed_FP32_proxy=fadd+fmul+2*ffma,work_inflation=(fadd+fmul+2*ffma)/2879000000)
def analyze(work,out):
    assert load(work/'qualification/RESULTS.json')['complete'] and load(work/'primary/RESULTS.json')['complete'] and load(work/'ncu/RESULTS.json')['complete']
    out.mkdir(exist_ok=False);modes={};samples={}
    for m in ('N0','N1','R0'):
        checked=[load(work/'primary'/f'r{r}_{m}.checked.json') for r in range(1,7)]
        means=[j['mean_query_ms'] for j in checked];samples[m]=means
        modes[m]=dict(process_means_ms=means,median_process_mean_ms=statistics.median(means),p10_ms=percentile(means,.1),p90_ms=percentile(means,.9),
            process_pass_ms=[j['pass_ms'] for j in checked],median_pass_ms=statistics.median(j['pass_ms'] for j in checked),query_ACK_ms=[j['query_ack_ms'] for j in checked])
    med={m:modes[m]['median_process_mean_ms'] for m in modes}
    recovery=(med['N0']-med['N1'])/(med['N0']-med['R0']) if med['N0']>med['R0'] else None
    ratios={key:[samples[a][i]/samples[b][i] for i in range(6)] for key,a,b in [('N1_over_N0','N1','N0'),('R0_over_N0','R0','N0'),('N1_over_R0','N1','R0')]}
    draws={k:[] for k in ratios};recoveries=[];rng=random.Random(2026101212)
    for _ in range(20000):
        idx=[rng.randrange(6) for _ in range(6)]
        for k,v in ratios.items():draws[k].append(geometric([v[i] for i in idx]))
        mm={m:statistics.median(samples[m][i] for i in idx) for m in modes}
        if mm['N0']>mm['R0']:recoveries.append((mm['N0']-mm['N1'])/(mm['N0']-mm['R0']))
    paired={k:dict(ratios=v,geometric_ratio=geometric(v),CI95=[percentile(draws[k],.025),percentile(draws[k],.975)],
        wins_below_one=sum(x<1 for x in v),forward_geometric=geometric(v[::2]),reverse_geometric=geometric(v[1::2])) for k,v in ratios.items()}
    profiles={m:metric_record(work/'ncu/reports'/f'{m}.base.csv') for m in modes}
    infl=profiles['N1']['work_inflation'];bw={m:profiles[m]['DRAM_GBs'] for m in modes}
    bandwidth_recovery=(bw['N1']-bw['N0'])/(bw['R0']-bw['N0']) if bw['R0']>bw['N0'] else None
    label=classify(infl,recovery if recovery is not None else float('nan'),med['N1'],med['R0'])
    result=dict(primary_scope='Host request ready -> complete Host output ready;R0 structural control only',modes=modes,paired=paired,
        native_relative_latency=med['N1']/med['N0'],native_speedup=med['N0']/med['N1'],native_latency_reduction=1-med['N1']/med['N0'],
        native_minus_readonly_ms=med['N0']-med['R0'],nonpadded_minus_readonly_ms=med['N1']-med['R0'],
        nonpadded_over_readonly=med['N1']/med['R0'],residual_fraction=(med['N1']-med['R0'])/med['N1'],
        latency_recovery=recovery,latency_recovery_CI95=[percentile(recoveries,.025),percentile(recoveries,.975)] if len(recoveries)==20000 else None,
        undefined_recovery_bootstrap_draws=20000-len(recoveries),work_inflation=infl,bandwidth_recovery=bandwidth_recovery,
        decision=label,decision_basis='original point gates;grayzone human clarified;CI never hidden',
        static_baseline_direction_pass=infl<=1.5 and paired['N1_over_N0']['CI95'][1]<1,
        profiler_duration_not_primary=True,new_GPU_starts=len((work/'STARTS.jsonl').read_text().splitlines()))
    write(out/'BASELINE_TIMING.json',result)
    for m,v in profiles.items():write(out/(m+'_METRICS.json'),v)
    print(json.dumps({k:result[k] for k in ('decision','native_speedup','native_latency_reduction','latency_recovery','latency_recovery_CI95','nonpadded_over_readonly','residual_fraction','work_inflation','bandwidth_recovery','new_GPU_starts')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();analyze(a.work,a.out)
