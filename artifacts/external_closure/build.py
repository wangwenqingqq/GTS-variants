#!/usr/bin/env python3
"""Build the labeled adapters from pinned local source and installed dependencies."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from common import outside_repo
from prepare_tree import prepare,HERE

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(a):
    work=outside_repo(a.work);work.mkdir(parents=True,exist_ok=False);prepare(a.upstream,work/'tree_source')
    nvcc=(a.cuda/'bin/nvcc').resolve();assert nvcc.is_file()
    common=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120']
    site=a.cuvs_site.resolve();libs=sorted({str(p) for p in site.rglob('*') if p.is_dir() and p.name in ('lib','lib64')})
    env=dict(os.environ,LD_LIBRARY_PATH=':'.join(libs+[str(a.cuda/'lib64')]))
    recipes=[]
    for name,flags in (('tree_native',[]),('tree_adapt',['-DCLOSURE_REUSE']),('tree_safe',['-DCLOSURE_REUSE','-DCLOSURE_TAIL_SAFE','-Xnvlink=--ignore-host-info'])):
        recipes.append((name,common+['-rdc=true',*flags,'-I'+str(work/'tree_source/include'),str(work/'tree_source/tree_service.cu'),'-o',str(work/name)]))
    recipes.append(('range_service',common+['-I'+str(site/'libcuvs/include'),'-I'+str(a.dlpack_include),str(HERE/'range_service.cu'),
        '-L'+str(site/'libcuvs/lib64'),'-lcuvs_c','-L'+str(site/'rapids_logger/lib64'),'-lrapids_logger','-L'+str(site/'librmm/lib64'),'-lrmm','-o',str(work/'range_service')]))
    manifest=dict(source_sha256={p.name:sha(p) for p in HERE.iterdir() if p.is_file()},commands=dict(recipes),
        nvcc_version=subprocess.check_output([nvcc,'--version'],text=True),nvcc_sha256=sha(nvcc),library_search_dirs=libs)
    (work/'BUILD_REGISTERED.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for name,cmd in recipes:
        with (work/(name+'.compile.log')).open('x') as log:subprocess.run(cmd,stdout=log,stderr=log,env=env,check=True)
    ldd=subprocess.check_output(['ldd',str(work/'range_service')],env=env,text=True);assert 'not found' not in ldd
    (work/'ldd.txt').write_text(ldd)
    dependencies={}
    for line in ldd.splitlines():
        if '=>' in line:
            target=line.split('=>',1)[1].split()[0]
            if target.startswith('/') and any(key in Path(target).name for key in ('cuvs','rmm','rapids','cuda')):dependencies[Path(target).name]=sha(target)
    (work/'BUILD.json').write_text(json.dumps(dict(binaries={name:sha(work/name) for name,_ in recipes},dependencies=dependencies,
        registration_sha256=sha(work/'BUILD_REGISTERED.json'),tree_source_sha256={str(p.relative_to(work/'tree_source')):sha(p) for p in (work/'tree_source').rglob('*') if p.is_file()},
        scope='compile only, no runtime promotion'),indent=2)+'\n')
    print('PASS compiled four labeled adapters; no GPU workload launched')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('work','upstream','cuda','cuvs-site','dlpack-include'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
