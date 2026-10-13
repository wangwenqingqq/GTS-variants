"""Delivery entry point; reject optimized Python before importing frozen checks."""
import argparse
import sys
from pathlib import Path


if sys.flags.optimize:
    raise SystemExit('Python optimized mode is unsupported: required checks must run')

p = argparse.ArgumentParser()
p.add_argument('--binary', type=Path, help='Small fixtures only; no population run')
for key in ('data', 'gate3', 'work'):
    p.add_argument('--' + key, type=Path)
a = p.parse_args()
if a.binary:
    if any((a.data, a.gate3, a.work)):
        p.error('--binary cannot be combined with population arguments')
    from test_gate4 import check
    check(a.binary)
else:
    if not all((a.data, a.gate3, a.work)):
        p.error('population replay requires --data, --gate3 and --work')
    from replay import population
    population(a)
