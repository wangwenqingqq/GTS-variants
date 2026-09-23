#!/usr/bin/env python3
"""Promote ordered hashes only after independent full-output and native-order checks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'graph_query_20260923'))
from analyze import clean
from oracle import check,digest


def verify(root,oracle):
    o=json.loads(oracle.read_text())
    for name,key in [('words_2000.txt','data_sha256'),('queries.qid','qids_sha256')]:
        assert hashlib.sha256((root/'fixtures'/name).read_bytes()).hexdigest()==o[key]
    binary=hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest();checks={};expected={}
    for r in [-1,0,4,256]:
        reference=None
        for m in ('BCDE' if r==-1 else 'ABCDE'):
            path=root/'runs'/f'full_{r}_{m}';rec=json.loads((path/'receipt.json').read_text());clean(rec)
            assert rec['binary_sha256']==binary and rec['radius']==r and rec['mode']==m
            actual=check(path,oracle,r)
            if reference is None:reference=actual
            assert actual==reference,path.name
            checks[path.name]=hashlib.sha256((path/'result.results').read_bytes()).hexdigest()
        expected[r]={str(q):[len(p),digest(p)] for q,p in reference}
    for r,gold in expected.items():(root/'fixtures'/f'expected_{r}.json').write_text(json.dumps(gold,indent=2)+'\n')
    result={'binary_sha256':binary,'full_output_checks':checks,'negative_radius_reference':'B; native A has known zero-grid error'}
    (root/'full_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','oracle']:p.add_argument(name,type=Path)
    a=p.parse_args();result=verify(a.root,a.oracle)
    print('PASS',len(result['full_output_checks']),'full-output runs; ordered hashes generated')
