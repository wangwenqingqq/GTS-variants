#!/usr/bin/env python3
"""Prepare exactly three leaf mappings; reuse the pinned original adapter."""
import argparse, hashlib, importlib.util, json, shutil, difflib
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'native_knn_faiss_ivf_20261003'
GEOM=HERE.parent/'leaf_execution_geometry_20261011'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def leaf(s):
    start=s.index('__global__ void dataProcessKnn(')
    end=s.index('\n}\n',start)+3
    return start,end,s[start:end]
def variant(s,mode):
    if mode=='G0':return s
    if mode=='G1':return once(s,'dataProcessKnn<<<block_num, THREAD_NUM>>>','dataProcessKnn<<<block_num, 32>>>')
    assert mode=='G2'
    start,end,body=leaf(s)
    body=once(body,'int cur_level, int *size_list, int nnum_up)','int cur_level, int *size_list, int nnum_up, int leaf_tasks)')
    body=once(body,'\tint bid = blockIdx.x;\n\tint tid = threadIdx.x;',
        '\tint bid = 3 * blockIdx.x + threadIdx.x / 10;\n\tint tid = threadIdx.x % 10;\n'
        '\tif (threadIdx.x >= 30 || bid >= leaf_tasks) return;')
    body=once(body,'did += THREAD_NUM','did += 10')
    s=s[:start]+body+s[end:]
    s=once(s,'dataProcessKnn<<<block_num, THREAD_NUM>>>','dataProcessKnn<<<(block_num + 2) / 3, 32>>>')
    pos=s.index('dataProcessKnn<<<');end=s.index(';',pos)+1
    return s[:pos]+once(s[pos:end],'size_list, nnum_up);','size_list, nnum_up, lnum);')+s[end:]
def prepare(source,out):
    assert not out.exists();out.mkdir(parents=True)
    geometry=load('geometry_generator',GEOM/'prepare.py')
    geometry.prepare(source,out/'observed')
    adapted=out/'observed/shared/adapted'
    original=(adapted/'include/search_v2.cuh').read_text()
    driver=(BASE/'gts_bench.cu').read_text()
    driver=once(driver,'(batch==1||batch==32)','batch==1')
    driver=once(driver,'    std::ifstream cache(argv[6],std::ios::binary); bool cache_loaded=bool(cache);',
        '    std::ifstream cache(argv[6],std::ios::binary); bool cache_loaded=bool(cache);\n    require(cache_loaded,"reference index must exist");')
    (out/'bench.cu').write_text(driver)
    shutil.copy2(out/'observed/bench.cu',out/'count_bench.cu')
    for mode in ('G0','G1','G2'):
        s=variant(original,mode)
        for counted in (False,True):
            path=out/(mode+('_count' if counted else ''))
            shutil.copytree(adapted,path)
            (path/'include/search_v2.cuh').write_text(geometry.instrument(s) if counted else s)
            if counted:shutil.copy2(GEOM/'geometry.cuh',path/'include/geometry.cuh')
        (out/(mode+'.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),'G0',mode)))
    pins={'upstream':json.loads((out/'observed/shared/SOURCE_PINS.json').read_text()),
          'generator_sha256':sha(Path(__file__)),'adapter_sha256':sha(BASE/'prepare_gts.py'),
          'geometry_generator_sha256':sha(GEOM/'prepare.py'),
          'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
    (out/'SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
    return pins
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.source,a.out)
