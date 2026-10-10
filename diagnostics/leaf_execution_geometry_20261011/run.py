#!/usr/bin/env python3
"""Serial diagnostic collection; no timing comparison or optimization dispatch."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('reference','prior','data'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--python',required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    a=p.parse_args();r=HERE;ref=a.reference.resolve();prior=a.prior.resolve();data=a.data.resolve()
    subprocess.run([a.python,'-c',"import sys;sys.path.insert(0,sys.argv[1]);import verify_outputs",str(r/'helpers')],check=True)
    physical=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=index','--format=csv,noheader'],text=True).strip()
    topology=subprocess.check_output(['nvidia-smi','topo','-m'],text=True)
    device_row=next(line.split() for line in topology.splitlines() if line.startswith('GPU1\t'))
    assert physical=='1' and a.numa==0 and device_row[-2]=='0','physical GPU/NUMA outside contract'
    c=json.loads((r/'CONTRACT.json').read_text());source=json.loads((r/'code/SOURCE_PINS.json').read_text())
    assert sha(data)==c['dataset']['sha256'] and sha(ref/'GIST.index')==c['index_sha256']
    assert sha(r/'diag32.qid')==c['query_sha256']
    for name,digest in source['files'].items():assert sha(r/'code'/name)==digest,('source drift',name)
    extension=prior.parent/'extensions/boundary'
    needed={'GIST.index', 'fixtures/synthetic_ragged33.qid'}
    for d in (96,960):needed.update([f'synthetic_{d}.f32bin',f'synthetic{d}.index'])
    for name in needed:assert (ref/name).is_file(),name
    inputs={**{str(x.relative_to(r)):x for x in r.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'},
      **{'reference/'+name:ref/name for name in needed},'data':data,
      'prior/oracle_diag32.json':prior/'oracle_diag32.json','prior/diag_G0.bin':prior/'diag_G0.bin'}
    for d in (96,960):
        for name in (f'oracle_allk_{d}.json',f'last_leaf_{d}.qid',f'oracle_last_{d}.json'):
            assert (extension/name).is_file();inputs['prior_extension/'+name]=extension/name
    # Validate read-only reference identity against the prior qualification contract.
    bc=json.loads((r/'BOUNDARY_CONTRACT.json').read_text())
    for name,digest in bc['reference_sha256'].items():assert sha(ref/name)==digest
    before={name:sha(path) for name,path in inputs.items()}
    write(r/'FROZEN.json',{'inputs':before,'gpu':a.gpu,'numa':a.numa,'source':source,
        'software':{'nvcc':subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),
                    'gpu':subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=name,driver_version,uuid','--format=csv,noheader'],text=True)}})
    rows=[];sanitizer=str(Path(shutil.which('compute-sanitizer')).resolve())
    def query(label,mode,table,index,qids,oracle,k=8,tool=None):
        prefix=r/label;report=r/'runs'/label
        cmd=[r/(mode+'.bench'),table,qids,k,1,1,index,prefix,0]
        if tool:cmd=[sanitizer,'--tool',tool,'--error-exitcode','99',*cmd]
        subprocess.run([sys.executable,r/'locked.py','--gpu',a.gpu,'--numa-node',str(a.numa),
                        '--output',report,'--',*map(str,cmd)],check=True)
        receipt=json.loads((report/'receipt.json').read_text());assert receipt['runtime_valid']
        assert all(not x['foreign'] for x in json.loads((report/'checks.json').read_text()))
        logs=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
        assert not re.search(r'\berror\s*:|\bFAIL\s*:|Error!!!|cuda.{0,60}(?:error|failed)',logs,re.I)
        if tool:assert ('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs
        quality=r/(label+'.quality.json')
        subprocess.run([a.python,r/'helpers/verify_outputs.py','check-gts','--data',table,
            '--reference',oracle,'--result',r/(label+'.bin'),'--out',quality],check=True)
        q=json.loads(quality.read_text());assert q['recall_tie_aware']==1 and q['distance_tolerance_pass']
        record={'label':label,'receipt_sha256':sha(report/'receipt.json'),'stdout_sha256':sha(report/'stdout.log'),
                'stderr_sha256':sha(report/'stderr.log'),'result_sha256':sha(r/(label+'.bin')),'quality':q}
        if mode=='Gcount':
            from analyze import analyze
            result=analyze(index,r/(label+'.geometry.bin'),r/(label+'.bin'),oracle)
            write(r/(label+'.work.json'),result);record['work_sha256']=sha(r/(label+'.work.json'))
        rows.append(record);write(r/(label+'.validated.json'),record)
        print('VALIDATED '+label,flush=True)
    for d in (96,960):
        for k in (1,8,32):
            for mode in ('G0','Gcount'):
                query(f'd{d}_k{k}_{mode}',mode,ref/f'synthetic_{d}.f32bin',ref/f'synthetic{d}.index',
                      ref/'fixtures/synthetic_ragged33.qid',extension/f'oracle_allk_{d}.json',k)
            assert (r/f'd{d}_k{k}_G0.bin').read_bytes()==(r/f'd{d}_k{k}_Gcount.bin').read_bytes()
        for mode in ('G0','Gcount'):
            query(f'last_d{d}_{mode}',mode,ref/f'synthetic_{d}.f32bin',ref/f'synthetic{d}.index',
                  extension/f'last_leaf_{d}.qid',extension/f'oracle_last_{d}.json')
        assert (r/f'last_d{d}_G0.bin').read_bytes()==(r/f'last_d{d}_Gcount.bin').read_bytes()
    for tool in ('memcheck','racecheck','synccheck'):
        query(tool,'Gcount',ref/'synthetic_96.f32bin',ref/'synthetic96.index',
              ref/'fixtures/synthetic_ragged33.qid',extension/'oracle_allk_96.json',tool=tool)
    for mode in ('G0','Gcount'):
        query('diag32_'+mode,mode,data,ref/'GIST.index',r/'diag32.qid',prior/'oracle_diag32.json')
    assert (r/'diag32_G0.bin').read_bytes()==(r/'diag32_Gcount.bin').read_bytes()==(prior/'diag_G0.bin').read_bytes()
    assert before=={name:sha(path) for name,path in inputs.items()},'collection input drift'
    write(r/'COMPLETE.json',{'scope':'diagnostics and correctness only','rows':rows,
        'frozen_sha256':sha(r/'FROZEN.json'),'all_pairs_bit_identical':True,'unchanged_prior_G0_results':True})
    print('COMPLETE diagnostic gates only; no optimization or formal timing',flush=True)
if __name__=='__main__':main()
