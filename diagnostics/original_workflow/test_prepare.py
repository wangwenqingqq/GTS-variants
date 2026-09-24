#!/usr/bin/env python3
"""CPU-only checks for the source copy, deterministic probes and count parser."""
import argparse
import json
import tempfile
from pathlib import Path
import prepare

EXPECTED = {
    'query_only': [1, 1, 1], 'all_include': [1000], 'buffer_insert': [1, 2],
    'base_delete': [1000, 999], 'buffer_delete': [2, 1],
    'rebuild_no_prior_buffer_query': [11], 'rebuild_after_buffer_query': [2, 11, 11],
    'mixed_delete_rebuild': [1009], 'rebuild_then_delete': [11, 10],
}

def test(source):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = prepare.prepare(source, root/'a')
        b = prepare.prepare(source, root/'b')
        assert a == b
        for f, h in a['source_sha256'].items():
            assert prepare.sha(root/'a/source'/f) == h
        assert {k: v['expected_counts'] for k, v in a['cases'].items()} == EXPECTED
        for counts in EXPECTED.values():
            cost = 'Range search radius: 0\nResult num: \n'+' '.join(map(str, counts))+' \nTime of index construction: 0.1\n'
            assert prepare.validate(cost, counts)['pass']
            assert not prepare.validate(cost, counts+[0])['pass']
        for bad in ['Result num: \nTime: 1', 'Result num: 2 nan', 'Result num: -1']:
            assert not prepare.validate(bad, [1])['pass']
        try:
            prepare.prepare(source, root/'a')
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing artifacts must not be overwritten')
        p = root/'b/source/include/update.cuh'
        p.write_text(p.read_text()+'\n')
        try:
            prepare.prepare(root/'b/source', root/'drift')
        except AssertionError:
            assert not (root/'drift').exists()
        else:
            raise AssertionError('Source drift must be rejected before copying')
    assert prepare.oracle([[0], [1], [2]], [(2, 0)], 1) == [2]
    print('PASS: original eight-file pins, deterministic nine-case oracle, count parser, drift and overwrite guards; CPU-only')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    test(p.parse_args().source)
