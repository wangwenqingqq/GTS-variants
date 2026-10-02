#!/usr/bin/env python3
"""Extract cold setup and observed GPU memory from frozen formal receipts."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
setup=[];memory=[]
for folder in sorted((ROOT/'runs').glob('formal_p5_r1_*')):
    meta=json.loads((folder/'result.json').read_text())
    receipt=json.loads((folder/'receipt.json').read_text())
    assert receipt['runtime_valid']
    mode=meta['mode']
    dataset='Deep' if 'deep' in folder.name else 'GIST'
    radius='half' if '_half_' in folder.name else 'all' if '_all_' in folder.name else 'normal'
    b=int(meta['batch'])
    setup.append((dataset,radius,b,mode,meta.get('data_setup_s'),
                  meta.get('layout_s'),meta.get('ordered_layout_s'),
                  meta.get('index_refit_s'),meta.get('index_bytes'),
                  meta.get('layout_bytes',meta.get('ordered_layout_bytes')),
                  meta.get('squared_workspace_bytes'),meta.get('scan_temp_bytes'),
                  meta.get('graph'),meta.get('chunk_n')))
    readings=[]
    with (folder/'gpu.csv').open() as f:
        for row in csv.reader(f):
            try:readings.append(int(row[1]))
            except (ValueError,IndexError):pass
    assert readings
    memory.append((dataset,radius,b,mode,max(readings),min(readings),
                   receipt['wall_s'],receipt['binary_sha256']))
assert len(set((a,b,c,d) for a,b,c,d,*_ in setup))==48
with (ROOT/'setup.csv').open('w') as f:
    w=csv.writer(f);w.writerow(('dataset','radius','B','mode','data_setup_s',
        'aosoa_layout_s','ordered_layout_s','index_refit_s','index_bytes',
        'layout_bytes','squared_workspace_bytes','scan_temp_bytes','graph','chunk_n'))
    w.writerows(setup)
with (ROOT/'memory.csv').open('w') as f:
    w=csv.writer(f);w.writerow(('dataset','radius','B','mode','gpu_peak_used_mib',
        'gpu_min_used_mib','process_wall_s','binary_sha256'))
    w.writerows(memory)
print('PASS',len(setup),'round-1 conditions')
