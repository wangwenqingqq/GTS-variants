#!/usr/bin/env python3
"""Serialize the registered qualification, development and formal campaign."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('qualify','development','formal'))
    p.add_argument('--python',required=True)
    p.add_argument('--data-root',required=True,type=Path)
    p.add_argument('--gpu',required=True)
    a=p.parse_args();os.chdir(ROOT)
    contract=json.loads((ROOT/'CONTRACT.json').read_text())
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in ROOT.iterdir() if p.suffix in ('.py','.cu') or p.name=='gts_bench'}
    (ROOT/f'SOURCE_HASHES_{a.phase}.json').write_text(json.dumps(source_hashes,indent=2)+'\n')

    def run(label,cmd):
        folder=ROOT/'runs'/label
        if not folder.exists():
            subprocess.run([sys.executable,str(ROOT/'run_locked.py'),'--gpu',a.gpu,
                            '--output',str(folder),'--',*map(str,cmd)],check=True)
        receipt=json.loads((folder/'receipt.json').read_text())
        assert receipt['runtime_valid'] and receipt['command'][3:]==list(map(str,cmd)),label
        print('PASS',label,flush=True)

    def oracle(data,qids,out,label):
        run(label,[a.python,ROOT/'native_ivf.py','oracle','--data',data,'--qids',qids,'--out',out])

    def gts(data,qids,k,b,repeats,cache,out,label,sanitizer=None):
        cmd=[ROOT/'gts_bench',data,qids,k,b,repeats,cache,out,2]
        if sanitizer:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','91',*cmd]
        run(label,cmd)

    def check_gts(data,reference,out):
        target=ROOT/f'{out}.quality.json'
        subprocess.run([a.python,ROOT/'native_ivf.py','check-gts','--data',str(data),
                        '--reference',str(reference),'--result',str(ROOT/f'{out}.bin'),
                        '--out',str(target)],check=True,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu})
        quality=json.loads(target.read_text())
        assert quality['distance_tolerance_pass'],target
        return quality

    if a.phase=='qualify':
        records=[]
        for d in (96,960):
            data=ROOT/f'synthetic_{d}.f32bin';qids=ROOT/'fixtures/synthetic_ragged33.qid'
            reference=ROOT/f'oracle_synthetic{d}.json'
            if not reference.exists():oracle(data,qids,reference,f'oracle_synthetic{d}_registered')
            for k in (8,32):
                for b in (1,32):
                    label=f'qual_gts_d{d}_k{k}_b{b}'
                    gts(data,qids,k,b,8,ROOT/f'synthetic{d}.index',label,label)
                    quality=check_gts(data,reference,label)
                    assert quality['recall_tie_aware']==1, (label,quality)
                    records.append({'label':label,**quality})
            label=f'qual_ivf_d{d}'
            run(label,[a.python,ROOT/'native_ivf.py','faiss','--data',data,'--qids',qids,
                       '--reference',reference,'--configs',ROOT/'synthetic_configs.json',
                       '--repeats',2,'--out',ROOT/f'{label}.json'])
            result=json.loads((ROOT/f'{label}.json').read_text())
            for row in result['rows']:
                assert row['quality']['recall_tie_aware']==1 and row['quality']['distance_tolerance_pass'],row
            for tool in ('memcheck','synccheck'):
                label=f'qual_{tool}_d{d}'
                gts(data,qids,32,32,2,ROOT/f'synthetic{d}.index',label,label,tool)
                log=(ROOT/'runs'/label/'stdout.log').read_text()+(ROOT/'runs'/label/'stderr.log').read_text()
                assert 'ERROR SUMMARY: 0 errors' in log,label
        (ROOT/'QUALIFICATION.json').write_text(json.dumps({'status':'passed','records':records,
            'scope':'N4097, D96/960, 33 ragged queries, K8/32, B1/32, duplicate vectors/ties, repeated calls, memcheck and synccheck'},indent=2)+'\n')
        return

    assert json.loads((ROOT/'QUALIFICATION.json').read_text())['status']=='passed'
    for dataset in (('GIST','Deep') if a.phase=='development' else ('GIST','Deep')):
        data=a.data_root/dataset/'1000000/fixtures/data.f32bin'
        phase='dev128' if a.phase=='development' else 'final256'
        qids=ROOT/'fixtures'/f'{dataset}_{phase}.qid'
        reference=ROOT/f'oracle_{dataset}_{phase}.json'
        if not reference.exists():oracle(data,qids,reference,f'oracle_{dataset}_{phase}')

    if a.phase=='development':
        grid=[{'K':k,'B':b,'nlist':nlist,'nprobe':probe}
              for nlist in contract['faiss']['nlist'] for probe in contract['faiss']['nprobe']
              if probe<=min(nlist,2048) for k in contract['K'] for b in contract['B']]
        (ROOT/'development_configs.json').write_text(json.dumps(grid,indent=2)+'\n')
        frozen={}
        for dataset in ('GIST','Deep'):
            data=a.data_root/dataset/'1000000/fixtures/data.f32bin'
            qids=ROOT/'fixtures'/f'{dataset}_dev128.qid';reference=ROOT/f'oracle_{dataset}_dev128.json'
            baseline=[]
            for k in contract['K']:
                for b in contract['B']:
                    label=f'dev_gts_{dataset}_k{k}_b{b}'
                    gts(data,qids,k,b,2,ROOT/f'{dataset}.index',label,label)
                    baseline.append({'K':k,'B':b,'quality':check_gts(data,reference,label)})
            label=f'dev_ivf_{dataset}_v2'
            run(label,[a.python,ROOT/'native_ivf.py','faiss','--data',data,'--qids',qids,
                       '--reference',reference,'--configs',ROOT/'development_configs.json',
                       '--repeats',2,'--out',ROOT/f'{label}.json'])
            result=json.loads((ROOT/f'{label}.json').read_text());selected=[];anchors=[]
            for k in contract['K']:
                for b in contract['B']:
                    for anchor in contract['quality_anchors']:
                        candidates={}
                        for row in result['rows']:
                            if row['K']==k and row['B']==b and row['quality']['recall_tie_aware']>=anchor and row['quality']['distance_tolerance_pass']:
                                key=(row['nlist'],row['nprobe']);candidates.setdefault(key,[]).append(row['total_ms'])
                        if not candidates:
                            anchors.append({'K':k,'B':b,'anchor':anchor,'status':'no_development_point'});continue
                        key=min(candidates,key=lambda v:sum(candidates[v])/len(candidates[v]))
                        config={'K':k,'B':b,'nlist':key[0],'nprobe':key[1]}
                        if config not in selected:selected.append(config)
                        anchors.append({**config,'anchor':anchor,'status':'selected_from_development'})
            frozen[dataset]={'configs':selected,'anchors':anchors,'gts_development':baseline}
        (ROOT/'FROZEN_CONFIG.json').write_text(json.dumps(frozen,indent=2)+'\n')
        print('DEVELOPMENT FROZEN',json.dumps({k:v['configs'] for k,v in frozen.items()}),flush=True)
        return

    frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text())
    for round_no in range(1,contract['timing']['formal_pairs']+1):
        datasets=('GIST','Deep') if round_no%2 else ('Deep','GIST')
        for dataset in datasets:
            data=a.data_root/dataset/'1000000/fixtures/data.f32bin'
            qids=ROOT/'fixtures'/f'{dataset}_final256.qid';reference=ROOT/f'oracle_{dataset}_final256.json'
            configs=frozen[dataset]['configs'];configs=configs[round_no%len(configs):]+configs[:round_no%len(configs)]
            config_path=ROOT/f'formal_r{round_no}_{dataset}_configs.json';config_path.write_text(json.dumps(configs)+'\n')
            methods=('gts','ivf') if round_no%2 else ('ivf','gts')
            for method in methods:
                if method=='gts':
                    cases=[(k,b) for k in contract['K'] for b in contract['B']]
                    if round_no%2==0:cases.reverse()
                    for k,b in cases:
                        label=f'formal_r{round_no}_gts_{dataset}_k{k}_b{b}'
                        gts(data,qids,k,b,1,ROOT/f'{dataset}.index',label,label)
                        check_gts(data,reference,label)
                else:
                    label=f'formal_r{round_no}_ivf_{dataset}'
                    run(label,[a.python,ROOT/'native_ivf.py','faiss','--data',data,'--qids',qids,
                               '--reference',reference,'--configs',config_path,'--out',ROOT/f'{label}.json'])
    print('FORMAL COMPLETE',flush=True)


if __name__=='__main__':main()
