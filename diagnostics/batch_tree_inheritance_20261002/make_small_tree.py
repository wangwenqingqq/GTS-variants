#!/usr/bin/env python3
"""Make a deterministic valid C4 topology for the frozen CPU boundary fixtures."""
import argparse
import struct
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixture',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    d,n,metric=struct.unpack('<iii',(a.fixture/'data.f32bin').read_bytes()[:12])
    assert metric==2 and n in (4096,4103)
    order=list(struct.unpack('<'+str(n)+'i',(a.fixture/'idlist.i32').read_bytes()))
    nodes=11111
    tree=[(0,0.0,0,0,0)]*nodes
    empty=[1]*nodes
    tree[0]=(order[0],0.0,n,0,0);empty[0]=0
    current=[(0,0,n)]
    for depth in range(1,5):
        next_level=[]
        for parent,lid,size in current:
            half=size//2
            for side,(start,width) in enumerate(((lid,half),(lid+half,size-half))):
                nid=parent*10+1+side
                tree[nid]=(order[lid],0.0,width,start,int(depth==4))
                empty[nid]=0
                next_level.append((nid,start,width))
        current=next_level
    assert sum(width for _,_,width in current)==n
    with (a.output/'tree_c4.bin').open('wb') as f:
        f.write(struct.pack('<iii',d,n,nodes))
        for pid,min_dis,size,lid,is_leaf in tree:
            f.write(struct.pack('<ifiii',pid,min_dis,size,lid,is_leaf))
        f.write(struct.pack('<'+str(nodes)+'i',*empty))
        f.write(struct.pack('<'+str(n)+'i',*order))
    q127=(a.fixture/'q127.qid').read_text().split()
    assert int(q127[0])==127
    (a.output/'q33.qid').write_text('33\n'+'\n'.join(q127[1:34])+'\n')
    (a.output/'r33.f32').write_bytes((a.fixture/'r127.f32').read_bytes()[:33*4])
    print(a.output,'tree nodes',nodes,'active leaves',len(current))


if __name__=='__main__':main()
