#!/usr/bin/env python3
"""Publish only a verified4+44+24 matrix, preserving the original paired estimator."""
import argparse,ast,copy,json
from pathlib import Path
import numpy as np
import static_recovery2 as recovery
from static_check import read
from qualify import cpu
from rtp_results import paired
c=recovery.c
# Run this offline file separately while importing the unchanged executed tree.
HERE=recovery.HERE

def scope_time(row,scope):
    return row[scope] if scope!='both_task_lifecycle_ms' else sum(row[k] for k in ('preparation_ms','build_ms','knn_pass_ms','range_pass_ms','release_ms'))

def input_identities(records):
    # Bounded qualification inputs have no target snapshot metadata.
    return {name:{key:records[name][key] for key in ('data_sha256','snapshot_sha256','qids')} for name in c.CONTRACT['snapshots']}

def comparisons(rows):
    assert [r['label'] for r in rows]==[j['label'] for j in c.jobs('primary')]
    result={}
    for snapshot in c.CONTRACT['snapshots']:
        result[snapshot]={}
        for scope in ('knn_pass_ms','range_pass_ms','both_task_lifecycle_ms'):
            methods=[m for m in c.CONTRACT['orders'][0] if m not in ('GPU_TREE_ADAPT','GTSPP_P') and (scope=='knn_pass_ms' and m!='GPU_RANGE_COMPLETE' or scope=='range_pass_ms' and m!='GPU_FLAT_KNN' or scope=='both_task_lifecycle_ms' and m.startswith('CPU'))]
            group={}
            for m in methods:
                left=[scope_time(next(r for r in rows if r['snapshot']==snapshot and r['round']==i and r['method']==m),scope) for i in range(1,7)]
                right=[scope_time(next(r for r in rows if r['snapshot']==snapshot and r['round']==i and r['method']=='GTSPP_P'),scope) for i in range(1,7)]
                group[m+'/GTSPP_P']=paired(left,right,c.CONTRACT['orders'],m,'GTSPP_P')
            result[snapshot][scope]=group
    return result

def original_comparisons(rows):
    # Execute only the existing pure estimator block as a regression oracle.
    module=ast.parse((HERE/'static_results.py').read_text());main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    start=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='comparisons' for t in n.targets))
    code=ast.Module(body=copy.deepcopy(main.body[start:start+2]),type_ignores=[])
    env=dict(rows=rows,campaign=c,paired=paired);exec(compile(ast.fix_missing_locations(code),'frozen_comparison_block','exec'),env)
    return env['comparisons']

