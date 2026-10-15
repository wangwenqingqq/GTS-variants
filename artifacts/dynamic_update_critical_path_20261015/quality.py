"""Independent occurrence replay, complete exact answers and formal ACK accounting."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import csv
import ctypes
from pathlib import Path
import numpy as np
from common import HERE, REPO, PARENT, sha, load, module
from prepare import input_prefix


def table(path):
    with Path(path).open() as f:return list(csv.DictReader(f))


def array(path,dtype):
    out=np.fromfile(path,dtype);assert out.nbytes==Path(path).stat().st_size;return out


def outputs(prefix):return {p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()}


def distance_fields(dist,sq):
    assert len(dist)==len(sq) and np.isfinite(dist).all() and np.isfinite(sq).all()
    assert (dist>=0).all() and (sq>=0).all(), 'Nonnegative Euclidean and squared-distance fields required'


def operator_group(group,op,sample,b):
    kinds=[0,1,2] if op==2 else [1 if op==0 else 0]
    assert [int(r['kind']) for r in group]==kinds
    for r in group:
        kind=int(r['kind']);assert int(r['sample'])==sample and int(r['rows'])==b
        assert all(np.isfinite(float(r[f])) and float(r[f])>=0 for f in ('ack_ms','delete_ms','insert_ms')) and float(r['ack_ms'])>0
        assert int(r['sync_calls'])==(2 if kind==2 else 1) and int(r['H2D_bytes'])==(b*3840 if kind!=0 else 0)
        assert 0<=int(r['D2D_bytes'])<=b*3840 and int(r['D2D_bytes'])%3840==0
        assert int(r['copy_calls'])==int(r['D2D_bytes'])//3840+int(kind!=0)
        if kind==0:assert float(r['delete_ms'])==float(r['ack_ms']) and float(r['insert_ms'])==0
        if kind==1:assert int(r['D2D_bytes'])==0 and float(r['insert_ms'])==float(r['ack_ms']) and float(r['delete_ms'])==0
    if op==2:
        delete,insert,pair=group
        assert float(pair['delete_ms'])==float(delete['ack_ms']) and float(pair['insert_ms'])==float(insert['ack_ms'])
        assert float(pair['ack_ms'])+1e-9>=float(pair['delete_ms'])+float(pair['insert_ms'])
        for field in ('D2D_bytes','H2D_bytes','copy_calls','sync_calls'):
            assert int(pair[field])==int(delete[field])+int(insert[field]), ('Replacement/native accounting',field)
    return [r for r in group if int(r['kind'])<2]


def check(prefix,job,w,reg):
    prefix=Path(prefix);stem=str(prefix);parent=Path(reg['parent']);old=load(parent/'REGISTERED.json');c=load(HERE/'CONTRACT.json')
    if job['kind']=='service':
        parent_quality=module('immutable_parent_quality',PARENT/'quality.py')
        result=parent_quality.check(prefix,dict(mode=job['mode'],N=1000000,workload=2,diagnostic=job['diagnostic']),parent,{**old,'repo':str(REPO)})
        return dict(passed=True,kind='service',parent_quality=result,raw_outputs=outputs(prefix))
    meta=load(stem+'.meta.json')
    if job['kind']=='copy':
        rows=table(stem+'.copy.csv');assert len(rows)==32 and meta['passed'] and meta['all_destination_bytes_compared']==2*(1<<30)
        assert meta['trace']==int(job['variant']=='MARKED') and meta['bytes']==1<<30
        for r in rows:assert 0<=int(r['round'])<16 and int(r['kind']) in (0,1) and int(r['bytes'])==1<<30 and np.isfinite(float(r['ack_ms'])) and float(r['ack_ms'])>0
        assert {int(r['kind']) for r in rows}=={0,1} and all(sum(int(r['kind'])==kind for r in rows)==16 for kind in (0,1))
        return dict(passed=True,kind='copy',metadata=meta,samples=rows,raw_outputs=outputs(prefix))
    n,k,b=job['N'],job['K'],job['batch'];op=('I','D','R').index(job['op']);live=n-k if op==1 else n
    assert all(meta[key]==value for key,value in dict(kind='micro',N=n,K=k,op=op,batch=b,trace=int(job['variant']=='MARKED'),diagnostic=job['diagnostic'],final_live=live,warmup_queries=8,final_validation_queries=32).items())
    ip=input_prefix(parent,n,2);victims=array(str(ip)+'.victims.i32','<i4')[:k].copy();actual=array(stem+'.mutations.i32','<i4')
    assert len(actual)==(k if op==1 else 2*k)*8
    physical=array(stem+'.physical.i32','<i4');reverse=array(stem+'.reverse.i32','<i4');assert len(physical)==live and len(reverse)==n+k
    fn=ctypes.CDLL(str(w/'build/replay.so')).replay
    fn.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p];fn.restype=ctypes.c_int
    swaps=np.zeros(1,'<u8');assert fn(n,victims.ctypes.data,k,b,op,actual.ctypes.data,len(actual)//8,physical.ctypes.data,live,reverse.ctypes.data,swaps.ctypes.data)==0
    ids=array(stem+'.ids.i32','<i4');dist=array(stem+'.dist.f32','<f4');sq=array(stem+'.squared.f64','<f8');authority=array(stem+'.authority.f64','<f8')
    assert len(ids)==len(dist)==len(sq);distance_fields(dist,sq)
    qr=table(stem+'.queries.csv');assert len(qr)==40
    qids=list(range(32)) if n==4096 else c['qids'];cutoff=c['radius']**2;rank=np.zeros(n,dtype=bool);rank[victims]=True;at=0;maxerr=0.;verified=[]
    for i,r in enumerate(qr):
        phase=-1 if i<8 else 0;slot=i if i<8 else i-8;assert int(r['phase'])==phase and int(r['slot'])==slot and int(r['invocation'])==i and int(r['offset'])==at
        qid=qids[slot];base=np.memmap(parent/'cache'/f'N{n}_W2'/f'{qid}.base.f64' if n==4096 else Path(old['reference'])/f'{qid}.f64','<f8',mode='r',shape=(n,))
        incoming=np.memmap(parent/'cache'/f'N{n}_W2'/f'{qid}.incoming.f64','<f8',mode='r')[:k]
        removed=phase==0 or op==0;inserted=phase==0 and op!=1
        old_hits=np.flatnonzero(base<=cutoff)
        if removed:old_hits=old_hits[~rank[old_hits]]
        new_hits=np.flatnonzero(incoming<=cutoff) if inserted else np.array([],dtype=int)
        wanted=np.concatenate([old_hits,n+new_hits]);scores=np.concatenate([base[old_hits],incoming[new_hits]])
        count=int(r['count']);got=ids[at:at+count];assert len(np.unique(got))==count and np.array_equal(np.sort(got),wanted),('complete members',job['label'],i)
        exact=scores[np.searchsorted(wanted,got)];assert np.array_equal(sq[at:at+count].view('<u8'),exact.astype('<f4').astype('<f8').view('<u8'))
        error=float(np.max(np.abs(dist[at:at+count].astype(float)**2-exact)/np.maximum(1.,exact),initial=0.));assert error<=5e-5;maxerr=max(maxerr,error)
        if job['diagnostic']==2:assert np.array_equal(authority[at:at+count].view('<u8'),exact.view('<u8'))
        verified.append(dict(phase=phase,slot=slot,qid=qid,count=count,complete=True));at+=count
    assert at==len(ids) and len(authority)==(at if job['diagnostic']==2 else 0)
    rows=table(stem+'.ops.csv');expected=k//b*(3 if op==2 else 1);assert len(rows)==expected
    native=[]
    for sample in range(k//b):
        group=rows[sample*(3 if op==2 else 1):(sample+1)*(3 if op==2 else 1)]
        native.extend(operator_group(group,op,sample,b))
    assert sum(int(r['H2D_bytes']) for r in native)==meta['formal_H2D_request_bytes']==(0 if op==1 else k*3840)
    assert sum(int(r['D2D_bytes']) for r in native)==meta['formal_D2D_request_bytes']==(0 if op==0 else int(swaps[0])*3840)
    selected=[r for r in rows if int(r['kind'])==([1,0,2][op])];assert sum(float(r['ack_ms']) for r in selected)<=meta['events_ms']+1e-7
    proof=load(stem+'.final.json');assert proof['passed'] and proof['live']==live and proof['all_vector_bytes_compared']==live*3840
    stages=table(stem+'.stages.csv');assert len(stages)==160
    for i,q in enumerate(verified):
        actual_n=n-k if i<8 and op==0 or i>=8 and op==1 else n
        for stage in range(4):
            r=stages[i*4+stage];assert int(r['stage'])==stage+1 and int(r['invocation'])==i and int(r['input'])==actual_n
            assert 0<=int(r['output'])<=actual_n;actual_n=int(r['output'])
        assert actual_n==q['count']
    return dict(passed=True,kind='micro',metadata=meta,operator_samples=rows,complete_query_records=verified,
        complete_queries=40,false_negatives=0,false_positives=0,exact_native_squared_bits=True,
        internal_FP64_bit_checks=at if job['diagnostic']==2 else 0,max_native_scaled_error=maxerr,
        actual_transition_witnesses=len(actual)//8,independent_full_maps=True,final_device_vector_bytes_compared=live*3840,
        raw_outputs=outputs(prefix))
