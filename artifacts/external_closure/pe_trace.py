#!/usr/bin/env python3
"""Freeze vector requests and stable occurrence IDs by replaying the old physical trace."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,struct
from pathlib import Path
from common import outside_repo
import numpy as np
from qualify import cpu

def replay(n, operations):
    # Physical base retains deleted coordinates until native stable compaction.
    base=np.arange(n,dtype=np.int64);occ=base.copy();alive=np.ones(n,bool)
    buffer=[];next_id=n;rows=[]
    for step,(flag,index) in enumerate(operations):
        flag,index=int(flag),int(index)
        assert 0<=flag<=3 and index>=0
        if flag==1:
            positions=np.flatnonzero(alive)
            if index<len(positions):
                p=positions[index];oid=int(occ[p]);alive[p]=False
            else:
                oid,_=buffer.pop(index-len(positions))
            source=-1
        else:
            assert index<len(base);source=int(base[index]);oid=-1
            if flag==0:
                oid=next_id;next_id+=1;buffer.append((oid,source))
                if len(buffer)==10:
                    occ=np.r_[occ[alive],[v[0] for v in buffer]]
                    base=np.r_[base[alive],[v[1] for v in buffer]]
                    alive=np.ones(len(base),bool);buffer=[]
        rows.append((flag,oid,source))
    final=np.r_[occ[alive],[v[0] for v in buffer]].astype('<i4')
    assert len(set(final))==len(final) and np.all(final[:-1]<final[1:])
    return rows,final

def warm_events():
    return [(2,0),(3,0),(0,0),(2,0),(3,0),(1,0),(2,0),(3,0)]+[(0,0)]*9+[(2,0),(3,0)]

def freeze(data,events,prefix):
    x=cpu.validate.load(data);ops=np.loadtxt(events,skiprows=1,dtype=int,ndmin=2)
    assert len(ops)==int(Path(events).read_text().splitlines()[0])
    prefix=outside_repo(Path(prefix));assert not list(prefix.parent.glob(prefix.name+'.*'))
    binding={}
    for suffix,ev in (('',ops),('.warmup',warm_events())):
        rows,final=replay(len(x),ev);stem=str(prefix)+suffix
        Path(stem+'.logical').write_text(f'{len(rows)} {len(x)} {x.shape[1]}\n'+''.join(f'{f} {o}\n' for f,o,s in rows))
        vectors=np.zeros((len(rows),x.shape[1]),np.float32)
        for i,(_,_,source) in enumerate(rows):
            if source>=0:vectors[i]=x[source]
        vectors.astype('<f4').tofile(stem+'.vectors.f32');final.tofile(stem+'.final.i32')
        Path(stem+'.source.json').write_text(json.dumps(rows)+'\n')
        binding[suffix or 'main']={s:cpu.sha(stem+s) for s in ('.logical','.vectors.f32','.final.i32','.source.json')}
    result=dict(data_sha256=cpu.sha(data),events_sha256=cpu.sha(events),N=len(x),D=x.shape[1],files=binding,source_sha256=cpu.sha(__file__))
    cpu.save(str(prefix)+'.binding.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('data','events','prefix'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();freeze(a.data,a.events,a.prefix)
