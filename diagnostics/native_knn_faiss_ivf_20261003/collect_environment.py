#!/usr/bin/env python3
"""Record software identities and post-collection source/cache checks."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import cupy
import faiss
import numpy

ROOT = Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(64*1024*1024):h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--faiss-root',type=Path,required=True)
    p.add_argument('--gpu',required=True)
    a = p.parse_args()
    pinned = json.loads((ROOT/'SOURCE_HASHES_formal.json').read_text())
    sources = {name:sha(ROOT/name) for name in pinned}
    assert all(sources[name] == value for name,value in pinned.items())
    preflight = json.loads((ROOT/'PREFLIGHT.json').read_text())
    for dataset in ('GIST','Deep'):
        assert sha(ROOT/f'{dataset}.index') == preflight['dataset_checks'][dataset]['index_cache_sha256']
        command=json.loads((ROOT/'runs'/f'formal_r1_gts_{dataset}_k8_b1/receipt.json').read_text())['command']
        assert sha(Path(command[4])) == preflight['dataset_checks'][dataset]['sha256']
    cache = (a.faiss_root/'faiss_build/CMakeCache.txt').read_text()
    options = {line.split(':')[0]:line.split('=',1)[1] for line in cache.splitlines()
               if '=' in line and line.split(':')[0] in {'CMAKE_BUILD_TYPE','CMAKE_CUDA_ARCHITECTURES',
               'CMAKE_CUDA_COMPILER','CMAKE_CXX_COMPILER','FAISS_ENABLE_CUVS','FAISS_ENABLE_GPU',
               'FAISS_ENABLE_PYTHON','BLA_VENDOR','FAISS_OPT_LEVEL'}}
    module = Path(faiss.__file__).parent
    result = {'verified_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'python':platform.python_version(),'numpy':numpy.__version__, 'cupy':cupy.__version__,
              'faiss':faiss.__version__, 'faiss_compile_options':faiss.get_compile_options(),
              'faiss_cmake':options, 'faiss_module_hashes':{p.name:sha(p) for p in module.glob('*.so')},
              'faiss_source_archive_sha256':sha(a.faiss_root/'faiss-v1.15.1.tar.gz'),
              'formal_sources_binary_data_and_cache_unchanged':True, 'formal_source_hashes':sources,
              'extension_sources':{name:sha(ROOT/name) for name in ('verify_outputs.py','run_control.py','profile_queries.py')},
              'extension_runner_sha256':sha(ROOT/'delivery/run_locked.py'),
              'selected_gpu_postflight':subprocess.check_output(['nvidia-smi','-i',a.gpu,
                   '--query-gpu=index,uuid,name,driver_version,clocks.current.sm,clocks.current.memory,power.limit',
                   '--format=csv'],text=True),
              'selected_gpu_apps':subprocess.check_output(['nvidia-smi','-i',a.gpu,
                   '--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True),
              'nsys':subprocess.check_output(['nsys','--version'],text=True)}
    assert not result['selected_gpu_apps'].strip()
    (ROOT/'SOFTWARE_POSTFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS formal sources/binary/cache unchanged, selected GPU clear, software hashes recorded')


if __name__ == '__main__':main()
