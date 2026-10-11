#!/usr/bin/env python3
"""Copy a hash-verified scalar evidence whitelist; never publish coordinates."""
import argparse
import json
import shutil
from pathlib import Path
from ball import sha,save,outside_repo


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    proof=json.loads((a.run/'PROOF.json').read_text());verify=json.loads(a.verify.read_text())
    assert proof['passed'] and verify['passed'] and verify['proof_sha256']==sha(a.run/'PROOF.json')
    files={'LOCAL_BALL_STATS.json':'summary/LOCAL_BALL_STATS.json','SUMMARY_COMPARISON.json':'query/SUMMARY_COMPARISON.json'}
    for n in ('REGISTERED.json','BUILD.json','DECISION.json','initial_CERTIFICATE_READY.json','first_rebuilt_CERTIFICATE_READY.json'):
        files[n]='evidence/'+n
    records=[]
    for source,target in files.items():
        assert sha(a.run/source)==proof['raw_files'][source]
        dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.run/source,dest)
        records.append(dict(published_file=target,sha256=sha(dest),transform='byte-identical'))
    for source,target in ((a.run/'PROOF.json','evidence/PROOF.json'),(a.verify,'evidence/VERIFY.json')):
        dest=out/target;shutil.copyfile(source,dest)
        records.append(dict(published_file=target,sha256=sha(dest),transform='byte-identical'))
    save(out/'evidence/CURATION.json',dict(passed=True,files=records,
        omitted='Coordinate/reference/score/permutation/certificate arrays and native libraries remain external; raw hashes are in PROOF.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--verify',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
