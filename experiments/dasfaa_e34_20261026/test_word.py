"""CPU-only smoke checks for the unfrozen Word preparation and audit path."""
import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from audit_word import audit, distance, load
from prepare_words import isolation, main as prepare, pack, read_source


def raises(kind, fn):
    try:
        fn()
    except kind:
        return
    raise AssertionError(f'expected {kind.__name__}')


def oracle_bytes(base, queries):
    rows = [sorted((distance(q, x), i) for i, x in enumerate(base))[:10] for q in queries]
    ids = np.array([[i for d, i in row] for row in rows], dtype='<i4')
    ds = np.array([[d for d, i in row] for row in rows], dtype='<f8')
    return ids, ds


def test():
    assert distance(b'kitten', b'sitting') == 3
    assert distance(b'', b'abc') == 3
    assert distance(b'a' * 108, b'b' * 108) == 108
    assert isolation(['a', 'b', 'a'], ['a', 'c'], 1) == {
        'isolated': False, 'indexed_rows_equal_to_query': 1,
        'query_rows_equal_to_index': 1, 'shared_distinct_values': 1}
    assert isolation(['a', 'b'], ['c'], 2)['isolated']
    compiler = shutil.which('c++')
    assert compiler, 'CPU oracle smoke requires c++'
    rng = random.Random(20261026)
    base = [b''] + [bytes(rng.choices(b'acgtXYZ019', k=i)) for i in range(1, 29)] + [b'x' * 108]
    base[3] = b'\x8e\xff\x00'
    queries = [b'', b'QQQQ', b'\x8e\xff', b'acgt', b'A' * 107, base[7]]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        pack(root / 'x', base)
        pack(root / 'q', queries)
        lengths, text = load(root / 'x')
        assert int(max(lengths)) == 108 and text.shape == (30, 109)
        binary = root / 'edit_oracle'
        subprocess.run([compiler, '-O2', '-std=c++17', str(Path(__file__).with_name('edit_oracle.cpp')), '-o', str(binary)], check=True)
        subprocess.run([str(binary), str(root / 'x'), str(root / 'q'), str(len(base)), str(root / 'o')], check=True)
        oi = np.fromfile(root / 'o', dtype='<i4', count=len(queries) * 10).reshape(-1, 10)
        od = np.fromfile(root / 'o', dtype='<f8', offset=len(queries) * 10 * 4).reshape(-1, 10)
        reference_ids, reference_ds = oracle_bytes(base, queries)
        assert np.array_equal(od, reference_ds)
        for qi in range(len(queries)):
            assert len(set(oi[qi])) == 10
            assert all(distance(queries[qi], base[i]) == d for i, d in zip(oi[qi], od[qi]))
        case = {'N': len(base), 'base': 'x', 'query': 'q', 'oracle': 'o'}
        oi[:, :8].copy().tofile(root / 'good.ids')
        assert audit(root, case, root / 'good')['correct']
        bad = oi[:, :8].copy(); bad[0, 0] = len(base) - 1
        bad.tofile(root / 'rank.ids')
        assert audit(root, case, root / 'rank')['distance_failures'] == 1
        bad = oi[:, :8].copy(); bad[0, 0] = -1
        bad.tofile(root / 'invalid.ids')
        assert audit(root, case, root / 'invalid')['invalid_ids'] == 1
        bad = oi[:, :8].copy(); bad[0, 0] = bad[0, 1]
        bad.tofile(root / 'dup.ids')
        assert audit(root, case, root / 'dup')['duplicate_rows'] == 1
        (root / 'short.ids').write_bytes(b'1234')
        raises(ValueError, lambda: audit(root, case, root / 'short'))
        pack(root / 'tie_x', [b'a', b'b', b'c', b'd', b'e', b'f', b'g', b'h', b'i', b'j', b'k', b'l'])
        pack(root / 'tie_q', [b''] * 1000)
        ti = np.tile(np.arange(10, dtype='<i4'), (1000, 1)); td = np.ones((1000, 10), dtype='<f8')
        (root / 'tie_o').write_bytes(ti.tobytes() + td.tobytes())
        np.tile(np.arange(4, 12, dtype='<i4'), (1024, 1)).tofile(root / 'tie.ids')
        tie_case = {'N': 12, 'base': 'tie_x', 'query': 'tie_q', 'oracle': 'tie_o'}
        assert audit(root, tie_case, root / 'tie', expected_rows=1024)['correct']
        raises(ValueError, lambda: audit(root, tie_case, root / 'tie', expected_rows=1000))
        raises(ValueError, lambda: load(root / 'x', 31))
        raises(ValueError, lambda: pack(root / 'too_long', [b'a' * 109]))
        truncated = root / 'truncated'; truncated.write_bytes((root / 'x').read_bytes()[:-1])
        raises(ValueError, lambda: load(truncated))
        malformed = root / 'malformed'; raw = bytearray((root / 'x').read_bytes()); raw[8:12] = np.array([109], dtype='<i4').tobytes(); malformed.write_bytes(raw)
        raises(ValueError, lambda: load(malformed))
        raw_source = root / 'source.raw'
        raw_source.write_bytes(b'109 4 6\n\x8e\xff\nabc\r\nleft\x00ignored\n\n')
        header, raw_words, metadata = read_source(raw_source)
        assert header == [109, 4, 6]
        assert raw_words == [b'\x8e\xff', b'abc\r', b'left', b'']
        assert metadata['source_rows_with_non_ascii'] == 1
        assert metadata['source_rows_with_embedded_nul'] == 1
        source = root / 'source.txt'; words = ['same'] + [f'w{i}' for i in range(1010)]
        source.write_text(f'1 {len(words)}\n' + '\n'.join(words) + '\n')
        prepared = root / 'prepared'; prepared.mkdir()
        prepare(prepared, source)
        manifest = json.loads((prepared / 'WORD_MANIFEST.json').read_text())
        assert manifest['seed'] == 20261026 and manifest['available_base_rows'] == 11
        assert all(c['state'].startswith('infeasible:') for c in manifest['cases'])
        order = np.load(prepared / 'data/word_permutation.npy')
        assert np.array_equal(order, np.random.default_rng(20261026).permutation(len(words)))
        raises(FileExistsError, lambda: prepare(prepared, source))
    print('PASS CPU Word oracle, full-table audit, ties, Q1024 wrapping, bad IDs, collisions, lengths and frozen split')


if __name__ == '__main__':
    test()
