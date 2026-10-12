"""Register deterministic pools, immutable dependencies and CPU references before GPU admission."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np

HERE = Path(__file__).resolve().parent
EXT = HERE.parent / 'external_closure'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    Path(p).write_text(json.dumps(v, indent=2)+'\n')

def sources():
    names = [HERE/n for n in ('CONTRACT.json', 'batch.cu', 'prepare.py', 'campaign.py', 'test_contract.py')]
    names += [EXT/n for n in ('range_service.cu', 'static_guard.py', 'common.py')]
    return {str(p.relative_to(HERE.parent)): sha(p) for p in names}

def score_function(library):
    f = ctypes.CDLL(str(library)).ordered_scores
    f.argtypes = [ctypes.c_void_p]*4+[ctypes.c_size_t, ctypes.c_int, ctypes.c_int]
    f.restype = ctypes.c_int
    def score(x, q):
        ids = np.arange(len(x), dtype=np.int64)
        q = np.ascontiguousarray(q, dtype=np.float32)
        out = np.empty(len(x), np.float64)
        assert x.dtype == np.float32 and x.flags.c_contiguous
        assert f(x.ctypes.data, ids.ctypes.data, q.ctypes.data, out.ctypes.data, len(x), 960, 4) == 0
        return out
    return score

def prepare(a):
    w = a.work.resolve()
    assert not w.exists() and HERE.parent not in w.parents
    w.mkdir(); (w/'build').mkdir(); (w/'reference').mkdir()
    prior_device=read(a.previous/'keeper/REGISTERED.json');assert prior_device['gpu']==a.gpu and prior_device['numa']==a.numa
    prior_uuid=read(a.previous/'keeper/guards/keeper_r1/before.json')['device'].split(',')[1].strip()
    current_uuid=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip();assert current_uuid==prior_uuid
    old = read(a.previous/'REGISTERED.json'); old_build = read(a.previous/'build/BUILD.json')
    data = Path(old['data']); assert sha(data) == old['data_sha256'] == 'f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'
    keeper = Path(old['keeper_binary']); assert sha(keeper) == old['keeper_sha256'] == '14f6d53ce1471c0f5f093d4266787ddf0a600fbd07e7d0434b77de568d599071'
    cpu = a.previous/'build/cpu_oracle.so'; assert sha(cpu) == old_build['binaries']['cpu']
    contract = read(HERE/'CONTRACT.json'); q32 = old['qids']; excluded = set(q32)|set(read(HERE.parent/'exact_scan_breakdown_20261011/CONTRACT.json')['calibration_qids'])
    rng = np.random.default_rng(contract['query_pool']['seed']); extension = []
    while len(extension) < 96:
        q = int(rng.integers(0, 1000000))
        if q not in excluded:
            extension.append(q); excluded.add(q)
    q128 = q32 + extension; assert len(set(q128)) == 128
    for name, ids in (('pool32.txt', q32), ('pool128.txt', q128)):
        (w/name).write_text('\n'.join(map(str, ids))+'\n')
    radius = float(np.array([0x3f34a3d8], np.uint32).view(np.float32)[0])
    (w/'native_requests.txt').write_text('40\n'+''.join(f'1 {q} {radius:.17g} 8\n' for q in q32[:8]+q32))
    build_parent = read(a.static_build/'BUILD_REGISTERED.json')
    command = [str(HERE/'batch.cu') if v.endswith('/static_range.cu') else str(w/'build/batch') if v.endswith('/bin/range_static') else v for v in build_parent['commands']['range_static']] + ['--ptxas-options=-v']
    env = {**os.environ, **old['environment']}
    registration = dict(before_GPU=True,gpu=a.gpu,numa=a.numa,GPU_UUID=current_uuid, contract_sha256=sha(HERE/'CONTRACT.json'), source_hashes=sources(), data=str(data), data_sha256=sha(data), keeper_binary=str(keeper), keeper_sha256=sha(keeper), cpu_library=str(cpu), cpu_sha256=sha(cpu), previous=str(a.previous), previous_READY_sha256=sha(a.previous/'READY.json'), expected_library_hashes=old_build['libraries'], q32=q32, q128=q128, seed=contract['query_pool']['seed'], pool_hashes={n:sha(w/n) for n in ('pool32.txt','pool128.txt')}, radius=radius, build_command=command, environment=old['environment'], registered_unix=time.time())
    save(w/'REGISTERED.json', registration)
    with (w/'build/compile.log').open('x') as f:
        subprocess.run(command, env=env, stdout=f, stderr=f, check=True)
    ldd = subprocess.check_output(['ldd', str(w/'build/batch')], env=env, text=True); assert 'not found' not in ldd
    (w/'build/ldd.txt').write_text(ldd)
    libraries = {}
    for line in ldd.splitlines():
        v = line.strip().split()
        if '=>' in v and len(v)>2 and v[2].startswith('/'):
            libraries[v[0]] = dict(sha256=sha(v[2]))
    assert libraries == old_build['libraries'], 'exact library/container drift'
    save(w/'build/BUILD.json', dict(binary_sha256=sha(w/'build/batch'), registration_sha256=sha(w/'REGISTERED.json'), libraries=libraries, unchanged_native_source_sha256=sha(EXT/'range_service.cu')))
    score = score_function(cpu)
    x = np.memmap(data, '<f4', mode='r', offset=12, shape=(1000000,960))
    probe = rng.random((513,960), dtype=np.float32); expected = np.zeros(513)
    for j in range(960):
        delta = probe[:,j].astype(float)-float(probe[1,j]); expected += delta*delta
    assert expected.tobytes() == score(probe,probe[1]).tobytes()
    previous_refs = read(a.previous/'PREPARED.json')['reference_hashes']['960']
    for q in q128:
        dest = w/'reference'/f'{q}.f64'
        if q in q32:
            src = a.previous/'reference/960'/f'{q}.f64'; assert sha(src) == previous_refs[src.name]; shutil.copyfile(src,dest)
        else:
            score(x,x[q]).tofile(dest)
        print('REFERENCE',q,flush=True)
    save(w/'READY.json',dict(passed=True,registration_sha256=sha(w/'REGISTERED.json'),contract_sha256=sha(HERE/'CONTRACT.json'),source_hashes=sources(),build_sha256=sha(w/'build/BUILD.json'),reference_hashes={p.name:sha(p) for p in (w/'reference').iterdir()},pool_hashes=registration['pool_hashes'],CPU_bit_conformance=True,query_pool_frozen_before_GPU=True))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('work','previous','static-build'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    prepare(p.parse_args())
