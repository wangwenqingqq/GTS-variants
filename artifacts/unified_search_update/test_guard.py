#!/usr/bin/env python3
"""CPU-only failure-injection checks for the actual portable GPU receipt validator."""
import copy
from pathlib import Path
import tempfile

from run import sha, save, validate_guard


def main():
    if not __debug__: raise RuntimeError('Python -O disables checks')
    with tempfile.TemporaryDirectory(prefix='gts-guard-test-') as directory:
        root = Path(directory); binary = root / 'target'; binary.write_bytes(b'fixed test executable')
        good = {'receipt.json': dict(runtime_valid=True, exit_code=0, stop_reason=None, binary_sha256=sha(binary)),
                'before.json': dict(apps=[]), 'after.json': dict(apps=[]), 'checks.json': [dict(foreign=[])]}
        changes = [('receipt.json', 'runtime_valid', False), ('receipt.json', 'exit_code', 77),
                   ('receipt.json', 'stop_reason', 'foreign compute'), ('receipt.json', 'binary_sha256', '0'*64),
                   ('before.json', 'apps', [123]), ('after.json', 'apps', [123]), ('checks.json', 'foreign', [123])]
        for change in [None, *changes]:
            value = copy.deepcopy(good)
            if change:
                name, key, field = change
                if name == 'checks.json': value[name][0][key] = field
                else: value[name][key] = field
            for name, data in value.items(): save(root/name, data)
            try: validate_guard(root, binary)
            except AssertionError: assert change is not None
            else: assert change is None, ('invalid receipt accepted', change)
        for name, value in good.items(): save(root/name, value)
        binary.write_bytes(b'changed target')
        try: validate_guard(root, binary)
        except AssertionError: pass
        else: raise AssertionError('changed executable accepted')
    print('CPU_GUARD_PASS: valid control and8 rejected mutations')


if __name__ == '__main__': main()
