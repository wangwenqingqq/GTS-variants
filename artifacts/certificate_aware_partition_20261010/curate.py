#!/usr/bin/env python3
"""Whitelist scalar evidence; preserve raw bytes, exclude vectors/permutations."""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())


def main(a):
    root=a.artifact;raw=a.raw
    s=load(raw/'run/PROOF.json');u=load(raw/'update/PROOF.json');v=load(raw/'verification/VERIFY.json')
    sr=load(raw/'run/REGISTERED.json');ur=load(raw/'update/REGISTERED.json')
    assert s['passed'] and u['passed'] and v['passed']
    assert v['static_proof_sha256']==ur['static_proof_sha256']==sha(raw/'run/PROOF.json')
    assert ur['static_verification_sha256']==sha(raw/'verification/VERIFY.json')
    assert sr['source_hashes']==s['source_hashes']==ur['static_source_hashes']
    assert u['source_hashes']==ur['source_hashes']
    assert sr['contract_sha256']==ur['contract_sha256']==sha(root/'CONTRACT.json')
    assert u['registered_sha256']==sha(raw/'update/REGISTERED.json')
    for folder,proof in [('run',s),('update',u)]:
        for p in (raw/folder).glob('*.json'):
            if p.name!='PROOF.json':assert sha(p)==proof['raw_files'][p.name]
    assert hashlib.sha256(gzip.decompress((raw/'run/BLOCK_STATS.csv.gz').read_bytes())).hexdigest()==s['raw_files']['BLOCK_STATS.csv']
    q=load(raw/'run/BLOCK_SELECTIVITY.json');updates=load(raw/'update/UPDATE_RECHECK.json')
    assert len(q['rows'])==1024 and sum(r['false_prune_blocks'] for r in q['rows'])==0
    assert len(updates['rows'])==2 and updates['query_rows']==128
    mapping={'run/PARTITION_STATS.json':'partition/PARTITION_STATS.json','run/BLOCK_STATS.csv.gz':'partition/BLOCK_STATS.csv.gz',
             'run/BLOCK_SELECTIVITY.json':'query/BLOCK_SELECTIVITY.json','run/DECISION.json':'evidence/DECISION.json',
             'run/PROOF.json':'evidence/STATIC_PROOF.json','run/REGISTERED.json':'evidence/STATIC_REGISTERED.json',
             'verification/VERIFY.json':'evidence/STATIC_VERIFY.json','update/PROOF.json':'evidence/UPDATE_PROOF.json',
             'update/REGISTERED.json':'evidence/UPDATE_REGISTERED.json','update/UPDATE_RECHECK.json':'update/UPDATE_RECHECK.json',
             'ENVIRONMENT.json':'evidence/ENVIRONMENT.json'}
    records=[]
    for src,dst in mapping.items():
        target=root/dst;target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists();shutil.copyfile(raw/src,target)
        records.append(dict(raw_file=src,published_file=dst,sha256=sha(target),byte_identical=True))
    result=dict(passed=True,policy='Whitelist scalar counts and proof receipts; no numeric rewrites or private input paths',
                files=records,per_block_uncompressed_sha256=s['raw_files']['BLOCK_STATS.csv'],
                excluded='All object coordinates, references, occurrence/lineage arrays and partition NPZ files remain external with hashes in the proofs')
    (root/'evidence/CURATION.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);main(p.parse_args())
