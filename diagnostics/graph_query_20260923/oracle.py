#!/usr/bin/env python3
"""Independent byte-edit-distance membership oracle and full-output validation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'original_tree_profile'))
from make_fixture import distance


def digest(pairs):
    h=1469598103934665603
    for i,d in pairs:
        for word in (i,struct.unpack('<I',struct.pack('<f',d))[0]):
            h=((h^word)*1099511628211)&((1<<64)-1)
    return str(((h^len(pairs))*1099511628211)&((1<<64)-1))


def make(data,qids,out):
    rows=data.read_bytes().splitlines();n=int(rows[0].split()[1]);rows=rows[1:];assert n==len(rows)==2000
    ids=list(map(int,qids.read_text().split()));assert ids.pop(0)==len(ids)
    expected={str(q):[distance(rows[q],s) for s in rows] for q in dict.fromkeys(ids)}
    record={'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'qids_sha256':hashlib.sha256(qids.read_bytes()).hexdigest(),'queries':ids,'distances':expected}
    out.write_text(json.dumps(record)+'\n');print('Oracle ready for',len(expected),'distinct queries')


def check(run,oracle,radius):
    o=json.loads(oracle.read_text());actual=[]
    for line in (run/'result.results').read_text().splitlines():
        fields=line.split();q,n=map(int,fields[:2]);pairs=[(int(x.split(':')[0]),float(x.split(':')[1])) for x in fields[2:]]
        expected=[(i,d) for i,d in enumerate(o['distances'][str(q)]) if d<=radius]
        assert len(pairs)==n==len(expected),(run.name,q,n,len(expected))
        assert sorted(pairs)==expected,(run.name,q,'membership or distance mismatch')
        actual.append((q,pairs))
    assert len(actual)==len(o['queries']) and [q for q,p in actual]==o['queries']
    with (run/'result.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(actual)
    assert all(int(r['qid'])==q and int(r['count'])==len(p) and r['ordered_hash']==digest(p)
               for r,(q,p) in zip(rows,actual)), 'CSV digest disagrees with full output'
    return actual


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    m=s.add_parser('make');m.add_argument('data',type=Path);m.add_argument('qids',type=Path);m.add_argument('out',type=Path)
    c=s.add_parser('check');c.add_argument('oracle',type=Path);c.add_argument('radius',type=float);c.add_argument('runs',nargs='+',type=Path)
    c.add_argument('--expected',type=Path,help='Write the independently validated ordered hashes for later monitored runs')
    a=p.parse_args()
    if a.command=='make':make(a.data,a.qids,a.out)
    else:
        results=[check(r,a.oracle,a.radius) for r in a.runs]
        assert all(x==results[0] for x in results),'native ordered outputs differ'
        if a.expected:
            a.expected.write_text(json.dumps({str(q):[len(p),digest(p)] for q,p in results[0]},indent=2)+'\n')
        print('PASS: full membership/distances/count/native order for',len(a.runs),'runs')
