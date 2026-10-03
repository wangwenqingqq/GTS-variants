#!/usr/bin/env python3
"""Query-only NSYS diagnostics; profiler timings are not public latency."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT/'delivery/run_locked.py' if (ROOT/'delivery/run_locked.py').is_file() else ROOT/'run_locked.py'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python', required=True)
    p.add_argument('--data-root', required=True, type=Path)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    assert 'FORMAL COMPLETE' in (ROOT/'formal_console.log').read_text()
    # Fixed diagnostic subset, not another quality-tuning set.
    reference = json.loads((ROOT/'oracle_GIST_final256.json').read_text())
    reference['records'] = reference['records'][:32]; reference['Q'] = 32
    ref_path = ROOT/'oracle_GIST_profile32.json'
    ref_path.write_text(json.dumps(reference)+'\n')
    qids = ROOT/'fixtures/GIST_profile32.qid'
    qids.write_text('32\n'+''.join(f'{r["qid"]}\n' for r in reference['records']))
    data = a.data_root/'GIST/1000000/fixtures/data.f32bin'
    for b in (1, 32):
        configs = ROOT/f'profile_b{b}_configs.json'
        configs.write_text(json.dumps([{'K': 8, 'B': b, 'nlist': 1024, 'nprobe': 1024}])+'\n')
        for method in ('gts', 'ivf'):
            label = f'profile_{method}_GIST_k8_b{b}_v2'
            trace = ROOT/label
            if method == 'gts':
                command = [ROOT/'gts_bench', data, qids, 8, b, 1, ROOT/'GIST.index', label, 2]
            else:
                command = [a.python, ROOT/'native_ivf.py', 'faiss', '--data', data,
                           '--qids', qids, '--reference', ref_path, '--configs', configs,
                           '--out', ROOT/f'{label}.json']
            subprocess.run([sys.executable, RUNNER, '--gpu', a.gpu,
                            '--output', ROOT/'runs'/label, '--', '/usr/local/bin/nsys', 'profile',
                            '--trace=cuda,nvtx,osrt', '--sample=none', '--cpuctxsw=none',
                            '--capture-range=nvtx', '--nvtx-capture=formal.query_pass',
                            '--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
                            '--capture-range-end=stop', '--force-overwrite=false',
                            '-o', trace, *map(str, command)], check=True)
            subprocess.run(['nsys', 'export', '--type=sqlite', '--output', f'{trace}.sqlite',
                            f'{trace}.nsys-rep'], check=True)
    print('QUERY PROFILES COMPLETE', flush=True)


if __name__ == '__main__':
    main()
