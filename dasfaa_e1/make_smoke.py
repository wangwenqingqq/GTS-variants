"""Freeze feature-disjoint real-data smoke cases; never substitute for full loads."""
import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
from audit_inputs import SPECS, load, rowkey, sha

SEEDS = (20261026, 20261027, 20261028)

def make_events(nb, na, nq, seed):
    rng = np.random.Generator(np.random.PCG64(seed))
    ops = np.repeat([0,1,2], [2000,2000,1000]); rng.shuffle(ops)
    active = list(range(nb)); positions = {x:x for x in active}
    events=[]; arrival=0; query=0; version=0
    queries=rng.permutation(nq)
    for seq, op in enumerate(ops):
        uid=-1; off=-1; qid=-1
        if op == 0:
            uid=nb+arrival; off=arrival; arrival+=1
            positions[uid]=len(active); active.append(uid); version+=1
        elif op == 1:
            index=int(rng.integers(len(active))); uid=active[index]
            last=active.pop()
            if index<len(active):active[index]=last;positions[last]=index
            del positions[uid]; version+=1
        else:
            qid=int(queries[query%nq]); query+=1
        events.append(dict(seq=seq, op=('insert','delete','query')[op],id=uid,
                           vector_split='arrival' if op==0 else ('query' if op==2 else None),
                           vector_offset=off if op==0 else qid, query_id=qid,
                           required_snapshot=version, active_size=len(active)))
    assert arrival==na and query==nq and len(active)==nb
    return events

def make_case(root, name, x, dim, seed):
    metric=SPECS[name][3]; rng=np.random.Generator(np.random.PCG64(seed))
    selected=[]; seen=set()
    for row in rng.permutation(len(x)):
        key=rowkey(x[row])
        if key in seen:continue
        seen.add(key);selected.append(int(row))
        if len(selected)==13000:break
    assert len(selected)==13000
    out=root/f'{name}_{seed}';out.mkdir()
    (out/'vectors').mkdir();(out/'ids').mkdir();(out/'trace').mkdir()
    np.save(out/'ids/source_rows.npy',np.array(selected,dtype='<i8'))
    for label,lo,hi in [('base',0,10000),('arrival',10000,12000),('query',12000,13000)]:
        rows=[x[j] for j in selected[lo:hi]]
        if metric==6: arr=np.array([s.encode('latin1') for s in rows],dtype='S109')
        else: arr=np.array(rows,dtype='<f4')
        np.save(out/f'vectors/{label}.npy',arr)
        np.save(out/f'ids/{label}_ids.npy',np.arange(lo,hi,dtype='<i8'))
    events=make_events(10000,2000,1000,seed)
    with (out/'trace/events.jsonl').open('x') as f:
        for event in events:f.write(json.dumps(event)+'\n')
    with (out/'case.bin').open('xb') as f:
        f.write(b'E1CASE1\0');f.write(struct.pack('<7i',metric,dim,10000,2000,1000,8,len(events)))
        for j in selected:
            if metric==6:
                raw=x[j].encode('latin1');assert len(raw)<109
                f.write(raw+b'\0'*(109-len(raw)))
            else:f.write(np.asarray(x[j],dtype='<f4').tobytes())
        for e in events:f.write(struct.pack('<5i',('insert','delete','query').index(e['op']),e['id'],e['vector_offset'],e['query_id'],e['required_snapshot']))
    manifest=dict(dataset=name,seed=seed,metric=metric,base=10000,arrival=2000,queries=1000,k=8,
                  feature_disjoint=True,query_source='deduplicated corpus holdout (smoke only)',
                  hashes={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {**manifest,'manifest_sha256':sha(out/'case_manifest.json')}

def main():
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    records=[]
    for name in SPECS:
        x,_,_,dim=load(a.data_root,name)
        for seed in SEEDS:
            records.append(make_case(a.out,name,x,dim,seed)); print(name,seed,flush=True)
    (a.out/'SMOKE_PINS.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':main()
