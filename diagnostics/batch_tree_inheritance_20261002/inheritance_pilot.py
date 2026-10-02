#!/usr/bin/env python3
"""Audit the Deep/Tloc development set and freeze one tree path per dataset."""
import csv
import filecmp
import json
from pathlib import Path
import struct
import subprocess
import sys


ROOT=Path(__file__).resolve().parent
OLD=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
P0=Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
CONFIG={
    'Deep': {'qid':P0/'fixtures/Deep_dev256.qid','radius':'0x3f8a3818','depth':1},
    'Tloc': {'qid':ROOT/'fixtures/Tloc_dev256.qid','radius':'0x4045b6eb','depth':4},
}
MODES=('SCAN_L','C_ID_L','C_MASK_L','C_TASK_L',
       'SCAN_E','C_ID_E','C_MASK_E','C_TASK_E')


def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def execute(label,cmd):
    out=ROOT/'runs'/label
    if not out.exists():
        subprocess.run([sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,
                        '--output',str(out),'--',*cmd],check=True,stdout=subprocess.DEVNULL)
    assert json.loads((out/'receipt.json').read_text())['runtime_valid'],label
    return out


def main(dataset):
    cfg=CONFIG[dataset]
    data=OLD/f'data/{dataset}/1000000/fixtures/data.f32bin'
    order=OLD/f'reference_v2/{dataset}_idlist.i32'
    index=OLD/f'replay/{dataset}_index.bin'
    radius=struct.unpack('<f',struct.pack('<I',int(cfg['radius'],16)))[0]
    reference=execute(f'oracle_{dataset.lower()}_dev256',[
        str(OLD/f'data/{dataset}/1000000/bin/graph_bench_strict'),str(data),
        str(cfg['qid']),'FR',repr(radius),'1','8',
        str(ROOT/'runs'/f'oracle_{dataset.lower()}_dev256'/'result'),'1'])
    expected=[(int(r['qid']),int(r['count']),int(r['ordered_hash']))
              for r in rows(reference/'result.csv')]
    assert len(expected)==256
    totals={}
    for mode in MODES:
        label=f'pilot_{dataset.lower()}_dev256_b32_{mode}'
        out=execute(label,[str(ROOT/'bin/p4_bench_v3'),str(data),str(order),
            str(cfg['qid']),str(cfg['qid']),mode,cfg['radius'],'32','2','0',
            str(ROOT/'runs'/label/'result'),'1',str(index),str(cfg['depth'])])
        got=rows(out/'result_queries.csv')
        got.sort(key=lambda r:int(r['query_index']))
        assert [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
                for r in got]==expected,label
        assert filecmp.cmp(out/'result.bin',reference/'result.bin',shallow=False),label
        (out/'result.bin').unlink()
        totals[mode]=sum(float(r['host_ms']) for r in rows(out/'result.csv'))
        print('PILOT PASS',dataset,mode,round(totals[mode],3),flush=True)
    scores={path:totals[path+'_L']+totals[path+'_E']
            for path in ('C_ID','C_MASK','C_TASK')}
    selected=min(scores,key=scores.get)
    summary={'dataset':dataset,'development_queries':256,'B':32,'radius_bits':cfg['radius'],
             'depth':cfg['depth'],'criterion':'minimize L+E host-ready total on dev256',
             'scores_ms':scores,'totals_ms':totals,'selected_path':selected,
             'all_modes_full_output_equal_old_strict':True}
    (ROOT/f'pilot_{dataset.lower()}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('SELECTED',dataset,selected,flush=True)


if __name__=='__main__':main(sys.argv[1])
