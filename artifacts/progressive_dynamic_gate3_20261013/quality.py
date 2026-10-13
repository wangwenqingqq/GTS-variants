"""Complete logical-occurrence outputs and full-state induction, outside timers."""
import csv,math
from pathlib import Path
import numpy as np
from trace import read,sha,load,replay
if not __debug__:raise RuntimeError('Assertions required')
def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def payload(prefix):
    out=[]
    for suffix,dtype in (('.ids.i32','<i4'),('.dist.f32','<f4'),('.native_squared.f64','<f8')):
        p=Path(str(prefix)+suffix);x=np.fromfile(p,dtype=dtype);assert p.stat().st_size==x.size*np.dtype(dtype).itemsize,'trailing payload bytes';out.append(x)
    assert len(out[0])==len(out[1])==len(out[2])
    return out
def fields(actual,score,kind):
    f,raw=actual;assert np.isfinite(f).all() and np.isfinite(raw).all() and (f>=0).all()
    if kind==2:assert (raw>=0).all()
    err=max(float(np.max(np.abs(f.astype(float)**2-score)/np.maximum(1,score),initial=0)),float(np.max(np.abs(raw-score)/np.maximum(1,score),initial=0)))
    assert err<=5e-5,('native ordered field error',err)
    if kind==3:assert (np.diff(raw)>=0).all() and (np.diff(f)>=0).all()
    return err
def query(ids,f,raw,wanted,wanted_score,boundary,source,kind):
    assert len(np.unique(ids))==len(ids),'multiplicity uses distinct occurrence IDs,not unique vectors'
    assert (ids>=0).all()
    if kind==2:
        order=np.argsort(ids);assert np.array_equal(ids[order],wanted),'complete inclusive range members'
        score=wanted_score[np.searchsorted(wanted,ids)]
    else:
        assert len(ids)==8 and (ids<len(source)).all() and set(map(int,wanted))<=set(map(int,ids)),'all strictly closer top-K occurrences'
        score=source[ids];assert (score<=boundary).all(),'tie-aware exact top-K boundary'
    return fields((f,raw),score,kind)
def state_proof(n,rows,actual,capacity):
    """Full-map induction from actual transition witnesses and immutable native bodies.

    The timed path logs only changed owners. Every other entry is unchanged by
    the frozen native insert/erase source. Here each recorded transition is
    checked, and the ENTIRE reconstructed map/live set is verified after it.
    This is not a full actual-map export after every event; final actual maps
    are separately compared byte-for-byte.
    """
    physical=np.empty(capacity,dtype=np.int32);physical[:n]=np.arange(n);pos=np.full(capacity,-1,np.int32);pos[:n]=np.arange(n);alive=pos>=0
    want_phys,want_pos,states,snaps=replay(n,rows);live=n;next_id=n;ai=0;swaps=0;range_index=np.arange(capacity)
    for step,(flag,oid) in enumerate(rows):
        if flag>=2:continue
        expected=states[step];got={k:int(v) for k,v in actual[ai].items()};assert got==expected,('actual mutation witness',step,got,expected);ai+=1
        if flag==0:
            assert oid==next_id and not alive[oid];physical[live]=oid;pos[oid]=live;live+=1;next_id+=1;alive[oid]=True
        else:
            assert alive[oid];r=int(pos[oid]);last=live-1
            if r!=last:physical[r]=physical[last];pos[physical[r]]=r;swaps+=1
            live-=1;alive[oid]=False;pos[oid]=-1
        # A reverse bijection proves uniqueness; all non-live entries must be -1.
        assert np.array_equal(pos[physical[:live]],range_index[:live])
        assert np.array_equal(pos>=0,alive) and int(np.count_nonzero(alive))==live
    assert ai==len(actual) and physical[:live].tolist()==want_phys and np.array_equal(pos[:len(want_pos)],want_pos)
    return physical[:live],pos,states,snaps,swaps
