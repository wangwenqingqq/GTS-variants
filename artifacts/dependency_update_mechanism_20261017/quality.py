"""Fail-closed complete query,state,activity-ledger and ACK accounting checks."""
if not __debug__:raise SystemExit('Mandatory checks require non-optimized Python.')
import csv,ctypes
from pathlib import Path
import numpy as np
from protocol import VARIANTS,load,sha,ends,batches
from truth import records
def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def array(p,dtype):
    a=np.fromfile(p,dtype);assert a.nbytes==Path(p).stat().st_size;return a
def native_fields(actual,dist,exact,authority=None):
    assert len(actual)==len(dist)==len(exact)
    assert np.isfinite(actual).all() and np.isfinite(dist).all() and (actual>=0).all() and (dist>=0).all()
    assert np.array_equal(actual.view('<u8'),exact.astype('<f4').astype('<f8').view('<u8')),'native squared bits'
    err=float(np.max(np.abs(dist.astype(float)**2-exact)/np.maximum(1.,exact),initial=0.));assert err<=5e-5,'native distance field'
    if authority is not None:assert np.array_equal(authority.view('<u8'),exact.view('<u8')),'ordered FP64 authority bits'
    return err
def check(prefix,j,w,reg):
    p=str(prefix);n=j['N'];b=j['batch'];micro=j['micro'];k=ends(n,micro)[-1];v=VARIANTS.index(j['variant']);diag=j['diagnostic']
    key=f'micro_B{b}' if micro else f'N{n}_{j["family"]}';truth=Path(reg['truth_paths'][key]);proof=load(truth/'PROOF.json');assert proof['passed']
    ip=Path(reg['prefixes']['micro' if micro else f'N{n}_{j["family"]}']);victims=array(str(ip)+'.victims.i32','<i4');assert len(victims)==k
    physical=array(p+'.physical.i32','<i4');reverse=array(p+'.reverse.i32','<i4');mutations=array(p+'.mutations.i32','<i4');assert len(physical)==n and len(reverse)==n+k and len(mutations)==16*k
    replay=ctypes.CDLL(str(w/'build/oracle.so')).replay;replay.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];replay.restype=ctypes.c_int
    stops=np.array(ends(n,micro),'<i4');swaps=np.zeros(1,'<u8');status=replay(n,victims.ctypes.data,k,b,stops.ctypes.data,mutations.ctypes.data,physical.ctypes.data,reverse.ctypes.data,swaps.ctypes.data);assert status==0,('independent mutation replay',status)
    ids=array(p+'.ids.i32','<i4');dist=array(p+'.dist.f32','<f4');sq=array(p+'.squared.f64','<f8');authority=array(p+'.authority.f64','<f8');assert len(ids)==len(dist)==len(sq)
    wanted=array(truth/'ids.i32','<i4');scores=array(truth/'scores.f64','<f8');expected=load(truth/'queries.json');qr=table(p+'.queries.csv');assert len(qr)==len(expected)==168 and expected==[{**a,'offset':e['offset'],'count':e['count']} for a,e in zip(records(n,micro),expected)]
    at=0;maxerr=0.;counts=[]
    for i,(row,e) in enumerate(zip(qr,expected)):
        assert all(int(row[key])==e[key] for key in ('phase','slot','mutation','count','offset')) and int(row['invocation'])==i
        z=e['count'];actual=ids[at:at+z];want=wanted[at:at+z];assert len(np.unique(actual))==z and np.array_equal(np.sort(actual),want),('complete inclusive membership',i)
        exact=scores[at:at+z][np.searchsorted(want,actual)];maxerr=max(maxerr,native_fields(sq[at:at+z],dist[at:at+z],exact,authority[at:at+z] if diag==2 else None));at+=z;counts.append(z)
        assert np.isfinite(float(row['ack_ms'])) and float(row['ack_ms'])>0
    assert at==len(ids)==len(wanted) and len(authority)==(at if diag==2 else 0)
    operations=table(p+'.ops.csv');expected_batches=batches(n,b,micro);up=[r for r in operations if int(r['kind'])<2];query=[r for r in operations if int(r['kind'])==2];pairs=table(p+'.pairs.csv')
    assert len(operations)==2*len(expected_batches)+160 and len(query)==160 and len(pairs)==len(expected_batches)
    for entry,d,i,pair in zip(expected_batches,up[::2],up[1::2],pairs):
        phase,begin,count=entry['phase'],entry['begin'],entry['count'];assert (int(d['kind']),int(i['kind']))==(0,1)
        for row in (d,i):assert int(row['phase'])==phase and int(row['rows'])==count and int(row['slot'])==-1
        assert int(d['mutation'])==begin and int(i['mutation'])==begin+count
        assert int(d['n_before'])==int(i['n_after'])==n and int(d['n_after'])==int(i['n_before'])==n-count
        assert int(pair['phase'])==phase and int(pair['mutation'])==begin+count and int(pair['rows'])==count
        assert float(pair['ack_ms'])+1e-9>=float(d['ack_ms'])+float(i['ack_ms'])
    for row,q in zip(query,qr[8:]):
        assert all(int(row[key])==int(q[key]) for key in ('phase','slot','mutation')) and float(row['ack_ms'])==float(q['ack_ms']) and int(row['n_before'])==int(row['n_after'])==n
    for row in operations:
        assert all(np.isfinite(float(row[key])) and float(row[key])>=0 for key in ('ack_ms','stats_submit_ms','stats_tail_inclusive_ms')) and float(row['ack_ms'])>0
    structure=table(truth/'structure.csv');updates=table(p+'.updates.csv');assert len(updates)==len(structure)==len(expected_batches)
    for row,e in zip(updates,structure):
        moves=int(e['moves']);assignments=int(e['assignments']);count=int(e['count']);native=v==0 or count==1
        assert int(row['rows'])==count and int(row['moves'])==moves and int(row['syncs'])==1
        assert float(row['capture_ms'])>=0 and float(row['plan_ms'])>=0 and np.isfinite(float(row['capture_ms'])+float(row['plan_ms']))
        payload=(moves if native or v in (1,2) else assignments)*3840;assert int(row['payload'])==payload
        if native:expected_values=(0,0,moves,0,0)
        elif v==1:expected_values=(0,int(e['levels']),int(e['levels']),0,0)
        elif v==2:expected_values=(0,int(e['levels']),int(moves>0),int(e['levels']),moves*8)
        else:expected_values=(assignments,0,int(assignments>0),int(assignments>1),assignments*8 if assignments>1 else 0)
        assert tuple(int(row[key]) for key in ('assignments','levels','copy_APIs','kernels','metadata'))==expected_values,('update execution ledger',row,e)
    assert sum(int(e['moves']) for e in structure)==int(swaps[0])
    final=load(p+'.final.json');capacity=load(p+'.capacity.json');assert final['passed'] and final['live']==n and final['all_vector_bytes_compared']==n*3840
    assert capacity==dict(passed=True,all_allocated_vector_bytes_compared=n*3840,includes_retired_rows=True)
    if diag==2:
        ack=load(p+'.ack_oracle.json');assert ack['passed'] and ack['ACK_callbacks']==1+len(up) and ack['mutations_replayed']==2*k and ack['changed_rows_checked']==k+sum(int(e['changed_destinations']) for e in structure)
    stages=table(p+'.stages.csv');assert len(stages)==168*4
    stage_visits=[]
    for i,count in enumerate(counts):
        live=n;visits=0
        for s,increment in enumerate((128,128,256,448)):
            row=stages[i*4+s];assert int(row['invocation'])==i and int(row['stage'])==s+1 and int(row['input'])==live
            assert 0<=int(row['output'])<=live;visits+=live*increment;live=int(row['output'])
        assert live==count;stage_visits.append(visits)
    means=array(p+'.means.f32','<f4').reshape(5,960);initial=array(Path(reg['derived_parent'])/'inputs/initial_mean.f32','<f4');assert all(np.array_equal(mu.view('<u4'),initial.view('<u4')) for mu in means)
    ordering=table(p+'.ordering.csv');assert len(ordering)==168 and [int(r['invocation']) for r in ordering]==list(range(168))
    sums={name:sum(float(row['ack_ms']) for row in operations if int(row['kind'])==kind) for name,kind in (('delete',0),('insert',1),('query',2))}
    meta=load(p+'.meta.json')
    fixed=dict(variant=j['variant'],batch_limit=b,trace=j['trace'],mode=2,N=n,D=960,B=1,diagnostic=diag,formal_queries=160,warmup_queries=8,replacements=k,update_batches=len(up),point_updates=2*k,insert_H2D_request_bytes=k*3840,sequential_reference_swap_bytes=int(swaps[0])*3840,statistics_rows=0,statistics_calls=0,rebuilds=0,client_complete_items=at,raw_device_bytes=n*3840,extra_update_workspace_bytes=4096 if v>=2 else 0)
    assert all(meta[key]==value for key,value in fixed.items()),('metadata contract',fixed,meta)
    assert abs(meta['service_ms']-meta['events_ms']-meta['release_ms'])<1e-7 and meta['release_ms']>=0
    assert abs(meta['query_ms']-sums['query'])<1e-7 and abs(meta['update_ms_including_statistics']-sums['delete']-sums['insert'])<1e-7
    assert meta['other_ms']>=-1e-7 and abs(meta['events_ms']-sum(sums.values())-meta['other_ms'])<1e-7
    assert meta['known_device_owned_peak_bytes']==meta['raw_device_bytes']+meta['base_query_device_bytes']+meta['extra_update_workspace_bytes']
    return dict(passed=True,job=j,metadata=meta,complete_queries=168,formal_queries=160,complete_hit_records=at,false_negatives=0,false_positives=0,native_squared_bits=True,internal_FP64_bits=diag==2,max_native_scaled_error=maxerr,actual_mutation_witnesses=2*k,independent_full_final_maps=True,all_allocated_bytes_compared=n*3840,query_coordinate_visits=stage_visits,operation_totals_ms=sums,native_moves=int(swaps[0]),final_assignments=sum(int(e['assignments']) for e in structure),expected_RAW=sum(int(e['RAW']) for e in structure),expected_WAW=sum(int(e['WAW']) for e in structure),ledger={key:sum(float(row[key]) for row in updates) for key in ('copy_APIs','kernels','metadata','payload','syncs','capture_ms','plan_ms')},raw_outputs={f.name:dict(bytes=f.stat().st_size,sha256=sha(f)) for f in prefix.parent.glob(prefix.name+'.*') if f.is_file()})
