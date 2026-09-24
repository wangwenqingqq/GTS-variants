#!/usr/bin/env python3
"""Create a separate one-line rnum reset variant, preserving pinned original GTS."""
import argparse
import difflib
import json
import shutil
from pathlib import Path
from prepare import sha


def repair(root):
    manifest = json.loads((root/'manifest.json').read_text())
    original = root/'source'
    for name, expected in manifest['source_sha256'].items():
        assert sha(original/name) == expected, name
    out = root/'variants/rnum_reset'
    out.mkdir(parents=True, exist_ok=False)
    for name in manifest['source_sha256']:
        dest = out/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original/name, dest)
    target = out/'include/update.cuh'
    before = target.read_text()
    anchor = '\t\t\tif (in_size > 0)\n'
    assert before.count(anchor) == 1
    after = before.replace(anchor, '\t\t\trnum[0] = 0;\n'+anchor)
    target.write_text(after)
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='original/include/update.cuh',
                                      tofile='rnum_reset/include/update.cuh'))
    (out/'PATCH.diff').write_text(diff)
    record = {'variant': 'rnum_reset', 'source_commit': manifest['source_commit'],
              'change': 'Reset buffer result count before each optional buffered query.',
              'source_sha256': {name: sha(out/name) for name in manifest['source_sha256']},
              'original_source_sha256': manifest['source_sha256'],
              'patch_sha256': sha(out/'PATCH.diff'),
              'scope': 'Correctness repair only; no performance optimization or source overwrite.'}
    assert sum(record['source_sha256'][name] != h for name, h in manifest['source_sha256'].items()) == 1
    (out/'VARIANT.json').write_text(json.dumps(record, indent=2)+'\n')
    print(diff, end='')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    repair(p.parse_args().root.resolve())
