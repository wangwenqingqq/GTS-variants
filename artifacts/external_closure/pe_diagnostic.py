#!/usr/bin/env python3
"""Build a one-process attribution probe, never a performance candidate."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,shutil,subprocess
from pathlib import Path
from common import outside_repo
from prepare_static import once,HERE
from qualify import cpu

def prepare(parent,work):
    work=outside_repo(work);assert not work.exists();work.mkdir(parents=True)
    proof=json.loads((HERE.parent/'build_distance_tiles/evidence/QUALIFICATION.json').read_text())
    assert cpu.sha(parent/'PREPARED.json')==proof['source']['prepared_sha256']
    sources=json.loads((parent/'PREPARED.json').read_text())['sources']
    assert all(cpu.sha(parent/'source'/k)==v for k,v in sources.items())
    shutil.copytree(parent/'source',work/'source');p=work/'source/include/parallel_range.cuh';s=p.read_text()
    s=once(s,'namespace rex {','namespace rex {\n__managed__ unsigned long long radius_upper_calls=0;')
    s=once(s,'if(!threadIdx.x)rupper=target::radius_upper(radius,v.d);','if(!threadIdx.x){atomicAdd(&radius_upper_calls,1ULL);rupper=target::radius_upper(radius,v.d);}')
    p.write_text(s);p=work/'source/src/main.cu';s=p.read_text()
    s=once(s,'    u10.begin();','    rex::radius_upper_calls=0;u10_ck(cudaDeviceSynchronize());\n    u10.begin();')
    s=once(s,'    u10.write(output);','    {std::ofstream counts(output+".cost.json");counts<<"{\\\"radius_upper_calls\\\":"<<rex::radius_upper_calls<<",\\\"d\\\":"<<input.d<<",\\\"distinct_parameter_pairs\\\":1}\\n";}\n    u10.write(output);')
    p.write_text(s);(work/'bin').mkdir()
    cmd=json.loads((parent/'BUILD.json').read_text())['command'];cmd=[v.replace(str(parent/'source'),str(work/'source')).replace(str(parent/'bin/target'),str(work/'bin/target')) for v in cmd]
    cpu.save(work/'REGISTERED.json',dict(scope='diagnostic only: one extra atomic per active parent CTA; durations perturbed, no performance promotion',command=cmd,parent_prepared_sha256=cpu.sha(parent/'PREPARED.json'),sources={str(p.relative_to(work/'source')):cpu.sha(p) for p in (work/'source').rglob('*') if p.is_file()}))
    with (work/'compile.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=f,check=True)
    cpu.save(work/'BUILD.json',dict(binary_sha256=cpu.sha(work/'bin/target')))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('parent','work'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.parent.resolve(),a.work.resolve())
