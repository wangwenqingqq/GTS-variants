#!/usr/bin/env python3
"""Independently check Tloc held-out result counts against direct CPU L2."""
import csv
import json
from pathlib import Path
import sys

import numpy as np


def main(root: Path) -> None:
    case = root / 'data/Tloc/1000000'
    data_path = case / 'fixtures/data.f32bin'
    dim, n, metric = np.fromfile(data_path, dtype=np.int32, count=3)
    assert (dim, n, metric) == (2, 1000000, 2)
    data = np.memmap(data_path, dtype=np.float32, mode='r', offset=12,
                     shape=(n, dim))
    qids = [int(q) for q in (case / 'fixtures/queries.qid').read_text().split()]
    assert qids[0] == 24 and len(qids) == 25
    kinds = ('half', 'normal', 'double', 'quad', 'oct',
             'x16', 'x32', 'x64', 'all')
    references = {}
    for kind in kinds:
        receipt = json.loads((case / 'runs' / f'{kind}_f_0/receipt.json').read_text())
        rows = list(csv.DictReader((case / 'runs' / f'{kind}_f_0/result.csv').open()))
        references[kind] = (np.float32(receipt['radius']),
                            {int(row['qid']): int(row['count']) for row in rows})
    checks = 0
    differences = []
    for qid in qids[1:]:
        # Mirror the kernel's float32 coordinate arithmetic and final square
        # root. Comparing squared values with radius squared changes a few
        # boundary decisions because the GPU compares rounded L2 to radius.
        dx = data[:, 0] - data[qid, 0]
        dy = data[:, 1] - data[qid, 1]
        distance = np.sqrt(dx * dx + dy * dy)
        for kind, (radius, expected) in references.items():
            count = int(np.count_nonzero(distance <= radius))
            checks += 1
            if count != expected[qid]:
                differences.append({'qid': qid, 'radius': kind,
                                    'cpu': count, 'gpu_flat': expected[qid]})
    result = {'dataset': 'Tloc', 'queries': 24, 'radii': list(kinds),
              'checks': checks, 'mismatches': differences}
    print(json.dumps(result, indent=2))
    if differences:
        raise SystemExit(1)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
