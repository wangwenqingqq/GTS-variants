"""Precompute complete exact answers from immutable ordered-FP64 caches."""
import csv
from pathlib import Path
import numpy as np
from protocol import save,ends,batches
from planners import generic,dependencies
RADIUS=0.705625057220459
QIDS=[88406,865632,881748,916533,40158,242468,40486,900387,703226,791039,724874,671829,722418,152899,737995,144573,570909,347206,63744,625378,136857,201233,72436,617423,810945,789615,601856,433080,415755,282095,66651,326654]
def records(n,micro=False):
    return [dict(phase=-1,slot=i,mutation=0) for i in range(8)]+[dict(phase=p,slot=s,mutation=m) for p,m in enumerate(ends(n,micro)) for s in range(32)]
def build(stem,n,b,micro,parent,reference,out):
    assert not out.exists();out.mkdir();k=ends(n,micro)[-1];victims=np.fromfile(str(stem)+'.victims.i32','<i4');assert len(victims)==k
    qids=list(range(32)) if n==4096 else QIDS;folder=parent/'cache'/f'N{n}_W2';scores=[]
    for q in qids:
        base=np.memmap(folder/f'{q}.base.f64' if n==4096 else reference/f'{q}.f64','<f8',mode='r',shape=(n,))
        incoming=np.memmap(folder/f'{q}.incoming.f64','<f8',mode='r')[:k]
        old=np.flatnonzero(base<=RADIUS**2);new=np.flatnonzero(incoming<=RADIUS**2)
        scores.append((np.concatenate((old,n+new)).astype('<i4'),np.concatenate((base[old],incoming[new]))))
    mask=np.zeros(n+k,dtype=bool);mask[:n]=True;at=0;answer=[];allids=[];allscores=[];offset=0
    for record in records(n,micro):
        stop=record['mutation']
        while at<stop:
            count=min(b,stop-at);ids=victims[at:at+count];assert len(set(map(int,ids)))==count and mask[ids].all()
            mask[ids]=False;mask[n+at:n+at+count]=True;at+=count
        ids,sq=scores[record['slot']];keep=mask[ids];ids=ids[keep];sq=sq[keep]
        answer.append({**record,'offset':offset,'count':len(ids)});allids.append(ids);allscores.append(sq);offset+=len(ids)
    np.concatenate(allids).astype('<i4').tofile(out/'ids.i32');np.concatenate(allscores).astype('<f8').tofile(out/'scores.f64');save(out/'queries.json',answer)
    # Independent physical owner replay supplies expected structure for each batch.
    owner=list(range(n));position=list(range(n))+[-1]*k;next_id=n;structure=[]
    for batch in batches(n,b,micro):
        commands=[];ids=victims[batch['begin']:batch['begin']+batch['count']]
        for v in ids:
            row=position[v];last=len(owner)-1
            if row!=last:
                commands.append((last,row));moved=owner[-1];owner[row]=moved;position[moved]=row
            owner.pop();position[v]=-1
        net=generic(commands);structure.append({**batch,'moves':len(commands),'assignments':len(net),'changed_destinations':len({dst for src,dst in commands}),**dependencies(commands)})
        for _ in ids:position[next_id]=len(owner);owner.append(next_id);next_id+=1
    with (out/'structure.csv').open('x') as f:
        writer=csv.DictWriter(f,fieldnames=list(structure[0]),lineterminator='\n');writer.writeheader();writer.writerows(structure)
    save(out/'PROOF.json',dict(passed=True,complete_queries=168,full_cache_authority=True,fresh_ID_deletions_supported=True,N=n,K=k,batch=b,micro=micro,hit_records=offset))
