#!/usr/bin/env python3
"""Exactly two seen-development passes per native budget, no final tuning."""
import argparse
import json
from pathlib import Path
from native_knn import Backend
from qualification import BASE,native_ivf

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--family',choices=('IVF','CAGRA'),required=True)
    p.add_argument('--data-root',type=Path,required=True);a=p.parse_args()
    source=native_ivf.load_data(a.data_root/f'{a.dataset}/1000000/fixtures/data.f32bin')
    qids=native_ivf.read_qids(BASE/f'fixtures/{a.dataset}_dev128.qid')
    reference=json.loads((BASE/f'oracle_{a.dataset}_dev128.json').read_text());assert qids.tolist()==[r['qid'] for r in reference['records']]
    dest=ROOT/'development';dest.mkdir(exist_ok=True);rows=[]
    for nlist in ((1024,4096) if a.family=='IVF' else (0,)):
        backend=Backend(source,'IVF_APPROX' if a.family=='IVF' else 'CAGRA',nlist)
        configs=[{'nlist':nlist,'nprobe':n} for n in (16,64,128,256,512,1024,2048) if n<=min(nlist,2048)] if a.family=='IVF' else [
            {'itopk_size':t,'search_width':w} for t in (64,128,256,512,1024) for w in (1,2,4)]
        shapes=[(k,b) for k in (8,32) for b in (1,32)]
        for repeat in (1,2):
            items=[(k,b,c) for k,b in shapes for c in configs]
            if repeat==2:items=items[::-1]
            for k,b,c in items:
                suffix=f'n{nlist}p{c["nprobe"]}' if a.family=='IVF' else f't{c["itopk_size"]}w{c["search_width"]}'
                label=f'dev_{a.dataset}_{a.family}_{suffix}_k{k}_b{b}_r{repeat}'
                row=backend.measure(qids,qids,k,b,c,dest/label,reference)
                row.update(dataset=a.dataset,family=a.family,repeat=repeat,config=c,label=label)
                rows.append(row)
                (ROOT/f'DEV_{a.dataset}_{a.family}.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(f'{label}: {row["pass_ms"]:.3f} ms recall={row["quality"]["recall_tie_aware"]:.9f}',flush=True)
        del backend
    print(f'DEVELOPMENT COMPLETE {a.dataset} {a.family} {len(rows)}',flush=True)

if __name__=='__main__':main()
