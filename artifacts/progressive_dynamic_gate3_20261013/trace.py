"""Freeze requests before measurement; logical occurrences never mean live ranks."""
import json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ART=HERE.parent
def read(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def load(prefix):
    prefix=str(prefix);lines=Path(prefix+'.logical').read_text().splitlines();h=tuple(map(int,lines[0].split()))
    rows=[tuple(map(int,s.split())) for s in lines[1:]];assert len(rows)==h[0]
    vectors=np.fromfile(prefix+'.vectors.f32',dtype='<f4');assert vectors.size==h[0]*h[2] and Path(prefix+'.vectors.f32').stat().st_size==vectors.size*4
    return h,rows,vectors.reshape(h[0],h[2])
def replay(n,rows):
    cap=n+sum(f==0 for f,_ in rows);physical=list(range(n));position=np.full(cap,-1,dtype=np.int32);position[:n]=np.arange(n)
    next_id=n;states=[];ins=delete=0;snaps={-1:list(physical)};seen=set()
    for step,(flag,oid) in enumerate(rows):
        before=len(physical);row=last=moved=-1
        if flag==0:
            assert oid==next_id and position[oid]==-1
            row=before;physical.append(oid);position[oid]=row;next_id+=1;ins+=1
        elif flag==1:
            assert 0<=oid<next_id and position[oid]>=0
            row=int(position[oid]);last=before-1;moved=physical[-1] if row!=last else -1
            if moved>=0:physical[row]=moved;position[moved]=row
            physical.pop();position[oid]=-1;delete+=1
        else:assert flag in (2,3) and oid==-1
        states.append(dict(step=step,flag=flag,id=oid,n_before=before,n_after=len(physical),row=row,last=last,moved=moved,next=next_id))
        if ins==delete and ins in (20,40) and ins not in seen:
            seen.add(ins);snaps[step]=list(physical)
    snaps[len(rows)]=list(physical)
    return physical,position,states,snaps
def freeze_b(data,a_prefix,out):
    (events,n,d),rows,q=load(a_prefix);source=read(str(a_prefix)+'.source.json');assert len(source)==events
    rp=[s for f,o,s in source if f==2];kp=[s for f,o,s in source if f==3];assert len(rp)==len(kp)==128
    rng=np.random.default_rng(2026101303);rids=rng.permutation(rp)[:100];kids=rng.permutation(kp)[:100]
    logical=[];src=[];physical=list(range(n));live=set(physical);next_id=n
    # Frozen initial victim list, independent of query outcomes and timing.
    victims=iter(rng.permutation(n)[:200].tolist());pair=0
    for g in range(100):
        for k in range(4):
            origin=int(rids[(pair*17)%100]);oid=next_id;next_id+=1
            logical.append((0,oid));src.append((0,oid,origin));live.add(oid)
            victim=next(victims) if pair%2==0 else oid
            assert victim in live;live.remove(victim);logical.append((1,victim));src.append((1,victim,-1));pair+=1
            if k==1:logical.append((2,-1));src.append((2,-1,int(rids[g])))
        logical.append((3,-1));src.append((3,-1,int(kids[g])))
    assert len(logical)==1000 and [sum(f==i for f,_ in logical) for i in range(4)]==[400,400,100,100]
    h=np.fromfile(data,dtype='<i4',count=3);assert h.tolist()==[d,n,2];x=np.memmap(data,offset=12,dtype='<f4',shape=(n,d),mode='r')
    vectors=np.zeros((1000,d),dtype='<f4')
    for i,(_,_,s) in enumerate(src):
        if s>=0:vectors[i]=x[s]
    stem=str(out);Path(stem+'.logical').write_text(f'1000 {n} {d}\n'+''.join(f'{f} {o}\n' for f,o in logical));vectors.tofile(stem+'.vectors.f32');save(stem+'.source.json',src)
    final,position,states,snaps=replay(n,logical);np.asarray(final,dtype='<i4').tofile(stem+'.physical.i32');position.tofile(stem+'.reverse.i32')
    assert max(abs(s['n_after']-n) for s in states)==1
    return dict(seed=2026101303,events=1000,counts=[400,400,100,100],min_live=min(s['n_after'] for s in states),max_live=max(s['n_after'] for s in states),query_pool='original128 range/128 kNN pools',snapshots=list(snaps),input_hashes={p.name:sha(p) for p in Path(out).parent.glob(Path(out).name+'.*') if p.is_file()})
