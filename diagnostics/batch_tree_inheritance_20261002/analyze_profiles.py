#!/usr/bin/env python3
"""Read query-only Nsight traces; profiler timings are diagnostic, not formal."""
import csv
import hashlib
from pathlib import Path
import sqlite3


ROOT=Path(__file__).resolve().parent
MODES=('SCAN_E','C_ID_E','C_MASK_E','C_TASK_E','C_MASK_L','C_TASK_L')
ORACLE=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/data/GIST/1000000/runs/batch_dev256_FR_half_20261001/result.csv')


def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def main():
    expected={int(r['qid']):(int(r['count']),int(r['ordered_hash'])) for r in rows(ORACLE)}
    output=[]
    for mode in MODES:
        folder=ROOT/'runs'/f'profile_half_b32_{mode}'
        got=rows(folder/'result_queries.csv')
        assert len(got)==32
        assert all((int(r['count']),int(r['ordered_hash']))==expected[int(r['qid'])]
                   for r in got),mode
        with sqlite3.connect(folder/'trace.sqlite') as conn:
            names=dict(conn.execute('SELECT id,value FROM StringIds'))
            kernel=list(conn.execute('SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL'))
            copy=list(conn.execute('SELECT start,end,bytes,copyKind FROM CUPTI_ACTIVITY_KIND_MEMCPY'))
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            memset=(list(conn.execute('SELECT start,end,bytes FROM CUPTI_ACTIVITY_KIND_MEMSET'))
                    if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables else [])
            runtime=list(conn.execute('SELECT start,end,nameId FROM CUPTI_ACTIVITY_KIND_RUNTIME'))
        totals={k:0.0 for k in ('tree_walk_ms','candidate_mask_ms','task_compact_ms',
                                'candidate_compact_ms','object_distance_ms','collect_ms')}
        for start,end,name_id in kernel:
            name=names[name_id]
            if name in ('roots','parent_walk'):stage='tree_walk_ms'
            elif name=='candidate_mask':stage='candidate_mask_ms'
            elif name in ('make_tile_masks','DeviceCompactInitKernel','DeviceSelectSweepKernel'):
                stage='candidate_compact_ms' if mode.startswith('C_ID') else 'task_compact_ms'
            elif name in ('batchDistance','id_distance','masked_distance','task_distance'):
                stage='object_distance_ms'
            elif name in ('batchBlockCount','DeviceScanInitKernel','DeviceScanKernel',
                          'batchOffsets','batchScatter'):stage='collect_ms'
            else:raise ValueError(name)
            totals[stage]+=(end-start)/1e6
        data_d2h=[(end-start)/1e6 for start,end,size,kind in copy if kind==2]
        data_bytes=[size for _,_,size,kind in copy if kind==2]
        assert len(data_d2h)==3 and len(data_bytes)==3
        sync=[(end-start)/1e6 for start,end,name_id in runtime
              if names[name_id].startswith('cudaStreamSynchronize')]
        assert len(sync)==2
        first=min([s for s,_,_ in kernel]+[s for s,_,_,_ in copy]+[s for s,_,_ in memset])
        last=max([e for _,e,_ in kernel]+[e for _,e,_,_ in copy]+[e for _,e,_ in memset])
        measured=rows(folder/'result.csv')
        assert len(measured)==1
        output.append({'mode':mode,'profiled_host_ready_ms':measured[0]['host_ms'],
            'profiled_gpu_ready_ms':measured[0]['gpu_ms'],
            'h2d_ms':sum((e-s)/1e6 for s,e,_,kind in copy if kind==1),
            'clear_ms':sum((e-s)/1e6 for s,e,_ in memset),**totals,
            'count_feedback_copy_ms':data_d2h[0],
            'result_d2h_ms':sum(data_d2h[1:]),
            'count_feedback_bytes':data_bytes[0],
            'result_d2h_bytes':sum(data_bytes[1:]),
            'first_sync_api_ms':sync[0], 'second_sync_api_ms':sync[1],
            'gpu_activity_span_ms':(last-first)/1e6,
            'kernel_count':len(kernel),'memcpy_count':len(copy),
            'trace_sha256':hashlib.sha256((folder/'trace.nsys-rep').read_bytes()).hexdigest(),
            'output_matches_old_strict':True})
    with (ROOT/'profile_summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(output[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(output)
    for row in output:print(row['mode'],row['profiled_host_ready_ms'],row['tree_walk_ms'],
                            row['object_distance_ms'],row['result_d2h_ms'])


if __name__=='__main__':main()
