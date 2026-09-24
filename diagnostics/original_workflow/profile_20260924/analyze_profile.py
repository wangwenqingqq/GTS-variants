#!/usr/bin/env python3
"""Validate raw outputs, summarize clean host clocks, and attribute NVTX intervals."""
import argparse
from collections import defaultdict
import csv
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import statistics as st
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import prepare
spec = importlib.util.spec_from_file_location('timeline', HERE.parent.parent/'original_flow_20260923/analyze.py')
timeline = importlib.util.module_from_spec(spec); spec.loader.exec_module(timeline)


def phases(text):
    out = {}
    for line in text.splitlines():
        x = line.split(',')
        if len(x)==5 and x[0]=='GTS_DIAG' and x[2].isdigit():
            out[x[1]] = {'count':int(x[2]),'wall_ms':float(x[3])*1000,'cpu_ms':float(x[4])*1000}
    return out


def trace(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True); db.row_factory=sqlite3.Row
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    names = dict(db.execute('SELECT id,value FROM StringIds'))
    def rows(name):return list(db.execute('SELECT * FROM '+name)) if name in tables else []
    def title(r):return r['text'] or names.get(r['textId'],'')
    nvtx = [r for r in rows('NVTX_EVENTS') if r['end'] and r['end']>r['start']]
    whole = [r for r in nvtx if title(r)=='update.total']; assert len(whole)==1
    lo, hi = whole[0]['start'], whole[0]['end']
    kernel = rows('CUPTI_ACTIVITY_KIND_KERNEL'); copies=rows('CUPTI_ACTIVITY_KIND_MEMCPY')
    sets = rows('CUPTI_ACTIVITY_KIND_MEMSET'); apis=rows('CUPTI_ACTIVITY_KIND_RUNTIME')
    cpu_fault = rows('CUDA_UM_CPU_PAGE_FAULT_EVENTS'); gpu_fault=rows('CUDA_UM_GPU_PAGE_FAULT_EVENTS')
    copy_names = {r['id']:r['label'] for r in rows('ENUM_CUDA_MEMCPY_OPER')}
    mem_names = {r['id']:r['label'] for r in rows('ENUM_CUDA_MEM_KIND')}
    selected = [r for r in nvtx if lo<=r['start'] and r['end']<=hi]
    groups = defaultdict(list)
    for r in selected:groups[title(r)].append(r)
    output = {}
    for name, spans in groups.items():
        intervals = [(r['start'],r['end']) for r in spans]
        def inside(t):return any(a<=t<b for a,b in intervals)
        def time_union(items):
            return timeline.length([z for a,b in intervals for z in timeline.clipped(items,a,b)])/1e6
        ks=[r for r in kernel if inside(r['start'])]
        cs=[r for r in copies if inside(r['start'])]
        ats=[r for r in apis if inside(r['start']) and any(s['globalTid']==r['globalTid'] and s['start']<=r['start']<s['end'] for s in spans)]
        kd=defaultdict(lambda:{'calls':0,'ms':0}); ad=defaultdict(lambda:{'calls':0,'inclusive_ms':0})
        cd=defaultdict(lambda:{'calls':0,'bytes':0,'ms':0})
        for r in ks:
            d=kd[names[r['shortName']]];d['calls']+=1;d['ms']+=(r['end']-r['start'])/1e6
        for r in ats:
            d=ad[names[r['nameId']]];d['calls']+=1;d['inclusive_ms']+=(r['end']-r['start'])/1e6
        for r in cs:
            label=copy_names[r['copyKind']]+' | '+str(mem_names.get(r['srcKind'],r['srcKind']))+' -> '+str(mem_names.get(r['dstKind'],r['dstKind']))
            d=cd[label];d['calls']+=1;d['bytes']+=r['bytes'];d['ms']+=(r['end']-r['start'])/1e6
        wall=timeline.length(intervals)/1e6; busy=time_union(kernel+copies+sets)
        output[name]={'calls':len(spans),'host_span_ms':wall,'gpu_union_ms':busy,
                      'gpu_temporal_fraction':busy/wall,'kernel_union_ms':time_union(kernel),
                      'no_recorded_gpu_work_ms':wall-busy,'kernels':dict(sorted(kd.items(),key=lambda x:-x[1]['ms'])),
                      'cuda_api':dict(sorted(ad.items(),key=lambda x:-x[1]['inclusive_ms'])),
                      'copies':dict(cd),
                      'cpu_um_fault_events':sum(inside(r['start']) for r in cpu_fault) if 'CUDA_UM_CPU_PAGE_FAULT_EVENTS' in tables else None,
                      'gpu_um_fault_count':sum(r['numberOfPageFaults'] for r in gpu_fault if inside(r['start'])) if 'CUDA_UM_GPU_PAGE_FAULT_EVENTS' in tables else None}
    diagnostic_tables=[t for t in tables if 'DIAGNOSTIC' in t and not t.startswith('ENUM_')]
    diagnostics={t:[dict(r) for r in rows(t)] for t in diagnostic_tables}
    db.close()
    return {'scope':'update.total only; initial build/input/context excluded. Nested ranges overlap; do not add API wall and GPU time. GPU temporal coverage is not SM utilization. Traced timing is diagnostic only.',
            'ranges':output,'diagnostics':diagnostics}


