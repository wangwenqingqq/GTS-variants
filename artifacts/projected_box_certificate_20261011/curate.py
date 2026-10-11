#!/usr/bin/env python3
"""Publish a byte-preserved scalar evidence whitelist, never raw projections."""
import argparse
import json
import shutil
from pathlib import Path
from box import sha,save,outside_repo


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    p=json.loads((a.run/'PROOF.json').read_text());v=json.loads(a.verify.read_text())
    assert p['passed'] and v['passed'] and v['proof_sha256']==sha(a.run/'PROOF.json')
    files={'PROJECTED_BOX_STATS.json':'summary/PROJECTED_BOX_STATS.json','SUMMARY_COMPARISON.json':'query/SUMMARY_COMPARISON.json'}
    files.update({n:'directions/'+n for n in ('PCA_DIRECTIONS.json','DIRECTION_PROOF.json')})
    files.update({n:'evidence/'+n for n in ('REGISTERED.json','BUILD.json','DECISION.json','initial_BOX_READY.json','first_rebuilt_BOX_READY.json')})
    records=[]
    for source,target in files.items():
        assert sha(a.run/source)==p['raw_files'][source]
        dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.run/source,dest)
        records.append(dict(published_file=target,sha256=sha(dest),transform='byte-identical'))
    for source,target in ((a.run/'PROOF.json','evidence/PROOF.json'),(a.verify,'evidence/VERIFY.json')):
        dest=out/target;shutil.copyfile(source,dest);records.append(dict(published_file=target,sha256=sha(dest),transform='byte-identical'))
    save(out/'evidence/CURATION.json',dict(passed=True,files=records,omitted='Raw coordinates/references, per-object projections, covariance arrays, permutations and libraries remain external; hashes in PROOF. Derived PCA directions and scalar block/query summaries only.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--verify',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
