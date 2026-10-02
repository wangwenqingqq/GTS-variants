#!/usr/bin/env python3
"""Independent CPU FP64 spot check of selected million-scale oracle pairs."""
import argparse
import hashlib
import heapq
import json
import math
import mmap
from pathlib import Path
import random
import struct


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('data','idlist','qfile','oracle_bin','output'):
        parser.add_argument(name,type=Path)
    parser.add_argument('--radius-bits',required=True)
    parser.add_argument('--all-hit',action='store_true')
    args=parser.parse_args()
    qids=[int(x) for x in args.qfile.read_text().split()]
    assert qids[0]==len(qids)-1
    qids=qids[1:]
    selected=set(range(0,len(qids),max(1,len(qids)//16)))
    rng=random.Random(20261002)
    radius=struct.unpack('<f',struct.pack('<I',int(args.radius_bits,16)))[0]
    limit=float(radius)*float(radius)
    checked_hit=checked_miss=0
    with args.data.open('rb') as source,args.idlist.open('rb') as ids_file,args.oracle_bin.open('rb') as oracle:
        data=mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ)
        ids=mmap.mmap(ids_file.fileno(),0,access=mmap.ACCESS_READ)
        d,n,kind=struct.unpack_from('<3i',data,0)
        assert kind==2 and len(ids)==4*n
        def sqdist(qid,oid):
            qbase=12+qid*d*4;obase=12+oid*d*4
            value=0.0
            for j in range(d):
                delta=struct.unpack_from('<f',data,obase+j*4)[0]-struct.unpack_from('<f',data,qbase+j*4)[0]
                value=value+delta*delta
            return value
        for i,qid in enumerate(qids):
            actual_qid,count=struct.unpack('<2i',oracle.read(8))
            assert actual_qid==qid and 0<=count<=n
            if i not in selected:
                oracle.seek(count*8,1)
                continue
            hits=struct.unpack(f'<{count}i',oracle.read(count*4)) if count else ()
            distances=struct.unpack(f'<{count}f',oracle.read(count*4)) if count else ()
            if args.all_hit:assert count==n
            hit_set=set(hits) if not args.all_hit else set()
            positions={0,count//2,count-1}
            positions.update(heapq.nlargest(3,range(count),key=distances.__getitem__))
            for at in positions:
                if not 0<=at<count:continue
                oid=hits[at]
                squared=sqdist(qid,oid)
                assert squared<=limit,(i,oid,'missing CPU hit')
                rounded=struct.pack('<f',math.sqrt(squared))
                assert rounded==struct.pack('<f',distances[at]),(i,oid,'distance bits')
                checked_hit+=1
            misses=0
            while misses<(0 if args.all_hit else 4):
                pos=rng.randrange(n)
                oid=struct.unpack_from('<i',ids,pos*4)[0]
                if oid in hit_set:continue
                assert sqdist(qid,oid)>limit,(i,oid,'CPU miss classified as hit')
                misses+=1;checked_miss+=1
        assert oracle.read(1)==b''
        data.close();ids.close()
    digest=hashlib.sha256()
    with args.oracle_bin.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
    output={'query_count':len(qids),'sampled_queries':len(selected),
            'checked_hits':checked_hit,'checked_misses':checked_miss,
            'radius_bits':args.radius_bits,
            'oracle_sha256':digest.hexdigest(),
            'status':'all CPU membership and selected float32 distance bits match'}
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output))


if __name__=='__main__':main()
