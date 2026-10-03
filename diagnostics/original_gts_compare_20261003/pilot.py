#!/usr/bin/env python3
"""Recheck a pinned original binary using existing locked runner and oracle."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-root', required=True, type=Path)
    p.add_argument('--data-root', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--python', required=True)
    p.add_argument('--gpu', required=True)
    p.add_argument('--numa', required=True, type=int)
    a = p.parse_args()
    contract = json.loads((Path(__file__).parent/'CONTRACT.json').read_text())
    r = a.reference_root
    assert sha(r/'gts_bench') == contract['binary_sha256']
    for name, digest in contract['reused_harness_sha256'].items():
        assert sha(r/name) == digest, name
    # This campaign does not rebuild or change either preserved source tree.
    pins = json.loads((r/'gts/SOURCE_PINS.json').read_text())
    for kind in ('original', 'adapted'):
        for name, digest in pins[kind].items():
            assert sha(r/'gts'/kind/name) == digest, (kind, name)
    a.out.mkdir(parents=True, exist_ok=False)
    pre = {'binary_sha256': sha(r/'gts_bench'), 'data': {}, 'cache': {}}
    rows = []
    for dataset in ('GIST', 'Deep'):
        data = a.data_root/dataset/'1000000/fixtures/data.f32bin'
        pre['data'][dataset] = sha(data)
        assert pre['data'][dataset] == contract['data_sha256'][dataset], dataset
        pre['cache'][dataset] = sha(r/f'{dataset}.index')
        reference = json.loads((r/f'oracle_{dataset}_final256.json').read_text())
        reference['records'] = reference['records'][:32]
        reference['Q'] = 32
        original_qids = list(map(int, (r/'fixtures'/f'{dataset}_final256.qid').read_text().split()))
        assert original_qids[0] == 256
        assert original_qids[1:33] == [x['qid'] for x in reference['records']]
        ref = a.out/f'oracle_{dataset}_32.json'
        ref.write_text(json.dumps(reference)+'\n')
        qids = a.out/f'{dataset}_32.qid'
        qids.write_text('32\n'+''.join(f'{x["qid"]}\n' for x in reference['records']))
        for b in contract['B']:
            label = f'baseline_{dataset}_k8_b{b}'
            output = a.out/label
            command = [r/'gts_bench', data, qids, 8, b, 1, r/f'{dataset}.index', output, 2]
            subprocess.run(list(map(str, [sys.executable, r/'delivery/run_locked.py', '--gpu', a.gpu,
                            '--numa-node', a.numa, '--output', a.out/'runs'/label,
                            '--', *command])), check=True)
            target = a.out/f'{label}.quality.json'
            subprocess.run([a.python, r/'verify_outputs.py', 'check-gts', '--data', data,
                            '--reference', ref, '--result', str(output)+'.bin', '--out', target],
                           check=True, env={**os.environ, 'CUDA_VISIBLE_DEVICES': a.gpu})
            quality = json.loads(target.read_text())
            assert quality['recall_tie_aware'] == 1 and quality['distance_tolerance_pass']
            times = list(csv.DictReader(Path(str(output)+'.csv').open()))
            assert len(times) == 1 and times[0]['sample'] == '0'
            rows.append({'dataset': dataset, 'K': 8, 'B': b, 'Q': 32,
                         'total_ms': float(times[0]['total_ms']), 'quality': quality,
                         'output_sha256': sha(Path(str(output)+'.bin'))})
            print('PASS', label, times[0]['total_ms'], flush=True)
    assert sha(r/'gts_bench') == pre['binary_sha256']
    for dataset in ('GIST', 'Deep'):
        assert sha(a.data_root/dataset/'1000000/fixtures/data.f32bin') == pre['data'][dataset]
        assert sha(r/f'{dataset}.index') == pre['cache'][dataset]
    (a.out/'SUMMARY.json').write_text(json.dumps({'status': 'baseline_pilot_passed',
        'scope': contract['claim_boundary'], 'pre_post_identity': pre, 'rows': rows}, indent=2)+'\n')
    print('BASELINE PILOT COMPLETE', flush=True)


if __name__ == '__main__':
    main()
