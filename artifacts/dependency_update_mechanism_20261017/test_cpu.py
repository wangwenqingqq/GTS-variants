"""Independent full-capacity sequential oracle,including arbitrary generic copy cycles."""
import argparse,json,itertools,random
from pathlib import Path
from planners import generic,tail

def check(n,ids):
    owners=list(range(n));pos=list(owners);physical=list(owners);cmd=[]
    for v in ids:
        row=pos[v];last=len(owners)-1
        if row!=last:
            cmd.append((last,row));physical[row]=physical[last]
            moved=owners[-1];owners[row]=moved;pos[moved]=row
        owners.pop();pos[v]=-1
    a=generic(cmd);b=tail(cmd,n,len(ids));assert a==b
    actual=list(range(n))
    for dst,src in a.items():actual[dst]=src
    assert actual==physical and actual[:n-len(ids)]==owners

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    cases=0
    for n in range(1,9):
        for b in range(1,n+1):
            for ids in itertools.permutations(range(n),b):check(n,ids);cases+=1
    rng=random.Random(2026101700);randoms=0
    for n in (65,513,4096):
        for b in (1,32,512):
            for _ in range(64):check(n,rng.sample(range(n),min(n,b)));randoms+=1
    for _ in range(1000):
        n=32;commands=[(rng.randrange(n),rng.randrange(n)) for _ in range(128)]
        physical=list(range(n))
        for src,dst in commands:physical[dst]=physical[src]
        original=list(range(n));result=list(original)
        for dst,src in generic(commands).items():result[dst]=original[src]
        assert result==physical
    with a.out.open('x') as f:json.dump(dict(passed=True,exhaustive=cases,random_delete=randoms,arbitrary_generic_copy_sequences=1000,entire_capacity=True,generic_equals_tail=True,GPU_starts=0),f,indent=2);f.write('\n')
    print('CPU_PLANNER_PASS',cases,randoms,'generic non-tail control agrees;0 GPU starts')

if __name__=='__main__':main()
