#!/usr/bin/env python3
"""Validate and curate the three post-campaign, selected-query NCU diagnostics."""
import argparse
import csv
import json
from pathlib import Path
from profile_ncu import BINARY_SHA, SECTIONS, derive
from summarize import clean, read, sha

DETAILS = {'Grid Size','Block Size','# SMs','Registers Per Thread','Duration',
           'Compute (SM) Throughput','DRAM Throughput','Achieved Occupancy',
           'No Eligible','Eligible Warps Per Scheduler','Issued Warp Per Scheduler',
           'Avg. Active Threads Per Warp','Avg. Not Predicated Off Threads Per Warp',
           'Executed Instructions'}
RAW = ['profiler__replayer_passes','gpu__time_duration.sum',
       'device__attribute_multiprocessor_count','smsp__inst_executed.sum',
       'sm__throughput.avg.pct_of_peak_sustained_elapsed',
       'sm__warps_active.avg.pct_of_peak_sustained_active',
       'smsp__thread_inst_executed_per_inst_executed.ratio',
       'smsp__thread_inst_executed_pred_on_per_inst_executed.ratio',
       'smsp__warps_active.avg.per_cycle_active',
       'smsp__warps_eligible.avg.per_cycle_active',
       'smsp__average_warp_latency_per_inst_issued.ratio',
       'smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.ratio',
       'smsp__average_warps_issue_stalled_barrier_per_issue_active.ratio']


def summarize(primary, root, archive):
    ncu = root/'ncu'
    admission = read(primary/'logs/admission.json')
    assert admission['gpu_index'] == 1
    assert sha(primary/'bin/graph_bench') == BINARY_SHA
    assert (ncu/'run_ncu.py').read_text() == derive((primary/'run_ablation.py').read_text())
    assert (root/'profile_ncu.py').read_bytes() == Path(__file__).with_name('profile_ncu.py').read_bytes()
    expected = read(primary/'fixtures/expected_4.json')
    qids = (primary/'fixtures/queries.qid').read_text().split()
    assert qids.pop(0) == '64' and len(qids) == 64
    assert {p.name for p in (ncu/'runs').iterdir()} == {'ncu_'+m for m in 'DGQ'}
    result = {'experiment':'gts_20260923_traversal_ablation_words2000_ncu',
              'state':'diagnostic-only; same first query, 16-pass kernel replay, no clock/cache control',
              'scope':'D and Q profile two level kernels; G profiles the fused traversal including init/clear. Not public latency or a 64-query average.',
              'sections':SECTIONS,'order':['D','G','Q'], 'runs':{},
              'raw_archive_sha256':sha(archive),'raw_file_sha256':{}}
    for mode in 'DGQ':
        path=ncu/'runs'/('ncu_'+mode);r=read(path/'receipt.json');clean(r)
        kernel,count={'D':('findNextRnn',2),'G':('fusedTraversal',1),'Q':('dedupLevel',2)}[mode]
        assert r['tool']=='ncu' and r['mode']==mode and r['label']==path.name
        assert r['repeats']==1 and r['warmup']==0 and r['radius']==4 and not r['dump']
        assert r['binary_sha256']==BINARY_SHA and r['runner_sha256']==sha(ncu/'run_ncu.py')
        assert r['validation']['pass'] and r['validation']['rows']==64
        for phase in ['before','after']:
            s=read(path/(phase+'.json'));assert not s['apps'].strip()
            f=[x.strip() for x in s['gpu'].split(',')]
            assert f[:3]==['1',admission['gpu_uuid'],admission['gpu_name']]
        assert all(not x['foreign'] for x in read(path/'checks.json'))
        cmd=read(path/'command.json')
        prefix=['ncu','--kernel-name-base','demangled','--kernel-name','regex:'+kernel,
                '--launch-count',str(count),'--clock-control','none','--cache-control','none','--export']
        assert cmd[:len(prefix)]==prefix
        section_args=[arg for section in SECTIONS for arg in ['--section',section]]
        assert cmd[len(prefix)+1:len(prefix)+1+len(section_args)]==section_args
        rows=list(csv.DictReader((path/'result.csv').open()))
        assert [x['qid'] for x in rows]==qids
        assert all([int(x['count']),x['ordered_hash']]==expected[x['qid']] for x in rows)
        details=list(csv.DictReader((path/'metrics.csv').open()))
        raw=list(csv.reader((path/'metrics_raw.csv').open()))
        assert len(raw)==count+2
        units=dict(zip(raw[0],raw[1]));kernels=[]
        for i,row in enumerate(raw[2:]):
            v=dict(zip(raw[0],row));assert v['ID']==str(i) and kernel in v['Kernel Name']
            assert float(v['profiler__replayer_passes'])==16
            assert v['device__attribute_multiprocessor_count']=='188'
            d={x['Metric Name']:{'value':x['Metric Value'],'unit':x['Metric Unit']}
               for x in details if x['ID']==str(i) and x['Metric Name'] in DETAILS}
            assert set(d)==DETAILS
            assert d['Grid Size']['value']=='1' and d['Block Size']['value']=='512'
            kernels.append({'id':i,'kernel':v['Kernel Name'],'detail_metrics':d,
                            'raw_metrics':{k:{'value':v[k],'unit':units[k]} for k in RAW}})
        result['runs'][mode]={'binary_sha256':r['binary_sha256'],'runner_sha256':r['runner_sha256'],
                             'validation':r['validation'],'kernels':kernels}
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink():result['raw_file_sha256'][str(p.relative_to(root))]=sha(p)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['primary','root','archive','output']:p.add_argument(name,type=Path)
    a=p.parse_args();a.output.write_text(json.dumps(summarize(a.primary,a.root,a.archive),indent=2)+'\n')
    print('PASS three NCU runs, five selected launches, complete ordered outputs and GPU isolation')