def analyze(root,out):
    manifest=json.loads((root/'manifest.json').read_text())
    all_runs={p.parent.name:json.loads(p.read_text()) for p in sorted((root/'runs').glob('*/receipt.json'))}
    planned={x[0] for p in (root/'logs').glob('plan_*.json') for x in json.loads(p.read_text())['plan']}
    assert len(planned)==36 and set(all_runs)==planned
    scope={}; native={}; samples=[]; build={}
    for binary in ['gts_profile','gts_rnum_reset']:
        build[binary]=json.loads((root/'logs'/(binary+'.build.json')).read_text())
        assert build[binary]['exit_code']==0
        variant='profile' if binary=='gts_profile' else 'rnum_reset'
        for f,h in build[binary]['source_sha256'].items():assert prepare.sha(root/'variants'/variant/f)==h,f
    qcount=0
    for label,r in all_runs.items():
        path=root/'runs'/label;case=r['case'];expected=manifest['cases'][case]['expected_counts']
        assert r['exit_code']==0 and r['stop_reason'] is None and not r['runtime_errors'] and r['post_gpu_clear'] and r['sanitizer_ok'],label
        assert r['validation']==prepare.validate((path/'cost.txt').read_text(),expected) and r['validation']['pass'],label
        assert r['binary_sha256']==build[r['binary_name']]['binary_sha256']
        assert r['manifest_sha256']==prepare.sha(root/'manifest.json')
        assert r['input_sha256']['data.txt']==manifest['data_sha256']
        assert r['input_sha256'][case+'.updates']==manifest['cases'][case]['updates_sha256']
        assert r['runner_sha256']==prepare.sha(root/'run_profile.py')
        for when in ['before','after']:
            state=json.loads((path/('gpu_'+when+'.json')).read_text())
            assert state['gpu'].split(',')[0].strip()=='2' and not state['apps'].strip()
        assert all(not x['foreign'] for x in json.loads((path/'admission_checks.json').read_text()))
        log=(path/'stderr.log').read_text();combined=log+(path/'stdout.log').read_text()
        if r['mode'] in ['memcheck','synccheck']:assert 'ERROR SUMMARY: 0 errors' in combined
        if r['binary_name']=='gts_profile':
            assert len(r['observed_flags'])==1 and r['observed_flags'][0]&7==(4 if r['blocking'] else 0)
            scope[label]=phases(log)
            assert scope[label]['operation.query']['count']==len(expected)
            assert scope[label]['build.total']['count']==(17 if case=='mixed16' else 1)
            if case=='mixed16':
                assert scope[label]['operation.rebuild']['count']==16
                assert scope[label]['operation.insert']['count']==176
                assert scope[label]['operation.delete']['count']==176
        qcount+=len(expected)
        m=re.search(r'Search time in update\s*:\s*([0-9.eE+-]+)',(path/'cost.txt').read_text())
        assert m; native[label]=float(m[1])*1000*len(expected)
        if label.startswith('timing_'):
            _,case,pair,policy=label.split('_')
            samples.append({'case':case,'pair':int(pair),'policy':policy,'native_query_total_ms_rounded':native[label],
                            'update_wall_ms':scope.get(label,{}).get('update.total',{}).get('wall_ms'),
                            'update_cpu_ms':scope.get(label,{}).get('update.total',{}).get('cpu_ms')})
    summary={}
    for case in ['query128','mixed16']:
        med={}; pairs=[]
        for policy in 'DB':
            labels=[f'timing_{case}_{i}_{policy}' for i in range(3)]
            med[policy]={name:{'count':scope[labels[0]][name]['count'],
                              'wall_ms':st.median(scope[x][name]['wall_ms'] for x in labels),
                              'cpu_ms':st.median(scope[x][name]['cpu_ms'] for x in labels)} for name in scope[labels[0]]}
        for i in range(3):
            d=scope[f'timing_{case}_{i}_D']['update.total'];b=scope[f'timing_{case}_{i}_B']['update.total']
            pairs.append({'pair':i,'D_wall_ms':d['wall_ms'],'B_wall_ms':b['wall_ms'],
                          'D_cpu_ms':d['cpu_ms'],'B_cpu_ms':b['cpu_ms'],
                          'cpu_reduction':1-b['cpu_ms']/d['cpu_ms'], 'B_over_D_wall':b['wall_ms']/d['wall_ms'],
                          'diagnostic_overhead_native_query_D_over_R':native[f'timing_{case}_{i}_D']/native[f'timing_{case}_{i}_R']})
        summary[case]={'median_stages':med,'pairs':pairs,
                       'median_pair_cpu_reduction':st.median(x['cpu_reduction'] for x in pairs),
                       'median_pair_B_over_D_wall':st.median(x['B_over_D_wall'] for x in pairs),
                       'median_pair_diagnostic_overhead':st.median(x['diagnostic_overhead_native_query_D_over_R'] for x in pairs)}
    traces={p.parent.name:trace(p) for p in sorted((root/'runs').glob('trace_*/trace.sqlite'))};assert len(traces)==4
    for label,t in traces.items():
        for name,r in t['ranges'].items():
            if name not in scope[label]:
                assert name.startswith(('thrust::','cub::')),name
                continue
            expected=scope[label][name]['count']-(1 if name=='build.total' else 2 if name=='build.sort' else 0)
            assert r['calls']==expected,(label,name,r['calls'],expected)
        required={name for name,v in scope[label].items() if name not in ['main.total','runtime.init','input.load','input.updates'] and v['count']-(1 if name=='build.total' else 2 if name=='build.sort' else 0)>0}
        assert required==set(t['ranges']) & set(scope[label]),label
        t['nvtx_counts_match_host_scopes']=True
        t['nvtx_warning_note']='Raw diagnostics contain a No NVTX events collected warning; actual exported NVTX rows exist and all selected instrumentation range counts match independent host scope counts; extra Thrust/CUB ranges are retained separately. Warning retained; cause not resolved. Scheduling/context-switch trace was disabled, so OS runtime thread-state estimates are not used.'
    for case in ['query128','mixed16']:
        a=traces['trace_'+case+'_0']['ranges']['update.total']['kernels']
        b=traces['trace_'+case+'_1']['ranges']['update.total']['kernels']
        assert {k:v['calls'] for k,v in a.items()}=={k:v['calls'] for k,v in b.items()}

    raw_hashes={str(p.relative_to(root)):prepare.sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
    record={'scope':'Synthetic repeated workflow attribution only. Three process comparisons per case, no confidence interval or broad performance claim.',
            'runs':len(all_runs),'validated_query_counts':qcount,'sanitizer_processes':sum(r['mode'] in ['memcheck','synccheck'] for r in all_runs.values()),
            'manifest':manifest,'environment':json.loads((root/'environment.json').read_text()),'summary':summary,'traces':traces,
            'instrumentation_manifest':json.loads((root/'variants/profile/VARIANT.json').read_text()),'raw_sha256':raw_hashes}
    out.mkdir(parents=True,exist_ok=False)
    (out/'EVIDENCE.json').write_text(json.dumps(record,indent=2)+'\n')
    with (out/'samples.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
    with (out/'stages.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['run','range','count','inclusive_wall_ms','inclusive_main_thread_cpu_ms'])
        for label,values in scope.items():
            if label.startswith('timing_'):
                for name,v in values.items():w.writerow([label,name,v['count'],v['wall_ms'],v['cpu_ms']])
    print(json.dumps({'runs':len(all_runs),'validated_queries':qcount,'summary':{k:{'default':v['median_stages']['D']['update.total'],'blocking':v['median_stages']['B']['update.total'],'cpu_reduction':v['median_pair_cpu_reduction'],'wall_ratio_B_over_D':v['median_pair_B_over_D_wall'],'overhead_D_over_R':v['median_pair_diagnostic_overhead']} for k,v in summary.items()}},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();analyze(a.root.resolve(),a.out.resolve())
