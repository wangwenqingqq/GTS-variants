#!/usr/bin/env python3
"""Byte-preserved scalar whitelist plus lossless per-tile occupancy CSV."""
import argparse
import gzip
import shutil
from pathlib import Path
from tiles import load,sha,save,outside_repo


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);p=load(a.run/'PROOF.json');v=load(a.verify)
    assert p['passed'] and v['passed'] and v['proof_sha256']==sha(a.run/'PROOF.json')
    files={'GRANULARITY_RESULTS.json':'granularity/GRANULARITY_RESULTS.json','ORACLE_BY_TILE.json':'oracle/ORACLE_BY_TILE.json','COST_PROXY.json':'cost/COST_PROXY.json','REGISTERED.json':'evidence/REGISTERED.json','DECISION.json':'evidence/DECISION.json'}
    records=[]
    for n,target in files.items():
        assert sha(a.run/n)==p['raw_files'][n];dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.run/n,dest)
        records.append(dict(published_file=target,sha256=sha(dest),transform='byte-identical'))
    for src,target in [(a.run/'PROOF.json','evidence/PROOF.json'),(a.verify,'evidence/VERIFY.json')]:
        shutil.copyfile(src,out/target);records.append(dict(published_file=target,sha256=sha(out/target),transform='byte-identical'))
    src=a.run/'TILE_STATS.csv';assert sha(src)==p['raw_files'][src.name]
    dest=out/'granularity/TILE_STATS.csv.gz';dest.write_bytes(gzip.compress(src.read_bytes(),mtime=0))
    save(out/'evidence/CURATION.json',dict(passed=True,files=records,occupancy_gzip_sha256=sha(dest),occupancy_uncompressed_sha256=sha(src),omitted='Coordinates, full references, score arrays, occurrence IDs and tile permutations/bounds remain external. Hashes retained; no raw conversations/configuration/manuscript.'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('run','verify','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
