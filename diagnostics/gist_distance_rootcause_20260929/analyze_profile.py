#!/usr/bin/env python3
"""Check fixed query-only traces and export per-query stage durations."""
import csv
import json
from pathlib import Path
import sqlite3

ROOT = Path('/home/data/wangxuran/tmp/gts_gist_rootcause_20260929/data/GIST/1000000')


def main():
    output = []
    for radius in ('normal', 'half', 'all'):
        for mode in ('B', 'L', 'E64', 'L_E64'):
            run = ROOT / 'runs' / f'profile_{radius}_{mode}'
            receipt = json.loads((run / 'receipt.json').read_text())
            assert receipt['exit_code'] == 0 and receipt['post_gpu_clear']
            actual = list(csv.DictReader((run / 'result.csv').open()))
            expected = list(csv.DictReader((ROOT / 'runs' / f'audit_{radius}_{mode}' / 'result.csv').open()))
            assert len(actual) == len(expected) == 64
            assert [(r['qid'],r['count'],r['ordered_hash']) for r in actual] == [
                (r['qid'],r['count'],r['ordered_hash']) for r in expected]
            with sqlite3.connect(run / 'trace.sqlite') as db:
                names = dict(db.execute('SELECT id,value FROM StringIds'))
                kernels = list(db.execute('SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL ORDER BY start'))
                copies = list(db.execute('SELECT start,end,bytes,copyKind FROM CUPTI_ACTIVITY_KIND_MEMCPY ORDER BY start'))
            assert len(kernels) == len(copies) == 64*4
            for i, row in enumerate(actual):
                ks = kernels[i*4:(i+1)*4]
                cs = copies[i*4:(i+1)*4]
                stages = [names[x[2]].split('(')[0] for x in ks]
                assert stages[0] == 'rootcauseFlat' and stages[1] == 'DeviceScanInitKernel'
                assert stages[2] == 'DeviceScanKernel' and stages[3] == 'flatResultSelect'
                ms = [(e-s)/1e6 for s,e,_ in ks]
                d2h = sum((e-s)/1e6 for s,e,_,kind in cs if kind==2)
                d2h_bytes = sum(size for _,_,size,kind in cs if kind==2)
                assert d2h_bytes == 17777764
                output.append({'radius':radius,'mode':mode,'query_id':row['qid'],
                               'result_count':row['count'],
                               'profiled_host_ready_ms':float(row['query_us'])/1000,
                               'object_distance_ms':ms[0], 'result_scan_ms':ms[1]+ms[2],
                               'result_select_ms':ms[3], 'd2h_ms':d2h,
                               'd2h_bytes':d2h_bytes})
    with (ROOT.parent.parent.parent / 'profile_summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
    print('validated',len(output),'query traces')


if __name__ == '__main__':
    main()
