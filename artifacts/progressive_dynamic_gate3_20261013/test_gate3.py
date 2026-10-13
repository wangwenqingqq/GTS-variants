"""Small CPU-only regression check: IDs, duplicates, decision/timer boundaries."""
import csv,tempfile
from pathlib import Path
import numpy as np
from trace import read,save,load,replay,freeze_b
from prepare import fixture,references
from quality import state_proof,query,payload,check
from analyze import summary,classify,gate_b
from campaign import jobs,command
def rejects(fn):
    try:fn()
    except (AssertionError,IndexError,ValueError):return
    raise AssertionError('invalid proof accepted')
def csvwrite(p,rows):
    with Path(p).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def fake_outputs(w,data,trace,prefix,label,cap):
    (e,n,d),rr,_=load(trace);src=read(str(trace)+'.source.json');cache=w/'fixtures/cache';x=np.memmap(data,dtype='<f4',offset=12,shape=(n,d),mode='r');cache.mkdir(exist_ok=True)
    for q in {q for f,o,q in src if f>=2}:
        score=np.zeros(n)
        for j in range(d):diff=x[:,j].astype(float)-float(x[q,j]);score=score+diff*diff
        score.astype('<f8').tofile(cache/f'{q}.f64')
    references(w,data,trace,cache,1.,label)
    phy,pos,states,_=replay(n,rr);ownership=[s for s in states if s['flag']<2];csvwrite(str(prefix)+'.ownership.csv',ownership);ops=[];qr=[];ids=[];sq=[];origin=np.arange(cap);alive=np.zeros(cap,bool);alive[:n]=True
    for step,((f,o),(_,_,q)) in enumerate(zip(rr,src)):
        if f==0:origin[o]=q;alive[o]=True
        elif f==1:alive[o]=False
        else:
            live=np.flatnonzero(alive);score=np.fromfile(cache/f'{q}.f64','<f8')[origin[live]];pick=np.flatnonzero(score<=1.) if f==2 else np.lexsort((live,score))[:8]
            qr.append(dict(step=step,flag=f,count=len(pick),offset=len(ids)));ids.extend(live[pick].tolist());sq.extend(score[pick].tolist())
        ops.append({k:states[step][k] for k in ('step','flag','n_before','n_after')}|dict(ack_ms=.1,rebuild_ms=0))
    csvwrite(str(prefix)+'.queries.csv',qr);csvwrite(str(prefix)+'.ops.csv',ops)
    np.array(ids,'<i4').tofile(str(prefix)+'.ids.i32');np.sqrt(np.array(sq,'<f4')).astype('<f4').tofile(str(prefix)+'.dist.f32');np.array(sq,'<f4').astype('<f8').tofile(str(prefix)+'.native_squared.f64')
    np.array(phy,'<i4').tofile(str(prefix)+'.physical.i32');np.pad(pos,(0,cap-len(pos)),constant_values=-1).astype('<i4').tofile(str(prefix)+'.reverse.i32')
    save(str(prefix)+'.final.proof.json',dict(passed=True,all_vector_bytes_bitwise_compared=len(phy)*d*4,physical_rows=len(phy),reverse_entries=cap))
    swaps=sum(s['moved']>=0 for s in states);inserts=sum(f==0 for f,o in rr)
    save(str(prefix)+'.meta.json',dict(variant='D0',dry=False,capacity=cap,final_live=len(phy),rebuilds=0,norm_updates=1+inserts,swap_deletes=swaps,inserted_H2D_bytes=inserts*d*4,swap_D2D_bytes=swaps*(d*4+4),client_payload_bytes=16*len(ids),vector_storage_bytes=cap*d*4,norm_storage_bytes=cap*4,reverse_map_capacity_bytes=cap*4,progressive_state_bytes=0,query_owned_bytes=cap*25+d*4+4+1024,cub_scratch_bytes=1024,trace_ms=e*.1+.1,events_ms=e*.1,release_ms=.1,offline_final_and_probe_ms=1.,setup_ms=1.,context_ms=1.))