def collect(a):
    binding=recovery.verify(a);inputs=read(a.work/'INPUTS.json');plan=c.jobs('primary');rows=[];batches={}
    dependencies={name:dict(versions=env['versions'],module_sha256={key:value['sha256'] for key,value in env['modules'].items()}) for name,env in read(a.preflight)['dependencies'].items()}
    identities=input_identities(inputs['records'])
    keep=('preparation_ms','build_ms','warmup_ms','release_ms','range_pass_ms','knn_pass_ms','representation_bytes','index_bytes','memory_before','memory_built','memory_final','device_memory','device_used_before','device_used_built','device_used_final','workspace_bytes','context_ms','host_query_upload_bytes','extra_nonindexed_query_bytes')
    for batch,jobs in [('primary',plan[:4]),('recovery',plan[4:48]),('recovery2',plan[48:])]:
        folder=a.work/batch;raw=read(folder/'ROWS.json');reg=read(folder/'REGISTERED.json')
        assert list(raw)==[j['label'] for j in jobs]
        batches[batch]=dict(valid=len(jobs),registered_unix=reg['registered_unix'],registration_sha256=cpu.sha(folder/'REGISTERED.json'),rows_sha256=cpu.sha(folder/'ROWS.json'),guard_sha256=reg['guard_sha256'])
        for job in jobs:
            label=job['label'];actual=raw[label];meta=actual['timing'];prefix=folder/'outputs'/label
            clean={k:meta[k] for k in keep if k in meta};clean.update(process=read(folder/(label+'.process.json')),per_query_ms=actual['per_query_ms'])
            if job['method']=='GTSPP_P':
                summary=read(str(prefix)+'.summary.json');clean.update(sampled_device_peak_bytes=summary['sampled_device_peak_bytes'],host_output_capacity_bytes=summary['host_output_capacity_bytes'])
            rows.append(dict(**job,**clean,batch=batch,queries=actual['queries'],items=actual['items'],canonical_sha256=actual['canonical_sha256'],output_hashes=actual['output_hashes'],receipt_sha256=cpu.sha(folder/'guards'/label/'receipt.json'),quality_passed=True))
    measured=comparisons(rows);assert measured==original_comparisons(rows)
    distributions={}
    for snapshot in c.CONTRACT['snapshots']:
        distributions[snapshot]={}
        for method in c.CONTRACT['orders'][0]:
            group=[r for r in rows if r['snapshot']==snapshot and r['method']==method]
            if not group:continue
            distributions[snapshot][method]={k:dict(raw_ms=[r[k] for r in group],p10_median_p90_ms=np.quantile([r[k] for r in group],[.1,.5,.9]).tolist()) for k in ('preparation_ms','build_ms','warmup_ms','release_ms','knn_pass_ms','range_pass_ms') if all(k in r for r in group)}
            if all('knn_pass_ms' in r and 'range_pass_ms' in r for r in group):
                times=[scope_time(r,'both_task_lifecycle_ms') for r in group]
                distributions[snapshot][method]['both_task_lifecycle_ms']=dict(raw_ms=times,p10_median_p90_ms=np.quantile(times,[.1,.5,.9]).tolist())
    return dict(status='MEASURED_COMPLETE_EXTERNAL_STATIC_4_44_24',shape=c.CONTRACT['shape'],hardware=read(HERE/'evidence/STATIC_QUALIFICATION.json')['hardware'],dependencies=dependencies,input_identities=identities,contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),rows=rows,comparisons=measured,distributions=distributions,batches=batches,binding=binding,prior_failure_proof_sha256=cpu.sha(a.prior_proof),binary_sha256=read(a.build/'BUILD.json')['binaries'],inputs_sha256=cpu.sha(a.work/'INPUTS.json'),checker_sha256=cpu.sha(__file__),frozen_estimator_sha256=cpu.sha(HERE/'rtp_results.py'),old_analyzer_sha256=cpu.sha(HERE/'static_results.py'),external_valid_processes=72,external_primary_attempts=74,total_primary_attempts_including_RTP=92,retained_failures=2,old_GPU_qualifiers=32,blocked=c.CONTRACT['blocked'],limits=c.CONTRACT['limits'])

