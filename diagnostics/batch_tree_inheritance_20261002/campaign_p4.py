#!/usr/bin/env python3
"""Audit and rotate the GIST-half development pilot on the frozen P4 binary."""
import argparse
import csv
import filecmp
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
MODES=('SCAN_E','C_ID_E','C_MASK_E','C_TASK_E','SCAN_L')


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('audit','pilot'))
    p.add_argument('--binary',type=Path,default=ROOT/'bin/p4_bench_v2')
    for key in ('data','idlist','index','qid','oracle_bin','oracle_csv'):
        p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    expected=[(int(r['qid']),int(r['count']),int(r['ordered_hash']))
              for r in rows(a.oracle_csv)]
    assert len(expected)==256
    oracle_hash=hashlib.sha256(a.oracle_bin.read_bytes()).hexdigest()
    summary=[]
    for round_no in ((0,) if a.phase=='audit' else (1,2,3)):
        sizes=(8,32) if round_no%2==0 else (32,8)
        for batch in sizes:
            modes=MODES if round_no==0 else MODES[(round_no-1)%5:]+MODES[:(round_no-1)%5]
            for mode in modes:
                label=f'{a.phase}_gist_half_r{round_no}_b{batch}_{mode}'
                out=ROOT/'runs'/label
                cmd=[sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,'--output',str(out),'--',
                     str(a.binary),str(a.data),str(a.idlist),str(a.qid),str(a.qid),
                     mode,'0x3f34a3d8',str(batch),'2',str(int(round_no%2==0 and round_no>0)),
                     str(out/'result'),str(int(a.phase=='audit')),str(a.index),'4']
                subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
                receipt=json.loads((out/'receipt.json').read_text())
                assert receipt['runtime_valid']
                got=rows(out/'result_queries.csv')
                got.sort(key=lambda r:int(r['query_index']))
                assert [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
                        for r in got]==expected,label
                batches=rows(out/'result.csv')
                assert len(batches)==256//batch
                if a.phase=='audit':
                    assert filecmp.cmp(out/'result.bin',a.oracle_bin,shallow=False),label
                    (out/'output.sha256').write_text(oracle_hash+'\n')
                    (out/'result.bin').unlink()
                total=sum(float(r['host_ms']) for r in batches)
                gpu=sum(float(r['gpu_ms']) for r in batches)
                summary.append((a.phase,round_no,batch,mode,total,gpu))
                print('PASS',round_no,batch,mode,round(total,3),flush=True)
    with (ROOT/f'{a.phase}_gist_half_dev256.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('phase','round','B','mode','host_total_ms','gpu_total_ms'))
        w.writerows(summary)


if __name__=='__main__':main()