def check_one(prefix,trace,reference,cache,data,mode,dry,capacity,radius):
    prefix=str(prefix);(events,n,d),rows,vectors=load(trace);src=read(str(trace)+'.source.json');assert len(src)==events
    ids,f,raw=payload(prefix);qr=table(prefix+'.queries.csv');ops=table(prefix+'.ops.csv');meta=read(prefix+'.meta.json')
    assert meta['variant']==mode and meta['dry']==dry and meta['capacity']==capacity and len(ops)==events
    physical,pos,states,snaps,swaps=state_proof(n,rows,table(prefix+'.ownership.csv'),capacity)
    expected=read(str(reference)+'.queries.json');rid=np.fromfile(str(reference)+'.ids.i32',dtype='<i4');rsq=np.fromfile(str(reference)+'.scores.f64',dtype='<f8')
    assert Path(str(reference)+'.ids.i32').stat().st_size==4*len(rid) and Path(str(reference)+'.scores.f64').stat().st_size==8*len(rsq) and len(rid)==len(rsq)
    origin=np.zeros(capacity,dtype=np.int64);origin[:n]=np.arange(n);alive=np.zeros(capacity,bool);alive[:n]=True;at=ei=0;maxerror=0.;reports=[];refoff=0;op_totals={str(i):0. for i in range(4)}
    x=np.memmap(data,offset=12,dtype='<f4',shape=(n,d),mode='r')
    for step,((flag,oid),(sf,token,q)) in enumerate(zip(rows,src)):
        assert (sf,token)==(flag,oid)
        if flag==0:
            assert 0<=q<n and vectors[step].tobytes()==x[q].tobytes();origin[oid]=q;alive[oid]=True
        elif flag==1:assert alive[oid] and q==-1;alive[oid]=False
        else:
            assert vectors[step].tobytes()==x[q].tobytes()
            row=qr[ei];ref=expected[ei];assert (int(row['step']),int(row['flag']),int(row['offset']))==(step,flag,at)
            assert (ref['step'],ref['flag'],ref['source'],ref['offset'],ref['live'])==(step,flag,q,refoff,int(alive.sum()))
            z=int(row['count']);assert z>=0 and at+z<=len(ids);sl=slice(at,at+z);returned=ids[sl];assert ((returned>=0)&(returned<capacity)).all() and alive[returned].all()
            r=slice(ref['offset'],ref['offset']+ref['count']);wanted=rid[r];score=rsq[r];assert np.array_equal(wanted,np.sort(wanted))
            full=np.memmap(cache/f'{q}.f64',dtype='<f8',mode='r',shape=(n,));selected=full[origin]
            error=query(returned,f[sl],raw[sl],wanted,score,ref['boundary'],selected,flag);maxerror=max(maxerror,error)
            # Re-derive range cardinality/top-K boundary using ALL live rows.
            # The serialized oracle is not trusted as a hand-edited pass flag.
            live=np.flatnonzero(alive);scores=full[origin[live]]
            if flag==2:assert np.array_equal(wanted,live[scores<=radius**2]) and np.array_equal(score,scores[scores<=radius**2])
            else:
                boundary=float(np.partition(scores,7)[7]);assert boundary==ref['boundary'] and np.array_equal(wanted,live[scores<boundary]) and np.array_equal(score,scores[scores<boundary])
            reports.append(dict(step=step,flag=flag,count=z,complete=True,field_error_scale1=error));at+=z;refoff+=ref['count'];ei+=1
        op=ops[step];st=states[step];assert all(int(op[k])==st[k] for k in ('step','flag','n_before','n_after')) and float(op['rebuild_ms'])==0
        value=float(op['ack_ms']);assert math.isfinite(value) and value>0;op_totals[str(flag)]+=value
    assert ei==len(qr)==len(expected) and at==len(ids) and refoff==len(rid)
    for suffix,want in (('.physical.i32',physical),('.reverse.i32',pos)):
        p=Path(prefix+suffix);assert p.stat().st_size==len(want)*4 and np.array_equal(np.fromfile(p,dtype='<i4'),want),'entire actual final map'
    proof=read(prefix+'.final.proof.json');assert proof['passed'] and proof['all_vector_bytes_bitwise_compared']==len(physical)*d*4 and proof['physical_rows']==len(physical) and proof['reverse_entries']==capacity
    assert meta['final_live']==len(physical) and meta['rebuilds']==0 and meta['norm_updates']==1+sum(f==0 for f,_ in rows) and meta['swap_deletes']==swaps
    assert meta['inserted_H2D_bytes']==sum(f==0 for f,_ in rows)*d*4 and meta['swap_D2D_bytes']==swaps*(d*4+4) and meta['client_payload_bytes']==16*at
    assert meta['vector_storage_bytes']==capacity*d*4 and meta['norm_storage_bytes']==capacity*4 and meta['reverse_map_capacity_bytes']==capacity*4
    assert meta['progressive_state_bytes']==(32*capacity if mode=='D1' else 0)
    assert meta['query_owned_bytes']==capacity*25+d*4+4+meta['cub_scratch_bytes']+meta['progressive_state_bytes']
    assert abs(meta['trace_ms']-meta['events_ms']-meta['release_ms'])<=1e-8 and meta['events_ms']+1e-4>=sum(op_totals.values())
    assert all(math.isfinite(meta[k]) and meta[k]>0 for k in ('trace_ms','events_ms','release_ms','offline_final_and_probe_ms','setup_ms','context_ms'))
    if mode=='D1':
        stages=table(prefix+'.stages.csv');invocations=sum(f==2 for f,_ in rows)+(128 if dry else 0);assert len(stages)==invocations*4
        for i in range(invocations):
            active=None
            for j,row in enumerate(stages[i*4:i*4+4]):
                assert int(row['invocation'])==i and int(row['stage'])==j+1 and 0<=int(row['output'])<=int(row['input'])
                if active is not None:assert int(row['input'])==active
                active=int(row['output'])
    return dict(passed=True,queries=ei,range_queries=sum(f==2 for f,_ in rows),knn_queries=sum(f==3 for f,_ in rows),updates=sum(f<2 for f,_ in rows),complete_members=True,false_negatives=0,false_positives=0,ownership_errors=0,final_state_errors=0,mutation_check='actual local witnesses+full independently replayed bijection induction;final actual full maps+all GPU vector bytes',output_items=at,max_field_error_scale1=maxerror,per_query=reports,op_totals_ms=op_totals,meta=meta,final_proof=proof,snapshot_steps=list(snaps))
