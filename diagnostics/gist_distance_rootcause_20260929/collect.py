#!/usr/bin/env python3
"""Export checked run data and compact summaries from the frozen campaign."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

TOP=Path('/home/data/wangxuran/tmp/gts_gist_rootcause_20260929')
ROOT=TOP/'data/GIST/1000000'
OLD=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
RADII=('normal','half','all')
MODES=('B','L','E64','L_E64')


def read(label,name='result.csv'):
    with (ROOT/'runs'/label/name).open() as f:return list(csv.DictReader(f))


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
    return h.hexdigest()


def write_csv(name,rows):
    assert rows
    with (TOP/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def quantile(hist,p):
    target=p*sum(hist);total=0
    for i,n in enumerate(hist):
        total+=n
        if total>=target:return i*32
    raise AssertionError


def main():
    timings=[];setups=[];work=[];manifest={}
    for kind in RADII:
        reference=None
        for mode in MODES:
            label=f'audit_{kind}_{mode}'
            run=ROOT/'runs'/label
            audit=json.loads((run/'audit.json').read_text())
            assert audit['pass'] and len(audit['queries'])==64
            digest=sha(run/'result.bin')
            if reference is None:reference=digest
            assert digest==reference
            manifest[label]={'receipt_sha256':sha(run/'receipt.json'),
                             'ordered_result_sha256':digest,
                             'audit_sha256':sha(run/'audit.json')}
            audit_rows=read(label)
            for round_no in range(1,7):
                label=f'time_{kind}_r{round_no}_{mode}'
                run=ROOT/'runs'/label
                rec=json.loads((run/'receipt.json').read_text())
                assert rec['exit_code']==0 and rec['post_gpu_clear'] and not rec['runtime_errors']
                rows=read(label)
                assert [(r['qid'],r['count'],r['ordered_hash']) for r in rows]==[
                    (r['qid'],r['count'],r['ordered_hash']) for r in audit_rows]
                manifest[label]={'receipt_sha256':sha(run/'receipt.json'),
                                 'result_csv_sha256':sha(run/'result.csv')}
                setup=json.loads((run/'result.json').read_text())
                with (run/'gpu.csv').open() as f:
                    sampled_mib=max(float(row[1].strip().split()[0]) for row in csv.reader(f)
                                    if len(row)>1 and row[1].strip())
                setups.append({'radius':kind,'mode':mode,'round':round_no,
                               'layout_s':setup['layout_s'],
                               'layout_bytes':setup['layout_bytes'],
                               'sampled_peak_gpu_mib':sampled_mib,
                               'first_query_s':setup['first_query_s'],
                               'process_until_cleanup_s':setup['before_cleanup_process_s']})
                for row in rows:
                    timings.append({'radius':kind,'mode':mode,'round':round_no,
                                    'query_id':row['qid'],'count':row['count'],
                                    'ordered_hash':row['ordered_hash'],
                                    'host_ready_ms':float(row['query_us'])/1000})
            label=f'count_{kind}_{mode}'
            dim_rows=read(label,'dims.csv')
            manifest[label]={'receipt_sha256':sha(ROOT/'runs'/label/'receipt.json'),
                             'dims_csv_sha256':sha(ROOT/'runs'/label/'dims.csv')}
            assert len(dim_rows)==64
            for row,expected in zip(dim_rows,audit_rows):
                assert (row['qid'],row['count'],row['ordered_hash'])==(
                    expected['qid'],expected['count'],expected['ordered_hash'])
                hist=list(map(int,row['dim_hist'].split('|')))
                groups=list(map(int,row['group_max_hist'].split('|')))
                assert sum(hist)==1000000 and sum(groups)==31250
                assert len(hist)==len(groups)==31
                total=int(row['sum_dims'])
                assert total==sum(i*32*n for i,n in enumerate(hist))
                work.append({'radius':kind,'mode':mode,'query_id':row['qid'],
                             'count':row['count'],'ordered_hash':row['ordered_hash'],
                             'objects':1000000,'sum_dims':total,'mean_dims':total/1e6,
                             'p50_dims':quantile(hist,.5),'p90_dims':quantile(hist,.9),
                             'p99_dims':quantile(hist,.99),
                             'mean_group_max_dims':sum(i*32*n for i,n in enumerate(groups))/31250,
                             'full_dim_fraction':hist[30]/1e6,
                             'full_group_fraction':groups[30]/31250,
                             'logical_object_coord_read_gb':total*4/1e9})
            label=f'profile_{kind}_{mode}'
            manifest[label]={'receipt_sha256':sha(ROOT/'runs'/label/'receipt.json'),
                             'trace_sqlite_sha256':sha(ROOT/'runs'/label/'trace.sqlite')}
    assert len(timings)==3*4*6*64 and len(work)==3*4*64
    write_csv('latency.csv',timings);write_csv('setup.csv',setups);write_csv('work.csv',work)
    profiles=list(csv.DictReader((TOP/'profile_summary.csv').open()))
    assert len(profiles)==3*4*64
    summary={}
    for kind in RADII:
        summary[kind]={}
        baseline={rnd:statistics.mean(float(r['host_ready_ms']) for r in timings
                                   if r['radius']==kind and r['mode']=='B' and r['round']==rnd)
                  for rnd in range(1,7)}
        for mode in MODES:
            selected=[r for r in timings if r['radius']==kind and r['mode']==mode]
            means=[statistics.mean(float(r['host_ready_ms']) for r in selected if r['round']==rnd)
                   for rnd in range(1,7)]
            ratio=[baseline[rnd]/means[rnd-1] for rnd in range(1,7)]
            p=[r for r in profiles if r['radius']==kind and r['mode']==mode]
            w=[r for r in work if r['radius']==kind and r['mode']==mode]
            s=[r for r in setups if r['radius']==kind and r['mode']==mode]
            summary[kind][mode]={
                'round_mean_host_ms':means,'round_speedup_vs_B':ratio,
                'host_ms_mean':statistics.mean(means),
                'speedup_median':statistics.median(ratio),
                'speedup_range':[min(ratio),max(ratio)],
                'profile_object_ms_mean':statistics.mean(float(x['object_distance_ms']) for x in p),
                'profile_select_ms_mean':statistics.mean(float(x['result_select_ms']) for x in p),
                'profile_scan_ms_mean':statistics.mean(float(x['result_scan_ms']) for x in p),
                'profile_d2h_ms_mean':statistics.mean(float(x['d2h_ms']) for x in p),
                'mean_dims':statistics.mean(float(x['mean_dims']) for x in w),
                'mean_group_max_dims':statistics.mean(float(x['mean_group_max_dims']) for x in w),
                'layout_s_median':statistics.median(float(x['layout_s']) for x in s),
                'sampled_peak_gpu_mib_median':statistics.median(float(x['sampled_peak_gpu_mib']) for x in s),
                'layout_bytes':int(s[0]['layout_bytes'])}
    (TOP/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    evidence={'baseline_commit':'86fa5199b3e9cf90413c39371cd49a97d355c56f',
              'gpu_uuid':'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603',
              'data_sha256':sha(ROOT/'fixtures/data.f32bin'),
              'query_file_sha256':sha(ROOT/'fixtures/final_v3.qid'),
              'oracle_sha256':sha(OLD/'reference_v3/GIST_final.sq64'),
              'idlist_sha256':sha(OLD/'reference_v2/GIST_idlist.i32'),
              'main_binary_sha256':sha(ROOT/'bin/graph_bench_rootcause'),
              'count_binary_sha256':sha(ROOT/'bin/graph_bench_count'),
              'profile_binary_sha256':sha(ROOT/'bin/graph_bench_profile'),
              'small_validator_binary_sha256':sha(TOP/'small_validate'),
              'sanitizer_logs_sha256':{name:sha(TOP/name) for name in
                                        ('small_memcheck.log','small_synccheck.log')},
              'ncu_archive_sha256':sha(TOP/'ncu_reports.tar.gz'),
              'sass_archive_sha256':sha(TOP/'sass.txt.gz'),
              'source_sha256':{name:sha(TOP/name) for name in (
                  'rootcause_l2.cuh','graph_bench_main.cu',
                  'graph_bench_count.cu','graph_bench_profile.cu',
                  'small_validate.cu','run.py','run_profile.py',
                  'campaign.py','followup.py','analyze_profile.py','collect.py')},
              'ncu_settings':{'clock_control':'none','cache_control':'none',
                              'replay_mode':'kernel','launch_skip':9,
                              'launch_count':1,'query_selection':'development count P10/P50/P90'},
              'runs':manifest}
    old_labels={'normal':'finalcheck_GIST_FR',
                'half':'finalcheck_v3_half_GIST_FR',
                'all':'finalcheck_v3_all_GIST_FR'}
    evidence['old_F_ref_ordered_result_sha256']={}
    for kind,label in old_labels.items():
        digest=sha(OLD/'data/GIST/1000000/runs'/label/'result.bin')
        assert digest==manifest[f'audit_{kind}_B']['ordered_result_sha256']
        evidence['old_F_ref_ordered_result_sha256'][kind]=digest
    (TOP/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
