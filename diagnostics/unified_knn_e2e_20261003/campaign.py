#!/usr/bin/env python3
"""Registered fresh-process timing and quality, preserving every failure."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from qualification import BASE,native_ivf,check_output

ROOT=Path(__file__).resolve().parent
ORDERS=[['GTS_ORIG','O_FULL','IVF_ALL','O_BOUND','FAISS_FLAT','O_MASK'],
        ['O_FULL','O_BOUND','GTS_ORIG','O_MASK','IVF_ALL','FAISS_FLAT'],
        ['O_BOUND','O_MASK','O_FULL','FAISS_FLAT','GTS_ORIG','IVF_ALL'],
        ['IVF_ALL','GTS_ORIG','FAISS_FLAT','O_FULL','O_MASK','O_BOUND'],
        ['FAISS_FLAT','IVF_ALL','O_MASK','GTS_ORIG','O_BOUND','O_FULL'],
        ['O_MASK','FAISS_FLAT','O_BOUND','IVF_ALL','O_FULL','GTS_ORIG']]

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def command(a,dataset,method,k,b,qids,out,config):
    data=a.data_root/f'{dataset}/1000000/fixtures/data.f32bin';warm=BASE/f'fixtures/{dataset}_dev128.qid'
    if method.startswith('O_'):
        return [ROOT/'opt_knn_bench',data,qids,BASE/f'{dataset}.index',ROOT/'fixtures/seeds_1000000.i32',method,k,b,out,warm,0]
    if method=='GTS_ORIG':return [ROOT/'gts_bench_p7',data,qids,k,b,1,BASE/f'{dataset}.index',out,2,warm]
    python=a.cuvs_python if method=='CAGRA' else a.faiss_python
    cmd=[python,ROOT/'native_knn.py','--data',data,'--method',method,'--qids',qids,'--warm',warm,'--k',k,'--b',b,'--out',out]
    if 'nlist' in config:cmd+=['--nlist',config['nlist'],'--nprobe',config['nprobe']]
    if 'itopk_size' in config:cmd+=['--itopk',config['itopk_size'],'--width',config['search_width']]
    return cmd

def run(a,label,cmd):
    admission=ROOT/'runs'/label
    if admission.exists():raise RuntimeError(f'Existing run: {label}')
    args=[sys.executable,ROOT/'run_locked.py','--gpu',a.gpu,'--output',admission,'--',*cmd]
    completed=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if completed.returncode:
        print(completed.stdout,flush=True)
        raise RuntimeError(f'Failed runtime: {label}; see retained admission stderr')
    return json.loads((admission/'receipt.json').read_text())

def collect(a,row,qids,reference):
    dataset,method,k,b=row['dataset'],row['method'],row['K'],row['B']
    label=row['label'];out=ROOT/'outputs'/label
    receipt=run(a,label,command(a,dataset,method,k,b,qids,out,row['config']))
    if method=='GTS_ORIG':
        values=list(csv.DictReader(Path(str(out)+'.csv').open()));assert len(values)==1
        meta={'pass_ms':float(values[0]['total_ms']),'batch_p50_ms':float(values[0]['batch_p50_ms']),
              'batch_p95_ms':float(values[0]['batch_p95_ms'])}
        lines=(ROOT/'runs'/label/'stdout.log').read_text().splitlines()
        meta['setup']=json.loads(next(s.removeprefix('RESULT ') for s in lines if s.startswith('RESULT ')))
    else:meta=json.loads(Path(str(out)+'.json').read_text())
    data=native_ivf.load_data(a.data_root/f'{dataset}/1000000/fixtures/data.f32bin')
    q=check_output(str(out)+'.bin',data,reference,k,exact=method.startswith('O_'))
    row.update(meta);row['quality']=q
    row['receipt']={k:receipt[k] for k in ('binary_sha256','exit_code','stop_reason','wall_s','runtime_valid')}
    row['result_sha256']=hashlib.sha256(Path(str(out)+'.bin').read_bytes()).hexdigest()
    save(Path(str(out)+'.audit.json'),row)
    print(f"{label}: {row['pass_ms']:.3f} ms recall={q['recall_tie_aware']:.9f} min={q['minimum_query_recall']:.6f} gate={q['complete_gate_pass']}",flush=True)
    return row

def pilot(a):
    ref=json.loads((BASE/'oracle_GIST_final256.json').read_text());ref['records']=ref['records'][:32];ref['Q']=32
    qs=ROOT/'fixtures/GIST_pilot32.qid';qs.write_text('32\n'+''.join(f'{r["qid"]}\n' for r in ref['records']))
    save(ROOT/'oracle_GIST_pilot32.json',ref)
    methods=['GTS_ORIG','O_FULL','IVF_ALL','O_BOUND','FAISS_FLAT','O_MASK','CAGRA']
    rows=[];schedule=[]
    for round_no in range(1,4):
        order=methods[round_no-1:]+methods[:round_no-1]
        if round_no==2:order=order[::-1]
        for pos,m in enumerate(order):
            config={'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {'itopk_size':1024,'search_width':4} if m=='CAGRA' else {}
            schedule.append({'label':f'{a.tag}_r{round_no}_{m}','dataset':'GIST','K':8,'B':32,'method':m,'round':round_no,'position':pos,'config':config})
    save(ROOT/'PILOT_SCHEDULE.json',schedule)
    for row in schedule:
        rows.append(collect(a,row,qs,ref));save(ROOT/'PILOT.json',rows)
    print('PILOT COMPLETE 21/21',flush=True)

def formal(a):
    frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text());schedule=[]
    for name,digest in frozen['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    for round_no in range(1,7):
        shapes=[(d,k,b) for d in ('GIST','Deep') for k in (8,32) for b in (1,32)]
        shapes=shapes[round_no-1:]+shapes[:round_no-1]
        for dataset,k,b in shapes:
            shape=f'{dataset}_k{k}_b{b}';ann=frozen['selected'][shape]
            ann_items=list({c['label']:c for c in ann if c['method']!='IVF_ALL'}.values())
            # ANN orders are a predeclared forward/reverse cycle, independent
            # of measured speed. Insert among complete modes without changing
            # their registered relative order.
            shift=(round_no-1)//2%max(1,len(ann_items));ann_items=ann_items[shift:]+ann_items[:shift]
            if round_no%2==0:ann_items=ann_items[::-1]
            order=[]
            for i,m in enumerate(ORDERS[round_no-1]):
                order.append({'label':m,'method':m,'config':{'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {}})
                if i<len(ann_items):order.append(ann_items[i])
            order.extend(ann_items[6:])
            for pos,item in enumerate(order):
                schedule.append({'label':f'formal_r{round_no}_{shape}_{item["label"]}','dataset':dataset,'K':k,'B':b,'method':item['method'],
                                 'round':round_no,'position':pos,'config':item['config'],'variant':item['label'],'anchors':item.get('anchors',[])})
    save(ROOT/'FORMAL_SCHEDULE.json',schedule)
    rows=[]
    for row in schedule:
        dataset=row['dataset'];reference=json.loads((ROOT/f'oracle_{dataset}_final256.json').read_text())
        rows.append(collect(a,row,ROOT/f'fixtures/{dataset}_final256.qid',reference));save(ROOT/'FORMAL.json',rows)
    print(f'FORMAL COMPLETE {len(rows)}/{len(schedule)}',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('pilot','formal'))
    p.add_argument('--gpu',required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True)
    p.add_argument('--tag',default='pilot')
    a=p.parse_args();(ROOT/'runs').mkdir(exist_ok=True);(ROOT/'outputs').mkdir(exist_ok=True)
    globals()[a.phase](a)

if __name__=='__main__':main()