def check_probes(prefix,trace,cache,reg,w):
    (events,n,d),rows,vectors=load(trace);src=read(str(trace)+'.source.json');physical,pos,states,snaps=replay(n,rows);pool=[int(x) for x in (w/'pool32.txt').read_text().split()];assert len(pool)==32
    origin=np.arange(len(pos))
    for (flag,oid),(_,_,q) in zip(rows,src):
        if flag==0:origin[oid]=q
    ids,f,raw=payload(str(prefix)+'.probe');qr=table(str(prefix)+'.probe.queries.csv');stages=table(str(prefix)+'.probe.stages.csv');assert len(qr)==128 and len(stages)==512
    at=qi=0;result=[]
    dimpaths={int(Path(p).stem.split('.')[0]):Path(p) for p in reg['stage_reference_hashes']}
    for step,logical in snaps.items():
        logical=np.asarray(logical);ordered=np.sort(logical);sources=origin[logical]
        for q in pool:
            row=qr[qi];assert (int(row['step']),int(row['flag']),int(row['offset']))==(step,q,at);z=int(row['count']);assert z>=0 and at+z<=len(ids)
            full=np.memmap(cache/f'{q}.f64',dtype='<f8',mode='r',shape=(n,));all_scores=full[origin[ordered]];hit=all_scores<=reg['radius']**2;wanted=ordered[hit];sq=all_scores[hit]
            query(ids[at:at+z],f[at:at+z],raw[at:at+z],wanted,sq,None,np.empty(0),2)
            required=np.memmap(dimpaths[q],dtype='<u2',mode='r',shape=(n,));want=[int(np.count_nonzero(required[sources]>end)) for end in (128,256,512)]+[len(wanted)];active=len(logical)
            for j,st in enumerate(stages[qi*4:qi*4+4]):
                assert (int(st['step']),int(st['qid']),int(st['live']),int(st['stage']),int(st['input']),int(st['output']))==(step,q,len(logical),j+1,active,want[j]),'all snapshot stage survivor counts'
                active=want[j]
            result.append(dict(step=step,qid=q,live=len(logical),survivors=want,percent=[100*v/len(logical) for v in want]));at+=z;qi+=1
    assert at==len(ids)
    return dict(passed=True,complete_probe_queries=128,rows=result,check='full exact members/fields+all counts against frozen ordered CPU prefix evidence')
def check(prefix,job,w,reg):
    fixture=job.get('fixture',False);trace=w/'fixtures/trace' if fixture else w/'inputs'/job['workload'];data=w/'fixtures/data.f32bin' if fixture else Path(reg['data']);cache=w/'fixtures/cache' if fixture else w/'cache';label='fixture' if fixture else job['workload']
    (_,n,_),rows,_=load(trace);_,warm_rows,_=load(str(trace)+'.warmup');capacity=n+max(sum(f==0 for f,_ in rows),sum(f==0 for f,_ in warm_rows));radius=1. if fixture else reg['radius']
    measured=check_one(prefix,trace,w/'references'/label,cache,data,job['mode'],job.get('dry',False),capacity,radius)
    warm=check_one(str(prefix)+'.warmup',str(trace)+'.warmup',w/'references'/(label+'.warmup'),cache,data,job['mode'],False,capacity,radius)
    scope=read(str(prefix)+'.scope.json');assert scope['warmup_events']==19 and scope['warmup_queries']==8
    probes=check_probes(prefix,trace,cache,reg,w) if job.get('dry',False) and job['mode']=='D1' else None
    return dict(passed=True,job=job,measured=measured,warmup=warm,probes=probes,output_hashes={p.name:sha(p) for p in Path(prefix).parent.glob(Path(prefix).name+'.*') if p.is_file()})
