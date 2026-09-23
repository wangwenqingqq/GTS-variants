#!/usr/bin/env python3
"""Prepare reproducible real-data scale cases; no GPU activity."""
import argparse,hashlib,json,random,resource,subprocess,time
from pathlib import Path

def prepare(data,root):
    raw=data.read_bytes();assert hashlib.sha256(raw).hexdigest()=='72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c'
    lines=raw.splitlines();width,total,metric=map(int,lines.pop(0).split());assert len(lines)==total==611756 and metric==6
    for n in [2000,20000,100000,611756]:
        f=root/'fixtures'/str(n);f.mkdir();rows=[lines[i*(total-1)//(n-1)] for i in range(n)]
        (f/'data.txt').write_bytes(f'{width} {n} 6\n'.encode()+b'\n'.join(rows)+b'\n')
        qs=[i*(n-1)//31 for i in range(32)];rng=random.Random(20260923)
        for q in rng.sample(range(n),64):
            if q not in qs:qs.append(q)
            if len(qs)==64:break
        assert len(qs)==len(set(qs))==64;random.Random(935).shuffle(qs)
        for name,ids in [('queries.qid',qs),('boundary.qid',qs[:4])]:
            (f/name).write_text(str(len(ids))+'\n'+'\n'.join(map(str,ids))+'\n')
        (f/'manifest.json').write_text(json.dumps({'n':n,'qids':qs,'source_sha256':hashlib.sha256(raw).hexdigest(),
          'file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in f.iterdir()}},indent=2)+'\n')
        for k in ([1,8,32] if n==611756 else [1]):
            c=root/'cases'/f'n{n}_k{k}';c.mkdir();(c/'runs').mkdir();(c/'bin').symlink_to('../../bin');(c/'fixtures').symlink_to(f'../../fixtures/{n}')
    print('Prepared six cases from verified real Words input')

def oracles(root):
    for n in [2000,20000,100000,611756]:
        out=root/f'fixtures/{n}/oracle.bin';assert not out.exists()
        start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        prefix=root/f'logs/oracle_retry_{n}'
        with prefix.with_suffix('.stdout').open('x') as stdout,prefix.with_suffix('.stderr').open('x') as stderr:
            subprocess.run([str(root/'bin/oracle'),str(root/f'fixtures/{n}/data.txt'),str(root/f'fixtures/{n}/queries.qid'),str(out)],
                           check=True,stdout=stdout,stderr=stderr,timeout=1200)
        after=resource.getrusage(resource.RUSAGE_CHILDREN);assert out.stat().st_size==n*64
        record={'n':n,'queries':64,'wall_s':time.monotonic()-start,'cpu_s':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                'oracle_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((root/'bin/oracle').read_bytes()).hexdigest()}
        prefix.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('data',type=Path);prep.add_argument('root',type=Path)
    ref=sub.add_parser('oracles');ref.add_argument('root',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.data,a.root.resolve())
    else:oracles(a.root.resolve())
