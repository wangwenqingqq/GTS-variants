#!/usr/bin/env python3
"""Admit ordered hashes only after independent full-output and native checks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import clean
from oracle import check,digest


def verify(root,oracle):
    o=json.loads(oracle.read_text());binary=hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest()
    for name,key in [('words_2000.txt','data_sha256'),('queries.qid','qids_sha256')]:
        assert hashlib.sha256((root/'fixtures'/name).read_bytes()).hexdigest()==o[key]
    checks={}
    for r in [-1,0,4,256]:
        reference=None
        for m in ('DEFGPQ' if r==-1 else 'ADEFGPQ'):
            path=root/'runs'/f'full_{r}_{m}';rec=json.loads((path/'receipt.json').read_text());clean(rec)
            assert rec['binary_sha256']==binary and rec['mode']==m and rec['radius']==r
            actual=check(path,oracle,r)
            if reference is None:reference=actual
            assert actual==reference,path.name
            checks[path.name]=hashlib.sha256((path/'result.results').read_bytes()).hexdigest()
        gold={str(q):[len(p),digest(p)] for q,p in reference}
        (root/'fixtures'/f'expected_{r}.json').write_text(json.dumps(gold,indent=2)+'\n')
    result={'binary_sha256':binary,'full_output_checks':checks,'scope':'CPU byte-edit oracle, full results, exact native order at nonnegative radii'}
    (root/'full_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','oracle']:p.add_argument(name,type=Path)
    a=p.parse_args();r=verify(a.root,a.oracle);print('PASS',len(r['full_output_checks']),'full-output runs')
