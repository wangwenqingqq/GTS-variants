"""Reject altered delivery scalars even after their publish hashes are refreshed."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from check_public import HERE, ROOT, check, identity, load


def manifest(root):
    files = {str(p.relative_to(root)):identity(p) for p in sorted(root.rglob('*'))
             if p.is_file() and p != root/'evidence/PUBLISH_MANIFEST.json'}
    (root/'evidence/PUBLISH_MANIFEST.json').write_text(json.dumps(dict(files=files),indent=2,sort_keys=True)+'\n')


def run(out):
    assert not out.is_relative_to(ROOT.resolve()), 'Tests must write outside the source tree.'
    out.mkdir()
    check(HERE)
    cases = [
        ('aggregate', 'results/SUMMARY.json', lambda x: x['methods']['SAMPLED_PCA_MEDIAN']['metrics']['coordinate_proxy_bytes'].__setitem__('mean',0)),
        ('query_scalar', 'results/SAMPLED_PCA_MEDIAN.json', lambda x: x['rows'][0].__setitem__('retained_points',1)),
        ('verification_status', 'evidence/VERIFICATION.json', lambda x: x.__setitem__('passed',False)),
        ('runtime_priority', 'evidence/ENVIRONMENT.json', lambda x: x.__setitem__('nice',0)),
        ('source', 'geometry.cpp', None),
        ('extra_file', 'UNREGISTERED.txt', None),
    ]
    rejected = []
    for name,relative,mutate in cases:
        dest = out/name
        shutil.copytree(HERE,dest)
        f = dest/relative
        if mutate:
            x = load(f)
            mutate(x)
            f.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
        elif name == 'source':
            f.write_text(f.read_text()+'\n')
        else:
            f.write_text('unregistered\n')
        if name != 'extra_file':
            manifest(dest)
        try:
            check(dest)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('Altered evidence accepted: '+name)
    result = dict(passed=True,counterfactuals_rejected=rejected,
        refreshed_publish_hashes_for_first_five=True,
        checker_sha256=identity(HERE/'check_public.py')['sha256'],
        analyze_sha256=identity(HERE/'analyze.py')['sha256'],
        preserved_originals_unchanged=True,GPU_starts=0,heldout_query_evaluations=0)
    check(HERE)
    with (out/'TESTS.json').open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write('\n')
    print('DELIVERY_TEST_PASS:6 altered copies rejected;originals unchanged;0 GPU')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    run(a.out.resolve())
