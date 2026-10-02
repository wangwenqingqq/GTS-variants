#!/usr/bin/env python3
"""Freeze distinct database query IDs without materializing a million-ID pool."""
import argparse
import hashlib
import json
from pathlib import Path
import random


def read_qids(path):
    values = list(map(int, path.read_text().split()))
    assert values and values[0] == len(values) - 1
    assert len(set(values[1:])) == values[0]
    return values[1:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    p.add_argument('--n', type=int, required=True)
    p.add_argument('--count', type=int, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--exclude', type=Path, nargs='+', required=True)
    a = p.parse_args()
    assert not a.output.exists() and a.n > a.count > 0
    forbidden = {qid for path in a.exclude for qid in read_qids(path)}
    assert all(0 <= qid < a.n for qid in forbidden)
    rng = random.Random(a.seed)
    chosen = []
    while len(chosen) < a.count:
        qid = rng.randrange(a.n)
        if qid not in forbidden:
            chosen.append(qid)
            forbidden.add(qid)
    a.output.write_text(str(len(chosen)) + '\n' + ''.join(f'{qid}\n' for qid in chosen))
    print(json.dumps({'count':len(chosen),'seed':a.seed,
                      'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),
                      'first_ids':chosen[:8]}))


if __name__ == '__main__':
    main()
