#!/usr/bin/env python3
"""Run the frozen Deep/Tloc inheritance audits and paired formal rounds."""
import csv
import filecmp
import json
from pathlib import Path
import struct
import sys

from inheritance_pilot import ROOT,OLD,CONFIG,execute,rows


def main(dataset,phase):
    assert phase in ('audit','formal')
    cfg=CONFIG[dataset]
    selected=json.loads((ROOT/f'pilot_{dataset.lower()}_summary.json').read_text())['selected_path']
    modes=('SCAN_L',selected+'_L','SCAN_E',selected+'_E')
    sizes=(32,) if dataset=='Deep' else (1,32)
    qid=ROOT/'fixtures'/f'{dataset}_final1024.qid'
    data=OLD/f'data/{dataset}/1000000/fixtures/data.f32bin'
    order=OLD/f'reference_v2/{dataset}_idlist.i32'
    index=OLD/f'replay/{dataset}_index.bin'
    radius=struct.unpack('<f',struct.pack('<I',int(cfg['radius'],16)))[0]
    reference=execute(f'oracle_{dataset.lower()}_final1024',[
        str(OLD/f'data/{dataset}/1000000/bin/graph_bench_strict'),str(data),
        str(qid),'FR',repr(radius),'1','8',
        str(ROOT/'runs'/f'oracle_{dataset.lower()}_final1024'/'result'),'1'])
    expected=[(int(r['qid']),int(r['count']),int(r['ordered_hash']))
              for r in rows(reference/'result.csv')]
    assert len(expected)==1024
    rounds=(0,) if phase=='audit' else range(1,7)
    for round_no in rounds:
        batches=sizes[round_no%len(sizes):]+sizes[:round_no%len(sizes)]
        order_modes=modes[round_no%len(modes):]+modes[:round_no%len(modes)]
        for batch in batches:
            for mode in order_modes:
                label=f'final_{phase}_{dataset.lower()}_r{round_no}_b{batch}_{mode}'
                out=execute(label,[str(ROOT/'bin/p4_bench_v3'),str(data),str(order),
                    str(qid),str(cfg['qid']),mode,cfg['radius'],str(batch),'2',
                    str(int(round_no%2==0 and round_no>0)),str(ROOT/'runs'/label/'result'),
                    str(int(phase=='audit')),str(index),str(cfg['depth'])])
                got=rows(out/'result_queries.csv')
                got.sort(key=lambda r:int(r['query_index']))
                assert [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
                        for r in got]==expected,label
                batches_csv=rows(out/'result.csv')
                assert len(batches_csv)==1024//batch
                for r in batches_csv:
                    i=int(r['batch_id'])
                    count=sum(x[1] for x in expected[i*batch:(i+1)*batch])
                    assert int(r['result_count_total'])==count
                    assert int(r['d2h_bytes'])==(batch+1)*8+count*8
                if phase=='audit':
                    assert filecmp.cmp(out/'result.bin',reference/'result.bin',shallow=False),label
                    (out/'result.bin').unlink()
                total=sum(float(r['host_ms']) for r in batches_csv)
                print('PASS',phase,dataset,round_no,batch,mode,round(total,3),flush=True)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
