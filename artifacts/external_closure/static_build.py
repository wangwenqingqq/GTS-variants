#!/usr/bin/env python3
"""Compile only Host-adapter changes; preserve the qualified parent and kernels."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare_static import prepare,HERE
from qualify import cpu

def main(a):
    prepare(a.parent,a.work);source=a.work/'source';(a.work/'bin').mkdir()
    original=json.loads((a.parent/'BUILD.json').read_text())['command']
    command=[v.replace(str(a.parent/'source'),str(source)).replace(str(a.parent/'bin/target'),str(a.work/'bin/target')) for v in original]
    old=json.loads((a.range_build/'BUILD_REGISTERED.json').read_text());range_cmd=old['commands']['range_service']
    range_cmd=[str(HERE/'static_range.cu') if v.endswith('/range_service.cu') else str(a.work/'bin/range_static') if v==str(a.range_build/'range_service') else v for v in range_cmd]
    libs=old['library_search_dirs'];env=dict(os.environ,LD_LIBRARY_PATH=':'.join(libs+['/usr/local/cuda-13.1/lib64']))
    sources={str(p.relative_to(HERE)):cpu.sha(p) for p in HERE.iterdir() if p.is_file()}
    cpu.save(a.work/'BUILD_REGISTERED.json',dict(commands={'target':command,'range_static':range_cmd},source_sha256=sources,prepared_sha256=cpu.sha(a.work/'PREPARED.json'),parent_binary_sha256=cpu.sha(a.parent/'bin/target'),library_search_dirs=libs))
    for name,cmd in [('target',command),('range_static',range_cmd)]:
        with (a.work/(name+'.compile.log')).open('x') as log:subprocess.run(cmd,stdout=log,stderr=log,check=True,env=env)
    cpu.save(a.work/'BUILD.json',dict(binaries={n:cpu.sha(a.work/'bin'/n) for n in ('target','range_static')},registration_sha256=cpu.sha(a.work/'BUILD_REGISTERED.json')))
    print('PASS compiled Host adapters; no GPU runtime claimed')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('parent','range-build','work'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