def run():
    assert classify(.8,.5,1.51,1,.8,6)=='UPDATE_REGRESSION'
    assert classify(.8,.5,1,1,.8,6,False)=='NO_GO_DYNAMIC_PROGRESSIVE'
    assert classify(.85,.60,1.5,1.5,.919999,5)=='GO_DYNAMIC_PROGRESSIVE'
    for t,r,c,w in ((.86,.6,.9,6),(.9,.6,.9,6),(.8,.61,.9,6),(.8,.6,.92,6),(.8,.6,.9,4)):assert classify(t,r,1,1,c,w)=='UNCLASSIFIED'
    assert classify(.95,.6,1,1,.9,6)=='NO_GO_DYNAMIC_PROGRESSIVE' and classify(.8,.750001,1,1,.9,6)=='NO_GO_DYNAMIC_PROGRESSIVE'
    assert gate_b(.65,1.25,1.25) and not gate_b(.65,1.250001,1)
    v=summary([{'D0':10.,'D1':5.}]*6);assert v['ratio']==.5 and v['wins']==6 and np.allclose(v['paired_CI95'],[.5,.5])
    rows=[(0,3),(1,1),(2,-1),(1,3),(0,4),(3,-1)];p,rev,states,snaps=replay(3,rows);assert p==[0,2,4] and rev.tolist()==[0,-1,1,-1,2]
    changes=[s for s in states if s['flag']<2];state_proof(3,rows,changes,5)
    bad=[{**s,'moved':0} if s['flag']==1 else s for s in changes];rejects(lambda:state_proof(3,rows,bad,5))
    rejects(lambda:replay(3,[(1,1),(1,1)]));rejects(lambda:replay(3,[(0,4)]));rejects(lambda:replay(3,[(2,0)]))
    # Distinct logical occurrences of identical vectors must both be delivered.
    ids=np.array([4,0]);wanted=np.array([0,4]);score=np.array([0.,0.]);query(ids,np.zeros(2),np.zeros(2),wanted,score,None,np.empty(0),2)
    rejects(lambda:query(np.array([0,0]),np.zeros(2),np.zeros(2),wanted,score,None,np.empty(0),2))
    rejects(lambda:query(np.array([0,1]),np.zeros(2),np.zeros(2),wanted,score,None,np.empty(0),2))
    with tempfile.TemporaryDirectory() as tmp:
        w=Path(tmp);data,trace=fixture(w);(e,n,d),rr,_=load(trace);assert (e,n,d)==(160,65,960);replay(n,rr)
        _,warm,_=load(str(trace)+'.warmup');replay(n,warm)
        (w/'references').mkdir();out=w/'fake';fake_outputs(w,data,trace,out,'fixture',n+40);fake_outputs(w,data,str(trace)+'.warmup',Path(str(out)+'.warmup'),'fixture.warmup',n+40);save(str(out)+'.scope.json',dict(warmup_events=19,warmup_queries=8))
        good=check(out,dict(label='cpu_only',fixture=True,mode='D0'),w,{})
        assert good['measured']['queries']==80 and good['warmup']['queries']==8 and good['measured']['updates']==80
        # A logical/live-rank double conversion has valid shapes but wrong IDs.
        original=Path(str(out)+'.ids.i32').read_bytes();v=np.frombuffer(original,dtype='<i4').copy();v[-1]=1000;v.tofile(str(out)+'.ids.i32');rejects(lambda:check(out,dict(label='cpu_only',fixture=True,mode='D0'),w,{}));Path(str(out)+'.ids.i32').write_bytes(original)
        # A lightweight frozen-pool surrogate exercises B without the real data.
        x=np.zeros((300,960),'<f4');x[:,0]=np.arange(300);dat=w/'large.f32bin';dat.write_bytes(np.array([960,300,2],'<i4').tobytes()+x.tobytes());a=w/'A';flags=[2]*128+[3]*128
        Path(str(a)+'.logical').write_text('256 300 960\n'+''.join(f'{f} -1\n' for f in flags));np.array(x[:256]).tofile(str(a)+'.vectors.f32');save(str(a)+'.source.json',[(f,-1,i) for i,f in enumerate(flags)])
        b=freeze_b(dat,a,w/'B');(_,nn,_),br,_=load(w/'B');assert b['counts']==[400,400,100,100] and len(br)==1000 and b['max_live']-nn==1 and b['min_live']==nn
        p,rv,states,snaps=replay(nn,br);assert len(snaps)==4 and sum(s['moved']>=0 for s in states)>0
        state_proof(nn,br,[s for s in states if s['flag']<2],nn+400)
        prefix=w/'out'
        for s,dt in (('.ids.i32','<i4'),('.dist.f32','<f4'),('.native_squared.f64','<f8')):np.zeros(1,dt).tofile(str(prefix)+s)
        payload(prefix);Path(str(prefix)+'.ids.i32').write_bytes(b'\0'*5);rejects(lambda:payload(prefix))
    assert sum(len(jobs(s)) for s in ('qualification','A','B','B_probes'))==29
    assert jobs('A')[0]['mode']=='D0' and jobs('A')[2]['mode']=='D1' and len(jobs('qualification'))==10
    cmd=command(dict(mode='D0',fixture=True),Path('/scratch/work'),{},Path('/scratch/output'));assert cmd[5]=='/dev/null' and cmd[6]=='0'
    assert command(dict(mode='D1',workload='A',dry=True),Path('/scratch/work'),dict(data='GIST',radius=.7),Path('/scratch/output'))[5]=='/scratch/work/pool32.txt'
    print('PASS: full-state induction,one-map ID semantics,duplicate multiplicity,tail bytes,gray/update priority,B freeze/budget')
if __name__=='__main__':run()
