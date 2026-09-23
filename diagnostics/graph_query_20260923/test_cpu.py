#!/usr/bin/env python3
"""CPU-only regression checks; no GPU, SSH, or dataset access."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from analyze import analyze, clean, paired_interval, percentile
from oracle import check, digest, distance


class Checks(unittest.TestCase):
    def test_distance_and_hash(self):
        self.assertEqual(distance(b'kitten',b'sitting'),3)
        self.assertEqual(distance(b'\xff',b'\xfe'),1)
        self.assertEqual(distance(b'',b'ab'),2)
        self.assertNotEqual(digest([(1,0),(2,1)]),digest([(2,1),(1,0)]))
        self.assertNotEqual(digest([(1,0)]),digest([(1,1)]))
        self.assertEqual(digest([]),'4953163356653287321')

    def test_oracle_rejects_corrupt_output_and_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);o=p/'oracle.json'
            o.write_text(json.dumps({'queries':[0],'distances':{'0':[0,1,2]}}))
            (p/'result.results').write_text('0 2 1:1 0:0\n')
            with (p/'result.csv').open('w') as f:
                w=csv.writer(f);w.writerow(['qid','query_us','count','ordered_hash']);w.writerow([0,1,2,digest([(1,1),(0,0)])])
            self.assertEqual(check(p,o,1),[(0,[(1,1.),(0,0.)])])
            (p/'result.results').write_text('0 2 0:0 1:1\n')
            with self.assertRaises(AssertionError):check(p,o,1)
            (p/'result.results').write_text('0 2 1:1 1:1\n')
            with self.assertRaises(AssertionError):check(p,o,1)

    def test_statistics_and_admission(self):
        self.assertEqual(percentile([3,1,2],.5),2)
        pair=paired_interval([2]*6,[1]*6)
        self.assertEqual(pair['bootstrap_95'],[2,2]);self.assertEqual(pair['wins'],6)
        good={'exit_code':0,'stop_reason':None,'runtime_errors':[],'post_gpu_clear':True}
        clean(good)
        for k,v in [('exit_code',1),('stop_reason','foreign GPU activity'),('runtime_errors',['invalid argument']),('post_gpu_clear',False)]:
            with self.assertRaises(AssertionError):clean({**good,k:v})

    def test_missing_campaign_labels_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'runs').mkdir();o=p/'oracle.json';o.write_text('{}')
            with self.assertRaisesRegex(AssertionError,'Missing or unclassified'):
                analyze(p,o,p/'absent.tar.gz')


if __name__=='__main__':unittest.main()
