"""Small CPU-only fixtures for approved isolation, trace semantics and case format."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_inputs import rowkey
from prepare_inputs_v3 import (SEED, isolated_indices, make_trace, materialize_case,
                              prepare_dataset, skew_arrivals, write_rows)


class PreparedInputTests(unittest.TestCase):
    def test_corpus_query_duplicates_all_leave_before_split(self):
        x = np.asarray([[i, i + 1] for i in range(40)], dtype='<f4')
        chosen = np.random.Generator(np.random.PCG64(SEED)).choice(40, 2, replace=False)
        other = next(i for i in range(40) if i not in chosen)
        x[other] = x[chosen[0]]
        split = isolated_indices(x, None, 'tloc', query_count=2)
        self.assertEqual(split['status'], 'input-pass')
        self.assertEqual(len(split['excluded']), 3)
        self.assertEqual(split['query_rows'].tolist(), chosen.tolist())
        self.assertEqual(len(split['arrival']), 37 // 10)
        self.assertEqual(len(set(split['base']) & set(split['arrival'])), 0)
        keys = {rowkey(x[i]) for i in chosen}
        self.assertFalse(any(rowkey(x[i]) in keys for i in
                             np.concatenate((split['base'], split['arrival']))))
        again = isolated_indices(x, None, 'tloc', query_count=2)
        np.testing.assert_array_equal(split['base'], again['base'])

    def test_ann_overlap_is_blocked_without_explicit_approval(self):
        x = np.asarray([[0., -0.], [1., 2.], [3., 4.]], dtype='<f4')
        query = np.asarray([[-0., 0.]], dtype='<f4')
        blocked = isolated_indices(x, query, 'gist')
        self.assertEqual(blocked['status'], 'input-contract-blocked')
        self.assertEqual(blocked['excluded'].tolist(), [0])
        with self.assertRaisesRegex(ValueError, 'amendment'):
            isolated_indices(x, query, 'gist', exclude_ann_overlap=True)
        approved = isolated_indices(x, query, 'gist', exclude_ann_overlap=True,
                                    amendment='explicit-user-decision')
        self.assertEqual(approved['status'], 'input-pass')
        self.assertEqual(set(approved['base']), {1, 2})

    def test_trace_exact_counts_fresh_ids_and_active_snapshots(self):
        events = make_trace(100, 80, 3, 100, '4:4:2', 8)
        active = set(range(100))
        seen = active.copy()
        counts = dict(insert=0, delete=0, query=0)
        version = 0
        for event in events:
            counts[event['op']] += 1
            if event['op'] == 'insert':
                self.assertNotIn(event['id'], seen)
                self.assertEqual(event['id'], 100 + event['vector_offset'])
                seen.add(event['id'])
                active.add(event['id'])
                version += 1
            elif event['op'] == 'delete':
                self.assertIn(event['id'], active)
                active.remove(event['id'])
                version += 1
            else:
                self.assertIn(event['query_id'], range(3))
                self.assertGreaterEqual(len(active), 8)
            self.assertEqual(event['required_snapshot'], version)
            self.assertEqual(event['active_size'], len(active))
        self.assertEqual(counts, dict(insert=40, delete=40, query=20))
        self.assertEqual(events, make_trace(100, 80, 3, 100, '4:4:2', 8))
        with self.assertRaisesRegex(ValueError, 'fresh_arrival_exhausted'):
            make_trace(100, 3, 3, 100, '4:4:2', 8)
        with self.assertRaisesRegex(ValueError, 'final_active_cardinality_below_k'):
            make_trace(20, 80, 3, 100, '1:8:1', 8)

    def test_skew_orders_do_not_change_arrival_membership(self):
        rows = np.asarray([4, 3, 1, 0, 2], dtype='<i8')
        words = ['zz', 'a', 'b', 'a', '\xe9']
        self.assertEqual(skew_arrivals('word', words, rows, rows).tolist(), [1, 3, 2, 4, 0])
        fp = np.asarray([[1, 1], [0, 0], [1, 0], [0, 1], [1, 1]], dtype='<f4')
        self.assertEqual(skew_arrivals('chembl', fp, rows, rows).tolist(), [1, 3, 2, 4, 0])
        xy = np.asarray([[0, 0], [1, 0], [0, 1], [1, 1], [0, 0]], dtype='<f4')
        self.assertEqual(skew_arrivals('tloc', xy, rows, rows).tolist(), [4, 0, 2, 1, 3])
        with self.assertRaisesRegex(ValueError, 'labels are required'):
            skew_arrivals('sift', xy, rows, rows)
        labels = np.asarray([2, 1, 2, 1, 0], dtype='<i4')
        self.assertEqual(skew_arrivals('sift', xy, rows, rows, labels).tolist(), [4, 3, 1, 0, 2])

    def test_latin1_and_existing_case_format_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'word').mkdir()
            words = ['w' + str(i) for i in range(100)]
            words[0] = '\xe9'
            with (root / 'word/word.txt').open('w', encoding='latin1') as stream:
                stream.write('108 100 6\n' + '\n'.join(words) + '\n')
            (root / 'word/word_qid.txt').write_text('2\n0\n1\n')
            prepared = root / 'prepared'
            manifest = prepare_dataset(root, prepared, 'word', lengths=(10,), query_count=2)
            self.assertEqual(manifest['N'], 98)
            self.assertEqual(len(manifest['loads']), 6)
            self.assertEqual({row['status'] for row in manifest['loads']}, {'prepared-not-evaluated'})
            ids = np.load(prepared / 'query_source_rows.npy')
            raw_query = np.load(prepared / 'query.npy')
            self.assertEqual([bytes(v) for v in raw_query], [words[i].encode('latin1') for i in ids])
            write_rows(root / 'latin1.npy', ['\xe9'], np.asarray([0]), 6, 108)
            self.assertEqual(bytes(np.load(root / 'latin1.npy')[0]), b'\xe9')
            output = root / 'case.bin'
            record = materialize_case(prepared, '10_442_random_k8', output)
            self.assertEqual(len(record['sha256']), 64)
            payload = output.read_bytes()
            self.assertEqual(payload[:8], b'E1CASE1\0')
            header = struct.unpack('<7i', payload[8:36])
            self.assertEqual(header, (6, 108, 89, 9, 2, 8, 10))
            self.assertEqual(len(payload), 36 + 100 * 109 + 10 * 20)
            events = np.frombuffer(payload, dtype='<i4', offset=36 + 100 * 109).reshape(-1, 5)
            self.assertEqual(np.bincount(events[:, 0]).tolist(), [4, 4, 2])
            with (prepared / 'base.npy').open('ab') as stream:
                stream.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                materialize_case(prepared, '10_442_random_k8', root / 'must_not_exist.bin')
            self.assertFalse((root / 'must_not_exist.bin').exists())

    def test_ann_blocked_manifest_preserves_entire_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'fbin').mkdir()
            for file, data in [('gist1m_base.fbin', [[0., 1.], [2., 3.]]),
                               ('gist1m_query.fbin', [[0., 1.]])]:
                with (root / 'fbin' / file).open('wb') as stream:
                    stream.write(struct.pack('<2i', len(data), 2))
                    stream.write(np.asarray(data, dtype='<f4').tobytes())
            manifest = prepare_dataset(root, root / 'prepared', 'gist')
            self.assertEqual(manifest['input_status'], 'input-contract-blocked')
            self.assertEqual(len(manifest['loads']), 24)
            self.assertFalse((root / 'prepared/base.npy').exists())
            self.assertEqual(json.loads((root / 'prepared/manifest.json').read_text()), manifest)


if __name__ == '__main__':
    unittest.main()
