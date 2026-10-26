"""Frozen Word split; exact-value overlaps are reported, never resampled away."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pack(path, strings, stride=109):
    strings = [x.encode('ascii') if isinstance(x, str) else x for x in strings]
    lengths = np.array([len(x) for x in strings], dtype='<i4')
    if not len(strings) or stride != 109 or max(lengths) >= stride:
        raise ValueError('strings must fit the frozen stride-109 DP arrays')
    chars = np.zeros((len(strings), stride), dtype=np.uint8)
    for row, s in zip(chars, strings):
        row[:len(s)] = np.frombuffer(s, dtype=np.uint8)
    with Path(path).open('xb') as f:
        np.array([len(strings), stride], dtype='<i4').tofile(f)
        lengths.tofile(f)
        chars.tofile(f)


def isolation(base, queries, n):
    query_values = set(queries)
    matches = query_values.intersection(base[:n])
    return {'isolated': not matches,
            'indexed_rows_equal_to_query': sum(x in matches for x in base[:n]),
            'query_rows_equal_to_index': sum(x in matches for x in queries),
            'shared_distinct_values': len(matches)}


def read_source(source):
    # Match the archived Linux loader: getline('\n') followed by strlen.
    raw = Path(source).read_bytes()
    lines = raw.split(b'\n')
    if raw.endswith(b'\n'):
        lines.pop()
    header = list(map(int, lines[0].decode('ascii').split()))
    original_rows = lines[1:]
    words = [row.split(b'\x00', 1)[0] for row in original_rows]
    metadata = {'source_parser': 'raw bytes; LF getline; object ends at first NUL (native strlen)',
                'source_rows_with_non_ascii': sum(any(c >= 128 for c in row) for row in original_rows),
                'source_rows_with_embedded_nul': sum(b'\x00' in row for row in original_rows)}
    return header, words, metadata


def main(root, source):
    root = Path(root)
    header, words, source_metadata = read_source(source)
    if len(header) < 2 or len(words) != header[1] or len(words) <= 1000:
        raise ValueError('Word source cardinality/header mismatch')
    if max(map(len, words)) >= 109:
        raise ValueError('Word source exceeds stride-109 length contract')
    order = np.random.default_rng(20261026).permutation(len(words))
    queries = [words[i] for i in order[:1000]]
    base = [words[i] for i in order[1000:]]
    data = root / 'data'
    data.mkdir(exist_ok=True)
    manifest = root / 'WORD_MANIFEST.json'
    outputs = [data / 'word_permutation.npy', data / 'word_query.strb', data / 'word_base.strb', manifest]
    if any(p.exists() for p in outputs):
        raise FileExistsError('preserve existing frozen Word artifacts; use a fresh directory')
    with outputs[0].open('xb') as f:
        np.save(f, order)
    pack(outputs[1], queries)
    pack(outputs[2], base)
    m = {'seed': 20261026, 'source_sha256': sha(source), 'source_rows': len(words),
         'query_rows': 1000, 'query_distinct_values': len(set(queries)),
         'available_base_rows': len(base), 'stride': 109,
         'maximum_length': max(map(len, words)), 'cases': [], **source_metadata}
    for n in [61000, 150000, 300000, 611000]:
        iso = isolation(base, queries, min(n, len(base)))
        state = ('infeasible: insufficient source rows after holdout' if n > len(base)
                 else 'feasible' if iso['isolated'] else 'blocked: query/index exact-value overlap')
        m['cases'].append({'family': 'word', 'N': n, 'D': 109, 'k': 8,
                           'Q': [1, 32, 1024], 'base': 'data/word_base.strb',
                           'query': 'data/word_query.strb', 'oracle': f'data/word_{n}.oracle',
                           'state': state, 'query_isolation': iso})
    m['files'] = {str(p.relative_to(root)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                  for p in outputs[:-1]}
    with manifest.open('x') as f:
        json.dump(m, f, indent=2)
        f.write('\n')
    print(json.dumps({'word_manifest': str(manifest), 'case_states': [c['state'] for c in m['cases']]}), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
