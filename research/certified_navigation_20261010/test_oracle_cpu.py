#!/usr/bin/env python3
"""Small CPU reference cross-check; not a native-tree or cache boundary gate."""
from fractions import Fraction
import itertools
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from verify import result
HERE=Path(__file__).resolve().parent

def test():
    cxx=shutil.which('c++')
    if not cxx:raise RuntimeError('C++ compiler needed for the reference check')
    cases=[[[0.,0.,0.]]*9,
           [[i/16.,((i*3)%17)/16.,((i*7)%17)/16.] for i in range(17)],
           [[struct.unpack('<f',struct.pack('<I',i))[0],0.,0.] for i in range(9)]]
    real_order_differences=0
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp);binary=t/'oracle'
        subprocess.run([cxx,'-O3','-fno-fast-math','-ffp-contract=off','-std=c++17',str(HERE/'oracle_cpu.cpp'),'-o',str(binary)],check=True)
        for number,points in enumerate(cases):
            points=[[struct.unpack('<f',struct.pack('<f',x))[0] for x in p] for p in points]
            n=len(points);data=t/f'c{number}.data';q=t/f'c{number}.qid';o=t/f'c{number}.bin'
            data.write_bytes(struct.pack('<3i',3,n,2)+struct.pack('<'+str(n*3)+'f',*itertools.chain.from_iterable(points)))
            q.write_text(str(n)+'\n'+'\n'.join(map(str,range(n)))+'\n')
            subprocess.run([str(binary),str(data),str(q),'8',str(o)],check=True,stdout=subprocess.DEVNULL)
            raw,shape=result(o);ids=struct.unpack_from('<'+str(n*8)+'i',raw,16)
            scores=struct.unpack_from('<'+str(n*8)+'d',raw,16+n*8*4)
            for query,p in enumerate(points):
                expected=[];exact=[]
                for row,x in enumerate(points):
                    s=0.;r=Fraction(0)
                    for a,b in zip(x,p):
                        delta=a-b;s=s+delta*delta;r+=(Fraction(a)-Fraction(b))**2
                    expected.append((s,row));exact.append((r,row))
                expected.sort();exact.sort()
                got=list(zip(scores[query*8:(query+1)*8],ids[query*8:(query+1)*8]))
                if got!=expected[:8]:raise AssertionError('CPU RN score or lex identity mismatch')
                real_order_differences+=([x[1] for x in exact[:8]]!=[x[1] for x in expected[:8]])
    print(f'PASS {sum(map(len,cases))} exhaustive small queries, full score/ID/order; exact-rational rank differences={real_order_differences}; not E2 native tree admission')

if __name__=='__main__':test()
