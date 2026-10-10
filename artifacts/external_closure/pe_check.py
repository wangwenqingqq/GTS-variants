#!/usr/bin/env python3
"""Full logical-output qualification. No checks or CPU scores enter GPU timing."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import csv,json,math
from pathlib import Path
import numpy as np
from pe_trace import replay
from qualify import cpu

def csvrows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))

def check(data,events,trace,prefix,method,reference=None):
    x=cpu.validate.load(data);ops=np.loadtxt(events,skiprows=1,dtype=int,ndmin=2)
    logical,final=replay(len(x),ops);N=len(x);d=x.shape[1];prefix=str(prefix);trace=str(trace)
    qv=np.fromfile(trace+'.vectors.f32',dtype='<f4').reshape(len(ops),d)
    lines=Path(trace+'.logical').read_text().splitlines();assert tuple(map(int,lines[0].split()))==(len(ops),N,d)
    assert [tuple(map(int,s.split())) for s in lines[1:]]==[(f,o) for f,o,_ in logical]
    source=np.arange(N+len(ops),dtype=np.int64);alive=np.zeros(len(source),bool);alive[:N]=True
    actual=np.fromfile(prefix+'.ids.i32',dtype='<i4');fields=np.fromfile(prefix+'.dist.f32',dtype='<f4')
    assert Path(prefix+'.ids.i32').stat().st_size==len(actual)*4==Path(prefix+'.dist.f32').stat().st_size
    raw=np.fromfile(prefix+'.native_squared.f64',dtype='<f8') if method=='E' else None
    if raw is not None:assert len(raw)==len(actual) and Path(prefix+'.native_squared.f64').stat().st_size==len(raw)*8
    queries=csvrows(prefix+'.queries.csv');states=csvrows(prefix+'.ops.csv');assert len(states)==len(ops)
    refids=reffields=refrows=None
    if reference:
        reference=str(reference);refids=np.fromfile(reference+'.ids.i32',dtype='<i4');reffields=np.fromfile(reference+'.dist.f32',dtype='<f4');refrows=csvrows(reference+'.queries.csv')
        assert len(refids)==len(reffields)
    at=qi=0;reports=[];live_counts=[];physical=base_live=N;buffer=0
    for step,((flag,oid,s),(_,old_index)) in enumerate(zip(logical,ops)):
        n_before=int(alive.sum());before_state=(physical,buffer)
        if flag==0:
            buffer+=1
            if buffer==10:physical=base_live+buffer;base_live=physical;buffer=0
        elif flag==1:
            if old_index<base_live:base_live-=1
            else:buffer-=1
        assert base_live>=0 and 0<=buffer<10
        if flag==0:
            assert qv[step].tobytes()==x[s].tobytes(),'frozen insertion vector mismatch'
            source[oid]=s;alive[oid]=True
        elif flag==1:assert alive[oid];alive[oid]=False
        else:
            assert qv[step].tobytes()==x[s].tobytes(),'frozen request vector mismatch'
            live=np.flatnonzero(alive);r=queries[qi];assert int(r['step'])==step and int(r['offset'])==at
            assert method=='P' or int(r['flag'])==flag
            z=int(r['count']);assert z>=0 and at+z<=len(actual);sl=slice(at,at+z);ai=actual[sl];af=fields[sl]
            valid=(ai>=0)&(ai<len(alive));assert np.all(alive[ai[valid]]) and len(set(map(int,ai[valid])))==valid.sum()
            if refrows is None:
                scores=cpu.validate.scores(x,source[live],qv[step]);wanted=np.flatnonzero(scores<=float(np.float32(.705625057220459))**2) if flag==2 else np.lexsort((live,scores))[:8]
                expected=live[wanted];expected_sq=scores[wanted];expected_fields=np.sqrt(expected_sq).astype(np.float32)
            else:
                rr=refrows[qi];assert int(rr['step'])==step and int(rr['qid'])==old_index
                off=int(rr['offset']);count=int(rr['count']);rids=refids[off:off+count];assert np.all((rids>=0)&(rids<len(live)))
                expected=live[rids];expected_fields=reffields[off:off+count]
                expected_sq=cpu.validate.scores(x,source[expected],qv[step]) if flag==3 or method=='E' else None
            selected_sq=cpu.validate.scores(x,source[ai[valid]],qv[step])
            if flag==2:
                assert valid.all() and set(ai)==set(expected),(step,'complete range membership',list(set(expected)-set(ai))[:10],list(set(ai)-set(expected))[:10])
            else:
                count=min(8,len(live));assert z==8 and valid.sum()==count
                assert np.all(ai[count:]==-1) and np.all(np.isposinf(af[count:]))
                if raw is not None:assert np.all(np.isposinf(raw[sl][count:]))
                if count:
                    boundary=max(expected_sq);closer=set(expected[expected_sq<boundary]);returned=set(ai[:count])
                    assert closer<=returned and np.all(selected_sq<=boundary),(step,'complete tie-aware top-K',closer-returned)
            if method=='P':
                if flag==2:
                    aorder=np.argsort(ai);eorder=np.argsort(expected);assert np.array_equal(ai[aorder],expected[eorder]);assert af[aorder].tobytes()==expected_fields[eorder].tobytes()
                else:
                    expected=np.pad(expected,(0,8-len(expected)),constant_values=-1);expected_fields=np.pad(expected_fields,(0,8-len(expected_fields)),constant_values=np.inf)
                    assert np.array_equal(ai,expected) and af.tobytes()==expected_fields.tobytes(),(step,'P exact order/field bits')
                err=0.
            else:
                assert np.isfinite(af[valid]).all() and (af[valid]>=0).all() and np.isfinite(raw[sl][valid]).all()
                denom=np.maximum(1.,selected_sq)
                err=max(np.max(np.abs(af[valid].astype(float)**2-selected_sq)/denom,initial=0),np.max(np.abs(raw[sl][valid]-selected_sq)/denom,initial=0))
                assert err<=5e-5,(step,'native fields',err)
                if flag==3:assert np.all(np.diff(raw[sl][valid])>=0) and np.all(np.diff(af[valid])>=0)
            reports.append(dict(step=step,flag=flag,count=z,complete_members=True,field_bits=method=='P',native_error_scale1=float(err)))
            qi+=1;at+=z
        state=states[step];assert int(state['step'])==step and int(state['flag'])==flag
        assert all(math.isfinite(float(state[k])) and float(state[k])>=0 for k in ('ack_ms','rebuild_ms'))
        if method=='E':assert int(state['n_before'])==n_before and int(state['n_after'])==alive.sum()
        else:assert tuple(int(state[k]) for k in ('base_before','buffer_before','base_after','buffer_after'))==(*before_state,physical,buffer)
        live_counts.append(int(alive.sum()))
    assert qi==len(queries) and at==len(actual)==len(fields)
    if refrows is not None:assert qi==len(refrows),'reference trace prefix is not complete'
    delivered_final=np.fromfile(prefix+'.final.i32',dtype='<i4');assert Path(prefix+'.final.i32').stat().st_size==4*len(final)
    assert np.array_equal(np.sort(delivered_final),final) and Path(trace+'.final.i32').read_bytes()==final.tobytes()
    if method=='P':
        summary=json.loads(Path(prefix+'.summary.json').read_text());region=json.loads(Path(prefix+'.region.json').read_text());mirror=json.loads(Path(prefix+'.unified.json').read_text());numeric=json.loads(Path(prefix+'.numeric.json').read_text());meta=json.loads(Path(prefix+'.pe.json').read_text())
        assert region['mode']==1 and mirror['knn_mode']=='FULL'
        rebuilds=sum(int(r['flag'])==0 and int(r['buffer_before'])==9 for r in states)
        assert mirror['refreshes']==region['refreshes']==numeric['refreshes']==rebuilds+1
        # Native tile accounting is process-cumulative and written only at main exit.
        if not prefix.endswith('.warmup'):
            tiles=json.loads(Path(prefix+'.build_tiles.json').read_text())
            assert tiles['mode']=='TILED' and not tiles['audit'] and tiles['new_owned_GPU_bytes']==0
            assert tiles['build_calls']==rebuilds+3  # two warmup builds plus measured cold/rebuilds
        assert not mirror['final_owned_bytes'] and not region['final_owned_bytes'] and not numeric['final_bytes']
        assert meta['host_vector_upload_bytes']==sum(f!=1 for f,_,_ in logical)*d*4
        assert summary['observe'] and not summary['tree_audit']
    return dict(passed=True,queries=qi,output_items=at,final_live=len(final),per_query=reports,scope='P exact internal FP64, E native field tolerance with exact membership/tie-aware K; logical occurrence IDs',payload_hashes={s:cpu.sha(prefix+s) for s in ('.ids.i32','.dist.f32','.final.i32')})
