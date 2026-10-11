#!/usr/bin/env python3
"""Serial fail-closed qualification, work, profile and gated formal collection."""
import argparse,csv,fcntl,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from analyze import trace,formal
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['qualify','work','profile','formal'])
    for key in ('root','reference','prior','data'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--python',required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    a=p.parse_args();r=a.root.resolve();ref=a.reference.resolve();prior=a.prior.resolve();data=a.data.resolve()
    campaign_lock=(r/'campaign.lock').open('a+');fcntl.flock(campaign_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    c=json.loads((r/'CONTRACT.json').read_text());source=json.loads((r/'code/SOURCE_PINS.json').read_text())
    resource=json.loads((r/'RESOURCE_GATE.json').read_text());assert resource['pass']
    for mode,record in resource['modes'].items():
        assert sha(r/(mode+'.bench'))==record['binary_sha256']
        assert sha(r/(mode+'.resources.txt'))==record['resource_dump_sha256']
        assert sha(r/(mode+'.sass.txt'))==record['sass_dump_sha256']
        assert sha(r/(mode+'.build.log'))==record['build_log_sha256']
    physical=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=index','--format=csv,noheader'],text=True).strip()
    topology=subprocess.check_output(['nvidia-smi','topo','-m'],text=True)
    row=next(x.split() for x in topology.splitlines() if x.startswith('GPU1\t'))
    assert physical=='1' and a.numa==0 and row[-2]=='0','physical GPU/NUMA outside contract'
    shared_locks=[]
    for name in ('gtspp_gpu1.lock','gts_auto_knn_pro6000_gpu1.lock'):
        path=Path('/tmp')/name;lock=path.open('r' if path.exists() else 'a+')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);shared_locks.append(lock)
    lock_fds=tuple(x.fileno() for x in shared_locks)
    os.environ['GTS_CAMPAIGN_LOCK_FDS']=','.join(map(str,lock_fds))
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied after campaign admission'
    assert sha(data)==c['dataset']['sha256'] and sha(ref/'GIST.index')==c['index_sha256']
    for name in ('diag32.qid','confirm256.qid'):assert sha(r/name)==c[name+'_sha256']==sha(prior/name)
    for name,digest in source['files'].items():assert sha(r/'code'/name)==digest,('source drift',name)
    extension=prior.parent/'extensions/boundary'
    inputs={str(x.relative_to(r)):x for x in r.rglob('*') if x.is_file() and
        (x.parent==r and (x.suffix in ('.py','.json','.qid','.cu') or x.name=='NCU_ADMISSION.txt' or x.name.endswith(('.bench','.unit'))) or 'helpers' in x.relative_to(r).parts) and
        '__pycache__' not in x.parts and x.suffix!='.pyc' and x.name not in ('IDENTITY.json',)}
    inputs.update({'code/'+name:r/'code'/name for name in source['files']})
    inputs['code/SOURCE_PINS.json']=r/'code/SOURCE_PINS.json';inputs['data']=data
    names=['GIST.index','synthetic_96.f32bin','synthetic_960.f32bin','synthetic96.index','synthetic960.index','fixtures/synthetic_ragged33.qid']
    inputs.update({'reference/'+x:ref/x for x in names})
    for d in (96,960):
        for name in (f'oracle_allk_{d}.json',f'last_leaf_{d}.qid',f'oracle_last_{d}.json'):inputs['boundary/'+name]=extension/name
    for name in ('oracle_diag32.json','oracle_confirm256.json','diag_G0.bin'):inputs['prior/'+name]=prior/name
    bc=json.loads((r/'BOUNDARY_CONTRACT.json').read_text())
    for name,digest in bc['reference_sha256'].items():assert sha(ref/name)==digest
    identity={'inputs':{name:sha(path) for name,path in inputs.items()},'gpu':a.gpu,'numa':a.numa}
    if (r/'IDENTITY.json').exists():assert json.loads((r/'IDENTITY.json').read_text())==identity,'campaign input drift'
    else:write(r/'IDENTITY.json',identity)
    def gate(phase):
        g=json.loads((r/phase/'GATE.json').read_text());assert g['identity']==identity
        for name,digest in g['outputs'].items():assert sha(r/phase/name)==digest,(phase,name)
        return g
    if a.phase!='qualify':gate('qualify')
    if a.phase in ('profile','formal'):gate('work')
    if a.phase=='formal':assert gate('profile')['pass_gate_E'],'Gate E failed: formal phase prohibited'
    out=r/a.phase;out.mkdir(exist_ok=False)
    write(out/'FROZEN.json',{'identity':identity,'nvcc':subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),
        'topology':topology,'gpu':subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=name,driver_version,uuid,memory.total,clocks.sm,clocks.mem,power.limit','--format=csv,noheader'],text=True)})
    subprocess.run([a.python,'-c','import sys;sys.path.insert(0,sys.argv[1]);import verify_outputs',str(r/'helpers')],check=True)
    rows=[];sanitizer=str(Path(shutil.which('compute-sanitizer')).resolve())
    def launch(label,cmd,tool=None):
        report=out/'runs'/label
        if tool:cmd=[sanitizer,'--tool',tool,'--error-exitcode','99',*cmd]
        subprocess.run([sys.executable,r/'locked.py','--gpu',a.gpu,'--numa-node',str(a.numa),'--output',report,'--',*map(str,cmd)],check=True,pass_fds=lock_fds)
        receipt=json.loads((report/'receipt.json').read_text());assert receipt['runtime_valid']
        assert all(not x['foreign'] for x in json.loads((report/'checks.json').read_text()))
        log=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
        assert not re.search(r'\berror\s*:|\bFAIL\s*:|Error!!!|cuda.{0,60}(?:error|failed)',log,re.I),log[-2000:]
        if tool:assert ('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
        row={'label':label,'receipt_sha256':sha(report/'receipt.json'),'sanitizer':tool};rows.append(row)
        print('RUNTIME '+label,flush=True);return row
    def check(label,table,oracle,row):
        target=out/(label+'.quality.json')
        subprocess.run([a.python,r/'helpers/verify_outputs.py','check-gts','--data',table,'--reference',oracle,'--result',out/(label+'.bin'),'--out',target],check=True)
        quality=json.loads(target.read_text());assert quality['recall_tie_aware']==1 and quality['distance_tolerance_pass']
        row.update({'quality':quality,'result_sha256':sha(out/(label+'.bin'))})
        print('VALIDATED '+label,flush=True)
    def query(label,mode,qids,oracle,table=data,index=ref/'GIST.index',k=8,tool=None,prefix=None):
        cmd=[r/(mode+'.bench'),table,qids,k,1,1,index,out/label,2]
        if prefix:cmd=[*prefix,*cmd]
        row=launch(label,cmd,tool);check(label,table,oracle,row);return row
    def equal(labels):
        assert len({sha(out/(x+'.bin')) for x in labels})==1,('output disagreement',labels)
    if a.phase=='qualify':
        for mode in ('G0','G1','G2'):
            launch('unit_'+mode,[r/(mode+'.unit'),out/('unit_'+mode+'.bin')])
        equal(['unit_'+m for m in ('G0','G1','G2')])
        for mode in ('G1','G2'):
            for tool in ('memcheck','racecheck','synccheck'):
                label='unit_'+mode+'_'+tool;launch(label,[r/(mode+'.unit'),out/(label+'.bin')],tool)
                equal(['unit_G0',label])
        for d in (96,960):
            for k in (1,8,32):
                for mode in ('G0','G1','G2'):
                    query(f'd{d}_k{k}_{mode}',mode,ref/'fixtures/synthetic_ragged33.qid',extension/f'oracle_allk_{d}.json',ref/f'synthetic_{d}.f32bin',ref/f'synthetic{d}.index',k)
                equal([f'd{d}_k{k}_{m}' for m in ('G0','G1','G2')])
            for mode in ('G0','G1','G2'):
                query(f'last_d{d}_{mode}',mode,extension/f'last_leaf_{d}.qid',extension/f'oracle_last_{d}.json',ref/f'synthetic_{d}.f32bin',ref/f'synthetic{d}.index')
            equal([f'last_d{d}_{m}' for m in ('G0','G1','G2')])
        for mode in ('G1','G2'):
            for tool in ('memcheck','racecheck','synccheck'):
                query(mode+'_'+tool,mode,ref/'fixtures/synthetic_ragged33.qid',extension/'oracle_allk_96.json',ref/'synthetic_96.f32bin',ref/'synthetic96.index',tool=tool)
                equal(['d96_k8_G0',mode+'_'+tool])
    elif a.phase=='work':
        for mode in ('G0','G1','G2','G0_count','G1_count','G2_count'):
            query(mode,mode,r/'diag32.qid',prior/'oracle_diag32.json')
        equal(['G0','G1','G2','G0_count','G1_count','G2_count'])
        assert sha(out/'G0.bin')==sha(prior/'diag_G0.bin')
        assert len({sha(out/(m+'_count.geometry.bin')) for m in ('G0','G1','G2')})==1,'work/visit/bound drift'
        sys.path.insert(0,str(r/'helpers'));from geometry_analyze import analyze
        base=analyze(ref/'GIST.index',out/'G0_count.geometry.bin',out/'G0.bin',prior/'oracle_diag32.json')
        geometry={}
        for mode in ('G0','G1','G2'):
            rr=[]
            for row in base['rows']:
                count=row['totals']['visited_leaves'];bins=(count+2)//3 if mode=='G2' else count
                rr.append({'qid':row['qid'],'leaves':count,'ctas':bins,'threads':512 if mode=='G0' else 32,
                    'full_groups':count//3 if mode=='G2' else count,'tail_leaves':count%3 if mode=='G2' else 0})
            geometry[mode]=rr
        write(out/'WORK_COUNTS.json',{'scope':'Identical bytewise node sidecars; G0 analysis plus source-derived mappings, not hardware occupancy',
            'base':base,'mode_geometry':geometry,'sidecars_bit_identical':True})
    elif a.phase=='profile':
        work=json.loads((r/'work/WORK_COUNTS.json').read_text());results={}
        nsys=str(Path(shutil.which('nsys')).resolve())
        for number,order in enumerate(c['diag_process_orders'],1):
            for mode in order:
                label=f'r{number}_{mode}';prefix=[nsys,'profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none',
                    '--capture-range=nvtx','--nvtx-capture=formal.query_pass','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
                    '--capture-range-end=stop','--force-overwrite=false','-o',out/label]
                query(label,mode,r/'diag32.qid',prior/'oracle_diag32.json',prefix=prefix)
                subprocess.run([nsys,'export','--type=sqlite','--output',out/(label+'.sqlite'),out/(label+'.nsys-rep')],check=True)
                results[label]=trace(out/(label+'.sqlite'))
                for observed,expected in zip(results[label]['rows'],work['mode_geometry'][mode]):
                    assert observed['ctas']==expected['ctas'] and observed['threads']==expected['threads'],'runtime geometry mismatch'
            equal([f'r{number}_{m}' for m in ('G0','G1','G2')])
        # Counter permission probe is retained; do not escalate or change driver policy.
        probe=(r/'NCU_ADMISSION.txt').read_text()
        assert 'ERR_NVGPUCTRPERM' in probe,'counter status changed; requires separately frozen NCU collection'
        verdict=all(results[f'r{i}_G2']['leaf_inclusive_ms']<results[f'r{i}_G1']['leaf_inclusive_ms'] for i in (1,2))
        physical=all(results[f'r{i}_G2']['leaf_ctas']<results[f'r{i}_G1']['leaf_ctas'] for i in (1,2))
        write(out/'MECHANISM_RESULTS.json',{'results':results,'G1_leaf_improves_both':all(results[f'r{i}_G1']['leaf_inclusive_ms']<results[f'r{i}_G0']['leaf_inclusive_ms'] for i in (1,2)),
            'G2_leaf_improves_both':verdict,'runtime_cta_reduction_verified':physical,'pass_gate_E':verdict and physical,
            'NCU':'unavailable: ERR_NVGPUCTRPERM; no issued-instruction, DRAM/L2 traffic, SM utilization or hardware occupancy claim',
            'E5_evidence':'NSYS-recorded actual grid/block counts, same work and smaller leaf duration; not a hardware scheduling-overhead counter'})
    else:
        for number,order in enumerate(c['formal_process_orders'],1):
            for mode in order:query(f'r{number}_{mode}',mode,r/'confirm256.qid',prior/'oracle_confirm256.json')
            equal([f'r{number}_{m}' for m in ('G0','G1','G2')])
        summary=formal(out,c);write(out/'SUMMARY.json',summary)
        with (out/'FORMAL_ROUNDS.csv').open('x') as f:
            w=csv.DictWriter(f,fieldnames=summary['rows'][0]);w.writeheader();w.writerows(summary['rows'])
    assert identity['inputs']=={name:sha(path) for name,path in inputs.items()},'closing input drift'
    record={'identity':identity,'rows':rows,'outputs':{str(x.relative_to(out)):sha(x) for x in out.rglob('*') if x.is_file()}}
    if a.phase=='profile':record['pass_gate_E']=verdict and physical
    write(out/'GATE.json',record);print('PASS '+a.phase,flush=True)
if __name__=='__main__':main()
