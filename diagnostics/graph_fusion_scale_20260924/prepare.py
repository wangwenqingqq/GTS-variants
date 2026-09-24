#!/usr/bin/env python3
"""Reuse the pinned scale driver and selector; retain the B/C branch exactly."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
scale=module('scale_prepare',HERE.parent/'graph_scale_20260923/prepare.py')
BASE_SHA='75ba007721f255d4680f1351a35a084c30e2a9ae75922cdc876c99338335d484'

def selector():
    s=(HERE.parent/'fused_result_20260923/fused_result.cuh').read_text()
    assert hashlib.sha256(s.encode()).hexdigest()=='9cfe596b73d80a4632d66eaef5ea7283d6fd0230041dd93f2fff391eb572a8f4'
    s=scale.once(s,'const int* candidates, const int* hits,','const int* candidates, int capacity, const int* hits,')
    return scale.once(s,'*candidates<=111','*candidates<=capacity && capacity<=111111')

def transform(s):
    assert hashlib.sha256(s.encode()).hexdigest()==BASE_SHA
    s=scale.once(s,'struct Fixed {','#include "fused_result.cuh"\n\nstruct Fixed {\n    bool fused;')
    s=scale.once(s,'Fixed(int count_n,int h,int b):nodes','Fixed(int count_n,int h,int b,bool f=false):fused(f),nodes')
    start='        ck(cub::DeviceReduce::Sum(temp,tempbytes,hits,hit_count,slots,stream));'
    end='        projectBounded<<<(slots+511)/512,512,0,stream>>>(count,outids,outdis,ids,ds,is_delete_prefix);'
    old=s[s.index(start):s.index(end)+len(end)]
    s=scale.once(s,old,'''        if(fused) {
            ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
            fusedResultSelect<<<1,512,0,stream>>>(candidate_count,nodes,hits,rawids,rawdis,is_delete_prefix,count,outids,outdis);
        } else {
'''+old+'\n        }')
    s=scale.once(s,'mode=="A"||mode=="B"||mode=="C"','mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E"')
    s=scale.once(s,'new Fixed(n,tree_h,bundle)','new Fixed(n,tree_h,bundle,mode=="D"||mode=="E")')
    s=scale.once(s,'if(mode=="C")','if(mode=="C"||mode=="E")')
    s=scale.once(s,'fixed->query(qs,radius,mode=="C")','fixed->query(qs,radius,mode=="C"||mode=="E")')
    return s

def prepare(source,out):
    scale.prepare(source,out)
    p=out/'graph_bench.cu';p.write_text(transform(p.read_text()))
    (out/'fused_result.cuh').write_text(selector())
    for name in ['test_selector.cu','suite.py']:shutil.copy2(HERE/name,out/name)
    (out/'run_fusion.py').write_text(runner((out/'run_scale.py').read_text()))

def runner(s):
    s=scale.once(s,"choices=['A','B','C']","choices=['A','B','C','D','E','T']")
    s=scale.once(s,"'synccheck','initcheck']","'synccheck','initcheck','racecheck']")
    s=scale.once(s,"    if tool.startswith('nsys'):","    if mode=='T':cmd=[str(root/'bin/test_selector')]\n    if tool.startswith('nsys'):")
    s=scale.once(s,"gold=root/'fixtures'/f'expected_{radius:g}.json'","gold=root/'fixtures'/('expected_selector.json' if mode=='T' else f'expected_{radius:g}.json')")
    s=scale.once(s,"    record={'bundle':bundle", "    if mode=='T':\n        validation={'pass':'PASS selector 352 cases' in logs,'scope':'standalone scale selector'}\n        if not validation['pass']:errors.append('selector check incomplete')\n    record={'bundle':bundle")
    s=scale.once(s,"(root/'bin/graph_bench').read_bytes()","(root/'bin'/('test_selector' if mode=='T' else 'graph_bench')).read_bytes()")
    # A bounded NVML probe fails admission before launching work on an unobservable GPU.
    s=scale.once(s,"text=True)","text=True,timeout=15)")
    s=scale.once(s,"                    apps=snapshot(gpu)['apps'];foreign=[x for x in apps.splitlines() if int(x.split(',')[0]) not in owned]", """                    apps='';foreign=[]
                    try:
                        apps=snapshot(gpu)['apps'];foreign=[x for x in apps.splitlines() if int(x.split(',')[0]) not in owned]
                    except (subprocess.SubprocessError,ValueError):reason='GPU telemetry failure'""")
    spawn="""        p=subprocess.Popen(cmd,cwd=path,env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu,'GTS_BUNDLE':str(bundle)},stdout=out,stderr=err,start_new_session=True)
        owned.add(p.pid);nextcheck=start+.2
        try:"""
    s=scale.once(s,spawn,"""        p=None
        try:
            p=subprocess.Popen(cmd,cwd=path,env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu,'GTS_BUNDLE':str(bundle)},stdout=out,stderr=err,start_new_session=True)
            owned.add(p.pid);nextcheck=start+.2""")
    s=scale.once(s,"        finally:mon.terminate();mon.wait(timeout=10)", """        except BaseException as e:
            (path/'collector_failure.json').write_text(json.dumps({'error_type':type(e).__name__,'message':str(e),'owned_pid':p.pid if p else None}))
            raise
        finally:
            if p is not None:stop_owned(p,True)
            stop_owned(mon,False)""")
    s=scale.once(s,'def execute(','''def stop_owned(p,group):
    if p.returncode is not None:return
    try:
        if group:os.killpg(p.pid,signal.SIGTERM)
        else:p.terminate()
    except ProcessLookupError:pass
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if group:os.killpg(p.pid,signal.SIGKILL)
            else:p.kill()
        except ProcessLookupError:pass
        p.wait(timeout=5)

def execute(''')
    s=scale.once(s,"    after=snapshot(gpu);(path/'after.json').write_text(json.dumps(after));(path/'checks.json').write_text(json.dumps(checks,indent=2))", """    try:after=snapshot(gpu)
    except subprocess.SubprocessError:
        after={'gpu':'unavailable','apps':'unavailable'};reason=reason or 'post-run GPU telemetry failure'
    (path/'after.json').write_text(json.dumps(after));(path/'checks.json').write_text(json.dumps(checks,indent=2))""")
    return s

def fixtures(data,out):
    module('scale_fixtures',HERE.parent/'graph_scale_20260923/fixtures.py').prepare(data,out)
    f=out/'fixtures/611756';manifest=f/'manifest.json';m=json.loads(manifest.read_text())
    ids=m['qids'][:32];q=f/'bundle.qid';q.write_text('32\n'+'\n'.join(map(str,ids))+'\n')
    m['file_sha256']['bundle.qid']=hashlib.sha256(q.read_bytes()).hexdigest();manifest.write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    for mode in ['source','fixtures']:
        q=sub.add_parser(mode);q.add_argument('input',type=Path);q.add_argument('out',type=Path)
    a=p.parse_args()
    if a.mode=='source':prepare(a.input,a.out)
    else:fixtures(a.input,a.out)
