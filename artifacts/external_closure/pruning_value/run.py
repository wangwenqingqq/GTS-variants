#!/usr/bin/env python3
"""Single registered diagnosis with stage gates, existing isolation guard, no automatic retry."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from build import save,sha,outside_repo
if not __debug__:raise RuntimeError("Python assertions are required")
HERE=Path(__file__).resolve().parent

def main(a):
    a.work=outside_repo(a.work);a.work.mkdir(exist_ok=False);records=json.loads(a.inputs.read_text())['records']
    for name,r in records.items():
        assert sha(Path(r['data']))==r['data_sha256']
        assert sha(a.references/name/'REFERENCE.json')==r['reference_sha256']
        (a.work/(name+'.qids')).write_text('\n'.join(map(str,r['qids']))+'\n')
    jobs=[('bounded_capture','bounded','capture',None),('bounded_timing','bounded','timing',None)]+[(f'bounded_{t}','bounded','timing',t) for t in ('memcheck','racecheck','synccheck','initcheck')]+[(f'{n}_{s}',n,s,None) for n in ('initial','first_rebuilt') for s in ('capture','timing')]
    save(a.work/'REGISTERED.json',dict(contract_sha256=sha(HERE/'CONTRACT.json'),inputs_sha256=sha(a.inputs),source_hashes={p.name:sha(p) for p in HERE.glob('*') if p.is_file()},build=json.loads((a.build/'BUILD.json').read_text()),jobs=jobs,gpu=a.gpu,numa=a.numa))
    build=json.loads((a.build/'BUILD.json').read_text());compiled=json.loads((a.build/'REGISTERED.json').read_text())
    assert compiled['probe_sha256']==sha(HERE/'probe.cu') and compiled['contract_sha256']==sha(HERE/'CONTRACT.json')
    guard_hash=sha(a.guard)
    for label,name,mode,tool in jobs:
        assert sha(a.build/mode)==build[mode] and sha(a.guard)==guard_hash
        assert sha(a.inputs)==json.loads((a.work/'REGISTERED.json').read_text())['inputs_sha256']
        assert sha(a.references/name/'REFERENCE.json')==records[name]['reference_sha256']
        if mode=='timing':
            cache=a.work/(name+'_cache');proof=json.loads((cache/'CAPTURE.json').read_text())
            assert all(sha(cache/k)==v for k,v in proof['cache_hashes'].items())
        save(a.work/(label+'_BEFORE.json'),dict(binary_sha256=sha(a.build/mode),guard_sha256=guard_hash,reference_sha256=sha(a.references/name/'REFERENCE.json'),cache_hashes=proof['cache_hashes'] if mode=='timing' else None))
        # Each new process gets both an exclusive shared lock and live ownership checks.
        audit=a.audits/('stress4096_B1/build2' if name=='bounded' else 'million_prefix_B1/build'+('2' if name=='initial' else '3'))
        cmd=[str(a.build/mode),records[name]['data'],str(a.work/(name+'.qids')),str(a.work/label),str(a.work/(name+'_cache'))]
        if tool:cmd=['/usr/local/bin/compute-sanitizer','--tool',tool,'--error-exitcode','90',*cmd]
        guard=['python3',str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(a.work/(label+'_guard')),'--',*cmd]
        subprocess.run(guard,check=True,env=dict(os.environ,REGION_MODE='PAR_STRONG',KNN_MODE='FULL',BUILD_MAPPING='TILED',U10_TREE_AUDIT='0',U10_OBSERVE='0'))
        assert sha(a.build/mode)==build[mode] and sha(a.guard)==guard_hash
        if mode=='timing':assert all(sha(cache/k)==v for k,v in proof['cache_hashes'].items())
        if tool:
            text=''.join((a.work/(label+'_guard')/f).read_text() for f in ('stdout.log','stderr.log'))
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in text
        subprocess.run([sys.executable,str(HERE/'analyze.py'),mode,'--root',str(a.work/label),'--reference',str(a.references/name),'--qids',str(a.work/(name+'.qids')),'--audit',str(audit),'--output',str(a.work/(name+'_cache' if mode=='capture' else label+'_checked'))],check=True)
        save(a.work/(label+'_PASSED.json'),dict(passed=True,guard_sha256=sha(a.work/(label+'_guard')/'receipt.json')))
        print('PASSED',label,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','inputs','references','audits','build','guard'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);main(p.parse_args())