def reports(result):
    out={};names={'knn_pass_ms':'EXTERNAL_KNN_RESULTS.md','range_pass_ms':'EXTERNAL_RANGE_RESULTS.md','both_task_lifecycle_ms':'EXTERNAL_LIFECYCLE_RESULTS.md'}
    for scope,name in names.items():
        title={'knn_pass_ms':'External static kNN','range_pass_ms':'External static range','both_task_lifecycle_ms':'External dual-task static lifecycle'}[scope]
        lines=[f'# {title}', '', 'N1M/D960/B1/K8, FP32 inputs; radius bits `0x3f34a3d8`. Six fresh processes per method/snapshot, eight warmups and32 measured calls per supported task. Ratios are comparator/P; values below1 favor the comparator.', '', 'The matrix is4+44+24 valid observations. Both failed attempts remain excluded from estimates but retained in the budget (74 external attempts;92 including18 internal). The three registration batches and changed ownership observer are recorded; no incomplete batch is substituted for the frozen estimate.', '']
        if scope=='both_task_lifecycle_ms':lines+=['Scope: preparation + build +32 kNN +32 range + native/index resource release. Warmup/context and process setup/serialization are separate; retained-client-output destruction is excluded. Only dual-task CPU portfolios are paired against dual-task P; single-task GPU Flat/range are not divided by this denominator. This is not full-program time or a dynamic update workflow.', '']
        else:lines+=['Scope: continuous32-query Host-input-to-complete-Host-ID/FP32-field-ready pass on a prebuilt index. Preparation, build, warmup and native/index resource release are separate; serialization and retained-client-output destruction are excluded. This is not full-program or update-workflow time.', '']
        lines+=['All72 admitted processes pass complete membership and frozen numeric-field checks; the two failed attempts are excluded from the admitted matrix. The isolation-invalid attempt retains its separate output-quality pass; correct answers do not repair failed isolation. CPU_FLAT below means CPU_FLAT_INCLUSIVE_ADAPT (native kNN; explicitly inclusive range adapter).', '']
        lines+=['| Snapshot | Comparator | Comparator median ms | P median ms | Paired ratio |95% CI | P wins/6 | Comparator-first / P-first | Confirmed P gain |','|---|---|---:|---:|---:|---|---:|---|---|']
        for snapshot,scopes in result['comparisons'].items():
            for label,r in sorted(scopes[scope].items(),key=lambda item:(not item[0].startswith('GPU'),item[0])):
                method=label.split('/')[0];s=r['order_strata'];lo,hi=r['CI95'];order=f"{s[method+'_before_GTSPP_P']:.6f} / {s['GTSPP_P_before_'+method]:.6f}"
                medians=[float(np.median([scope_time(row,scope) for row in result['rows'] if row['snapshot']==snapshot and row['method']==m])) for m in (method,'GTSPP_P')]
                lines.append(f"| {snapshot} | {method} | {medians[0]:.6f} | {medians[1]:.6f} | {r['ratio']:.6f} | [{lo:.6f}, {hi:.6f}] | {r['wins']} | {order} | {'yes' if r['confirmed_speedup'] else 'no'} |")
        if scope!='both_task_lifecycle_ms':
            lines+=['', '## Absolute pass distribution and average query cost', '', 'Six observed pass times: p10 / median / p90, not a confidence interval. Average query cost is each pass divided by32; its median is shown below, not a latency percentile.', '', '| Snapshot | Method |32-query pass p10 / median / p90 ms | Median average ms/query |','|---|---|---|---:|']
            for snapshot in c.CONTRACT['snapshots']:
                for method in c.CONTRACT['orders'][0]:
                    times=[r[scope] for r in result['rows'] if r['snapshot']==snapshot and r['method']==method and scope in r]
                    if not times:continue
                    p10,median,p90=np.quantile(times,[.1,.5,.9])
                    lines.append(f'| {snapshot} | {method} | {p10:.6f} / {median:.6f} / {p90:.6f} | {median/32:.6f} |')
        else:
            lines+=['', '## Phase medians (ms)', '', 'All methods are listed to retain setup costs; a dash is an unsupported task, never zero. Warmup is separate. Lifecycle medians are computed per complete process, not by summing phase medians. Single-task GPU lifecycle ratios remain inadmissible.', '', '| Snapshot | Method | Preparation | Build | Warmup | kNN pass | Range pass | Native/index release | Dual-task lifecycle |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
            for snapshot in c.CONTRACT['snapshots']:
                for method in c.CONTRACT['orders'][0]:
                    group=[r for r in result['rows'] if r['snapshot']==snapshot and r['method']==method]
                    if not group:continue
                    cells=[]
                    for key in ('preparation_ms','build_ms','warmup_ms','knn_pass_ms','range_pass_ms','release_ms'):
                        cells.append(f'{np.median([r[key] for r in group]):.6f}' if all(key in r for r in group) else '—')
                    cells.append(f"{np.median([scope_time(r,scope) for r in group]):.6f}" if all('knn_pass_ms' in r and 'range_pass_ms' in r for r in group) else '—')
                    lines.append('| '+ ' | '.join([snapshot,method,*cells])+' |')
        lines+=['', 'Complete phase distributions, all72 raw rows, process CPU/RSS and returned payload/guard hashes are in `evidence/EXTERNAL_STATIC_COMPLETE.json`. The estimator is byte-bound and reproduces the original paired calculation:20,000 bootstrap resamples, seed2026101002. Confirmation requires lower95% bound>1, at least5/6 wins and both order strata>1; an unconfirmed row is not automatically a tie.', '', 'Limits: observed diagnostic queries, shared host, native single-thread CPU latency (not full-machine throughput); CPU_FLAT is the explicitly inclusive adapter, KD/Ball leaf512. GPU-Tree is absent from these timings (range correctness is separate; kNN safety remains blocked), MVPT provenance/output remain open. No universal GPU-tree, coalescing-only, held-out, dynamic,100k/1B or leak-clean claim; the96B context-symbol limitation remains.','']
        out[name]='\n'.join(lines)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','build','guard','prior-guard','prior-proof','qualification-source','original-source','cpu-python','gpu-python','preflight','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True);a=p.parse_args();assert __debug__
    a.output=c.outside_repo(a.output);assert not a.output.exists();result=collect(a);a.output.mkdir()
    cpu.save(a.output/'EXTERNAL_STATIC_COMPLETE.json',result)
    for name,text in reports(result).items():(a.output/name).write_text(text)
    print('PASS complete72; frozen statistics and three scoped tables',flush=True)
