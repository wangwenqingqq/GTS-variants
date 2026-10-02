#!/usr/bin/env python3
"""Reuse the frozen boundary vectors and add a seven-object partial tile."""
from array import array
import argparse
from pathlib import Path
import random
import struct


def main():
    p=argparse.ArgumentParser()
    p.add_argument('boundary_root',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    for d in (2,31,32,33,96,960):
        original=(a.boundary_root/str(d)/'data.f32bin').read_bytes()
        assert struct.unpack_from('<iii',original)==(d,4096,2)
        payload=original[12:]
        assert len(payload)==4096*d*4
        for n in (4096,4103):
            directory=a.output/f'd{d}_n{n}'
            directory.mkdir(parents=True,exist_ok=False)
            extra=payload[:7*d*4] if n==4103 else b''
            (directory/'data.f32bin').write_bytes(struct.pack('<iii',d,n,2)+payload+extra)
            order=array('i',((pos*13)%n for pos in range(n)))
            assert len(set(order))==n
            with (directory/'idlist.i32').open('wb') as f:order.tofile(f)
            rng=random.Random(20261001+d+n)
            qids=[0,0,1,2,4,5]
            while len(qids)<129:
                q=rng.randrange(n)
                if q not in qids:qids.append(q)
            radii=(-1.0,0.0,2.0**-149,
                   struct.unpack('<f',struct.pack('<I',0x3f7fffff))[0],
                   1.0,struct.unpack('<f',struct.pack('<I',0x3f800001))[0],
                   2.0**120)
            for b in (1,3,8,32,127,128,129):
                (directory/f'q{b}.qid').write_text(str(b)+'\n'+''.join(f'{q}\n' for q in qids[:b]))
                with (directory/f'r{b}.f32').open('wb') as f:
                    for i in range(b):f.write(struct.pack('<f',radii[i%len(radii)]))


if __name__=='__main__':main()
