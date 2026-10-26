"""Build fresh, approved P/G copies; never alter archives or legacy binaries.

Remote usage (itself also launched through guard):
  python3 build_patched.py ROOT --source-p ARCHIVE_P --source-g ARCHIVE_G \
      --patches PATCH_DIRECTORY
Outputs ROOT/builds/corrected_<UTCstamp>/BUILD_MANIFEST.json and bin/{tree,
 tree_count,g_tree}. The vector harness disables legacy index caches entirely.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from adapt import ORIGINAL_SHA, corrected, sha

GUARD = os.environ.get('GTSPP_GUARD', 'guard.py')


def guarded(cmd, folder, label):
    log = folder / 'logs' / (label + '.guard.jsonl')
    wrapped = [sys.executable, GUARD, '--log', str(log), '--rss-max-gb', '16',
               '--mem-available-min-gb', '48', '--timeout-s', '240', '--', *map(str, cmd)]
    with (folder / 'logs' / (label + '.log')).open('x') as output:
        result = subprocess.run(wrapped, cwd=folder, stdout=output, stderr=subprocess.STDOUT,
                                env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
    if result.returncode:
        (folder / 'BUILD_FAILED.json').write_text(json.dumps({'label': label, 'exit_code': result.returncode, 'command': wrapped}, indent=2)+'\n')
        raise SystemExit(result.returncode)
    return wrapped


def prepare_source(source, destination, patch, arm, p_header=None):
    source = Path(source)
    destination.mkdir()
    (destination / 'include').mkdir()
    files = sorted((source / 'include').glob('*.cuh'))
    assert files, f'no archived CUDA headers: {source}'
    for path in files:
        shutil.copyfile(path, destination / 'include' / path.name)
    header = Path(p_header) if arm == 'P' and p_header else source / 'include/search_v2.cuh'
    original = header.read_bytes()
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA[arm], f'wrong {arm} original'
    pure = corrected(original, patch.read_text(), arm)
    final = corrected(original, patch.read_text(), arm, instrument=arm == 'P')
    (destination / 'include/search_v2.cuh').write_text(final)
    return {
        'archive': str(source), 'archive_search': str(header), 'archive_search_sha256': sha(header),
        'patch': str(patch), 'patch_sha256': sha(patch),
        'corrected_search_sha256': hashlib.sha256(pure.encode()).hexdigest(),
        'compiled_search_sha256': hashlib.sha256(final.encode()).hexdigest(),
        'adaptation': 'approved patch plus WORK macros only' if arm == 'P' else 'approved patch plus output-only leaf-slot-to-ID observer',
        'archive_headers': {p.name: sha(p) for p in files},
        'diff': ''.join(difflib.unified_diff(original.decode().splitlines(True), final.splitlines(True), fromfile='archive/'+arm, tofile='compiled/'+arm)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('--source-p', required=True, type=Path)
    ap.add_argument('--source-g', required=True, type=Path)
    ap.add_argument('--patches', required=True, type=Path)
    ap.add_argument('--p-header', type=Path)
    ap.add_argument('--prepare-only', action='store_true', help='no subprocesses; local source tests only')
    a = ap.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    folder = a.root.resolve() / 'builds' / ('corrected_'+stamp)
    folder.mkdir(parents=True)
    (folder / 'bin').mkdir(); (folder / 'logs').mkdir()
    here = Path(__file__).resolve().parent
    shutil.copyfile(here / 'tree_bench.cu', folder / 'tree_bench.cu')
    sources = {arm: prepare_source(source, folder / ('source_'+arm.lower()), a.patches.resolve() / patch, arm, a.p_header)
               for arm, source, patch in [('P', a.source_p, 'gtspp_search_v2_fixes.patch'),
                                           ('G', a.source_g, 'gts_original_search_v2_fixes.patch')]}
    for arm, record in sources.items():
        (folder / (arm+'_source.diff')).write_text(record.pop('diff'))
    compiled = {str(p.relative_to(folder)): sha(p) for p in folder.rglob('*.cuh')}
    compiled['tree_bench.cu'] = sha(folder / 'tree_bench.cu')
    build_id = hashlib.sha256(json.dumps(compiled, sort_keys=True).encode()).hexdigest()
    record = {'time_utc': stamp, 'build_id': build_id, 'sources': sources,
              'compiled_sources': compiled, 'cache_policy': 'disabled; every fresh process rebuilds outside query timer',
              'G_height_policy': 'h=1+ceil(log_10(N/20)), implemented by integer capacity loop; assigned native MAX_H before indexConstru; verify leaf max<=20, ID permutation, and coverage=N before search',
              'workspace': {'P': 'native capped 4GiB', 'G': 'native half available GPU memory, unchanged; query refused if signed int32 slot count would overflow'},
              'G_launch_authorized': False,
              'G_blocker': {'state': 'static/inferred, not a measured runtime failure',
                            'source': 'search_v2.cuh: int size_a; avail=avail/2; size_a=avail/sizeof(double)',
                            'reason': 'native signed int32 workspace slot assignment is unsafe on a near-empty 96GiB device',
                            'conservative_free_gpu_bytes_bound': 2 * 8 * (2**31-1),
                            'decision': 'compile for provenance only; do not launch G, widen addressing, cap workspace, or manufacture GPU pressure'},
              'builder_sha256': sha(__file__), 'adapter_sha256': sha(here / 'adapt.py'), 'build_commands': {}, 'binaries': {}}
    (folder / 'SOURCE_MANIFEST.json').write_text(json.dumps(record, indent=2)+'\n')
    print(folder, flush=True)
    if a.prepare_only:
        return
    record['toolkit_command'] = guarded(['/usr/local/cuda/bin/nvcc', '--version'], folder, 'toolkit_version')
    for name, defines in [('tree', []), ('tree_count', ['-DINSTRUMENT=1']), ('g_tree', ['-DARM_G=1'])]:
        cmd = ['/usr/local/cuda/bin/nvcc', '-O3', '-std=c++17', '-arch=sm_120',
               '-I', str(folder), '-DBUILD_ID="'+build_id+'"', *defines,
               str(folder / 'tree_bench.cu'), '-o', str(folder / 'bin' / name), '-lcurand']
        record['build_commands'][name] = guarded(cmd, folder, 'compile_'+name)
        record['binaries'][name] = {'path': str(folder / 'bin' / name), 'sha256': sha(folder / 'bin' / name)}
        (folder / 'BUILD_MANIFEST.json').write_text(json.dumps(record, indent=2)+'\n')
    (folder / 'BUILD_COMPLETE.json').write_text(json.dumps({'build_id': build_id, 'binaries': record['binaries']}, indent=2)+'\n')


if __name__ == '__main__':
    main()
