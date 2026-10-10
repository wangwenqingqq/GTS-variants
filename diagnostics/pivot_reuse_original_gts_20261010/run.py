#!/usr/bin/env python3
"""Serial, fail-closed G0/G1 phases using the existing locked runner and oracle."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')

def runtime_errors(log):
    return [line for line in log.splitlines()
            if re.search(r'\berror\s*:|\bFAIL\s*:|Error!!!|cuda.{0,60}(?:error|failed)',line,re.I)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['diagnose','qualify','freeze','formal'])
    for key in ('root','reference','data'):p.add_argument('--'+key,required=True,type=Path)
    p.add_argument('--python',required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    a=p.parse_args();r=a.root.resolve();ref=a.reference.resolve();data=a.data.resolve()
    contract=json.loads((HERE/'CONTRACT.json').read_text())
    assert sha(data)==contract['dataset']['sha256']
    assert sha(ref/'GIST.index')==contract['index_sha256']
    source=json.loads((r/'v2/SOURCE_PINS.json').read_text())
    assert sha(r/'v2/bench.cu')==source['driver_sha256']
    for mode,pins in source['variants'].items():
        assert sha(r/f'v2/{mode}/include/search_v2.cuh')==pins['search_sha256']
        assert sha(r/f'v2/{mode}/include/reuse.cuh')==pins['support_sha256']
        for name,digest in source['upstream']['adapted'].items():
            if name!='include/search_v2.cuh':assert sha(r/'v2'/mode/name)==digest
    artifacts=[r/'v2/SOURCE_PINS.json',*(r/f'v2/{mode}.bench' for mode in source['variants']),r/'v2/test_cache',
               r/'helpers/run_locked.py',r/'helpers/native_ivf.py',r/'helpers/verify_outputs.py',r/'locked.py',
               HERE/'CONTRACT.json']
    identity={str(p.relative_to(r)) if p.is_relative_to(r) else p.name:sha(p) for p in artifacts}
    identity.update({'data_sha256':sha(data),'index_sha256':sha(ref/'GIST.index'),'gpu':a.gpu,'numa':a.numa})
    def mechanism_identity(x):
        # Pre-freeze orchestration changes are separately pinned per phase.
        # Earlier diagnostic records also pinned the initial orchestrator here.
        return {k:v for k,v in x.items() if k!='run.py'}
    if (r/'IDENTITY.json').exists():assert mechanism_identity(json.loads((r/'IDENTITY.json').read_text()))==identity,'campaign drift'
    else:write(r/'IDENTITY.json',identity)
    os.chdir(r)

    def gate(name):
        x=json.loads((r/(name+'.gate.json')).read_text());assert mechanism_identity(x['identity'])==identity
        for file,digest in x['outputs'].items():assert sha(r/file)==digest,file
        return x

    outputs=[]
    sanitizer=str(Path(shutil.which('compute-sanitizer')).resolve())
    def launch(label,command):
        report=r/'runs'/label
        try:
            subprocess.run([sys.executable,r/'locked.py','--gpu',a.gpu,'--numa-node',str(a.numa),
                            '--output',report,'--',*map(str,command)],check=True)
            receipt=report/'receipt.json';assert json.loads(receipt.read_text())['runtime_valid']
            errors=runtime_errors((report/'stdout.log').read_text()+(report/'stderr.log').read_text())
            assert not errors,errors
        except Exception as exc:
            if report.exists():write(report/'eligibility.json',{'eligible':False,'reason':repr(exc)})
            raise
        write(report/'eligibility.json',{'eligible':True,'native_runtime_log_clean':True})
        outputs.append(receipt)
        outputs.append(report/'eligibility.json')
        return report

    def check(label,table,oracle):
        target=r/(label+'.quality.json')
        subprocess.run([a.python,r/'helpers/verify_outputs.py','check-gts','--data',table,
                        '--reference',oracle,'--result',r/(label+'.bin'),'--out',target],check=True)
        x=json.loads(target.read_text());assert x['recall_tie_aware']==1 and x['distance_tolerance_pass'],x
        outputs.extend([target,r/(label+'.bin'),r/(label+'.csv'),r/(label+'.reuse.json')])

    def query(label,mode,qids,oracle,table=data,index=ref/'GIST.index',tool=None):
        cmd=[r/f'v2/{mode}.bench',table,qids,8,1,1,index,r/label,2]
        if tool:cmd=[sanitizer,'--tool',tool,'--error-exitcode','99',*cmd]
        report=launch(label,cmd)
        if tool:
            logs=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
            marker='RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors'
            assert marker in logs,(tool,logs[-1000:])
        check(label,table,oracle)

    if a.phase=='diagnose':
        reference=json.loads((ref/'oracle_GIST_final256.json').read_text())
        reference['records']=reference['records'][:32];reference['Q']=32
        write(r/'oracle_diag32.json',reference)
        ids=[x['qid'] for x in reference['records']]
        (r/'diag32.qid').write_text('32\n'+''.join(f'{q}\n' for q in ids))
        for mode in ('G0','G1','G0_count','G1_count'):
            query('diag_'+mode,mode,r/'diag32.qid',r/'oracle_diag32.json')
        base=(r/'diag_G0.bin').read_bytes()
        assert all((r/('diag_'+m+'.bin')).read_bytes()==base for m in ('G1','G0_count','G1_count'))
        rows={m:list(csv.DictReader((r/f'diag_{m}.work.csv').open())) for m in ('G0_count','G1_count')}
        assert len(rows['G0_count'])==len(rows['G1_count'])==32
        invariant=['qid','pivot_seen','unique_pivot_pairs','leaf_seen','pivot_leaf_seen','leaf_nodes','node_tests',
                   'node_pass','bound_updates','first_bound_count','first_bound_level_width','leaf_id_sum','node_id_sum']
        for x,y in zip(rows['G0_count'],rows['G1_count']):
            assert all(x[k]==y[k] for k in invariant),(x,y)
            assert int(y['bridge_mismatches'])==0
        work={'scope':'fixed32 diagnostic only, instrumentation time excluded from formal performance',
              'per_query':rows,'invariants_pass':True,'totals':{}}
        for mode,data_rows in rows.items():
            work['totals'][mode]={k:sum(int(x[k]) for x in data_rows) for k in data_rows[0] if k!='qid'}
            outputs.append(r/f'diag_{mode}.work.csv')
        write(r/'WORK_COUNTS.json',work);outputs.extend([r/'WORK_COUNTS.json',r/'diag32.qid',r/'oracle_diag32.json'])
    elif a.phase=='qualify':
        gate('diagnose')
        for tool in ('memcheck','racecheck','synccheck'):
            report=launch('unit_'+tool,[sanitizer,'--tool',tool,'--error-exitcode','99',r/'v2/test_cache'])
            logs=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
            marker='RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors'
            assert marker in logs,(tool,logs[-1000:])
        for d in (96,960):
            table=ref/f'synthetic_{d}.f32bin';oracle=ref/f'oracle_synthetic{d}.json';qids=ref/'fixtures/synthetic_ragged33.qid'
            for mode in ('G0','G1'):
                query(f'small{d}_{mode}',mode,qids,oracle,table,ref/f'synthetic{d}.index')
            assert (r/f'small{d}_G0.bin').read_bytes()==(r/f'small{d}_G1.bin').read_bytes()
        oracle=json.loads((r/'oracle_diag32.json').read_text());oracle['records']=oracle['records'][:1];oracle['Q']=1
        write(r/'oracle_one.json',oracle);(r/'one.qid').write_text('1\n'+str(oracle['records'][0]['qid'])+'\n')
        for tool in ('memcheck','racecheck','synccheck'):
            query('real_'+tool,'G1',r/'one.qid',r/'oracle_one.json',tool=tool)
    elif a.phase=='freeze':
        gate('diagnose');gate('qualify')
        # The inventory is caller-supplied and retained, not reconstructed from beneficial queries.
        inventory=json.loads((r/'HISTORICAL_INVENTORY.json').read_text())
        forbidden=set(inventory['excluded_ids']);forbidden.update(map(int,(r/'diag32.qid').read_text().split()[1:]))
        rng=random.Random(contract['confirmation_queries']['seed']);ids=[]
        while len(ids)<256:
            q=rng.randrange(1000000)
            if q not in forbidden:ids.append(q);forbidden.add(q)
        write(r/'FROZEN.json',{'identity':identity,'inventory_sha256':sha(r/'HISTORICAL_INVENTORY.json'),
            'query_seed':contract['confirmation_queries']['seed'],'scope':inventory['scope'],
            'query_ids':ids,'modes':['G0','G1'],'orchestrator_sha256':sha(HERE/'run.py'),
            'no_parameter_changes_after_this_point':True})
        (r/'confirm256.qid').write_text('256\n'+''.join(f'{q}\n' for q in ids))
        launch('oracle_confirm',[a.python,r/'helpers/native_ivf.py','oracle','--data',data,
                                '--qids',r/'confirm256.qid','--out',r/'oracle_confirm256.json'])
        outputs.extend([r/'FROZEN.json',r/'confirm256.qid',r/'oracle_confirm256.json',r/'HISTORICAL_INVENTORY.json'])
    else:
        gate('diagnose');gate('qualify');gate('freeze')
        frozen=json.loads((r/'FROZEN.json').read_text());assert frozen['identity']==identity
        assert frozen['orchestrator_sha256']==sha(HERE/'run.py'),'post-freeze orchestration drift'
        for round_id,order in enumerate(contract['process_orders'],1):
            for mode in order:
                query(f'formal_r{round_id}_{mode}',mode,r/'confirm256.qid',r/'oracle_confirm256.json')
            assert (r/f'formal_r{round_id}_G0.bin').read_bytes()==(r/f'formal_r{round_id}_G1.bin').read_bytes()
    write(r/(a.phase+'.gate.json'),{'identity':identity,'orchestrator_sha256':sha(HERE/'run.py'),
                                  'outputs':{str(x.relative_to(r)):sha(x) for x in outputs}})
    print('PASS phase',a.phase,flush=True)

if __name__=='__main__':main()
