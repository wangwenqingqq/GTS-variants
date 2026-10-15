"""Independent row-label model;exact allocated-capacity provenance,not coordinates."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from itertools import permutations
from pathlib import Path
import argparse,random
from common import save

def compile_batch(owners,ids):
    n=len(owners);b=len(ids)
    assert 0<b<=min(n,512) and len(set(ids))==b
    pos={v:i for i,v in enumerate(owners)};assert all(v in pos for v in ids)
    original=list(owners);owners=list(owners);physical=list(range(n));tail=list(range(n-b,n));prefix={};commands=[]
    for v in ids:
        row=pos[v];last=len(owners)-1
        if row!=last:
            commands.append((last,row));physical[row]=physical[last]
            origin=tail[last-(n-b)]
            if row>=n-b:tail[row-(n-b)]=origin
            else:prefix[row]=origin
            moved=owners[last];owners[row]=moved;pos[moved]=row
        owners.pop();del pos[v]
    final={**prefix,**{n-b+i:s for i,s in enumerate(tail) if s!=n-b+i}}
    assert not (set(final)&set(final.values())),'Final sources overlap destinations'
    result=list(range(n))
    for dst,src in final.items():result[dst]=src
    assert result==physical,'Allocated capacity differs,including retired rows'
    assert [original[i] for i in result[:n-b]]==owners
    levels=[];written={};read={}
    for src,dst in commands:
        level=1+max(written.get(src,-1),written.get(dst,-1),read.get(dst,-1));levels.append(level)
        written[dst]=level;read[src]=max(level,read.get(src,-1))
    for i,(src,dst) in enumerate(commands):
        for j,(s,d) in enumerate(commands[:i]):
            if d==src or d==dst or s==dst:assert levels[j]<levels[i]
    return dict(commands=commands,levels=levels,final=sorted(final.items()),owners=owners,physical=physical)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    count=0
    for n in range(1,9):
        for b in range(1,n+1):
            for ids in permutations(range(n),b):compile_batch(range(n),ids);count+=1
    rng=random.Random(2026101515);randoms=0;invalid=0
    for n in (65,513,4096):
        for b in (1,min(32,n),min(512,n)):
            for _ in range(64):
                owner=rng.sample(range(10*n),n);ids=rng.sample(owner,b);compile_batch(owner,ids);randoms+=1
        for ids in ([],[-1],[0,0],list(range(513)),[n]):
            try:compile_batch(range(n),ids)
            except AssertionError:invalid+=1
            else:raise AssertionError('Invalid/oversized input admitted')
    chain=compile_batch(range(4096),[0,*range(4095,3584,-1)])
    assert len(chain['commands'])==512 and len(chain['final'])==1 and max(chain['levels'])==511
    save(a.out,dict(passed=True,exhaustive_ordered_sequences=count,N_max_exhaustive=8,random_cases=randoms,invalid_cases=invalid,
        all_allocated_row_labels_equal=True,final_source_destination_disjoint=True,ordinary_batch_levels_dependency_safe=True,
        chain_native_moves=512,chain_final_changed_rows=1,chain_safe_batch_levels=512,GPU_starts=0))
    print('CPU_MODEL_PASS',count,randoms,invalid,'full-capacity+nonalias;chain512moves->1finalrow;0GPU')

if __name__=='__main__':main()
