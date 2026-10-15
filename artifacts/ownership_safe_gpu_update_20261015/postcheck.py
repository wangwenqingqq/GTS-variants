"""Stronger offline physical ledger proof from independently replayed mutation witnesses."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import numpy as np
from logical_quality import table

FIELDS=('kind','rows','reference_moves','compiled_rows','copy_APIs','launches','H2D_plan_bytes','H2D_vector_bytes','D2D_bytes','kernel_payload_bytes','syncs','levels')

def expected(group,update):
    b=len(group);assert b and all(int(m[0])==int(group[0][0]) for m in group)
    kind=int(group[0][0]);assert kind in (0,1)
    result={k:0 for k in FIELDS};result.update(kind=kind,rows=b,syncs=1)
    if kind==1:
        result.update(copy_APIs=1,H2D_vector_bytes=b*3840);return result
    n=int(group[0][2]);end=n-b;tail=list(range(end,n));final={};writers={};levels=[];moves=0
    for i,m in enumerate(group):
        before,row,last=map(int,(m[2],m[3],m[4]));assert before==n-i and last==before-1 and 0<=row<=last
        if row==last:continue
        moves+=1;original=tail[last-end]
        if row>=end:tail[row-end]=original
        else:final[row]=original
        level=1+max(writers.get(last,-1),writers.get(row,-1));levels.append(level);writers[row]=level
    final.update({end+i:v for i,v in enumerate(tail) if v!=end+i})
    assert not set(final).intersection(final.values()) and all(end<=v<n for v in final.values())
    result['reference_moves']=moves
    if update=='NATIVE' or b==1:result.update(copy_APIs=moves,D2D_bytes=moves*3840)
    elif update=='WAVES':result.update(copy_APIs=max(levels,default=-1)+1,levels=max(levels,default=-1)+1,D2D_bytes=moves*3840)
    else:
        assert update=='FINAL';count=len(final);assert 0<=count<=moves
        result.update(compiled_rows=count,copy_APIs=int(count>0),launches=int(count>1),H2D_plan_bytes=count*8 if count>1 else 0,
            D2D_bytes=3840 if count==1 else 0,kernel_payload_bytes=count*3840 if count>1 else 0)
    return result

def bind(row,group,update):
    assert set(row)==set(FIELDS);actual={k:int(v) for k,v in row.items()};assert min(actual.values())>=0
    assert actual==expected(group,update),'Per-ACK mutation/physical-ledger mismatch'
    return actual

def check(prefix,job):
    mutations=np.fromfile(str(prefix)+'.mutations.i32',dtype='<i4').reshape(-1,8)
    rows=table(str(prefix)+'.physical.csv');operators=[r for r in table(str(prefix)+'.ops.csv') if int(r['kind'])<2]
    assert len(rows)==len(operators)
    at=job['K'] if job['kind']=='micro' and job['op']=='I' else 0
    if at:assert (mutations[:at,0]==0).all()
    for row,op in zip(rows,operators):
        actual={k:int(v) for k,v in row.items()}
        b=actual['rows'];assert actual['kind']==int(op['kind']) and b==int(op['rows']) and 1<=b<=512
        group=mutations[at:at+b];assert len(group)==b;bind(row,group,job['update'])
        at+=b
    assert at==len(mutations)
    return dict(passed=True,ACKs=len(rows),mutations=len(mutations),every_integer_nonnegative=True,per_ACK_reference_net_levels_and_execution_exact=True)

def test():
    # Three dependent swaps repeatedly overwrite row0;strict final state changes one row.
    chain=np.array([[0,0,8,0,7,7,8,7],[0,7,7,0,6,6,8,6],[0,6,6,0,5,5,8,5]])
    native=expected(chain,'NATIVE');waves=expected(chain,'WAVES');final=expected(chain,'FINAL')
    assert native['copy_APIs']==waves['levels']==3 and final['compiled_rows']==final['copy_APIs']==1 and final['D2D_bytes']==3840
    independent=np.array([[0,0,8,0,7,7,8,7],[0,1,7,1,6,6,8,6]])
    assert expected(independent,'WAVES')['levels']==1 and expected(independent,'FINAL')['compiled_rows']==2
    assert expected(independent,'FINAL')['H2D_plan_bytes']==16
    # The exact checker rejects both false positives found in the original validator.
    for bad in ({**final,'compiled_rows':-1},{**native,'reference_moves':999,'copy_APIs':999,'D2D_bytes':999*3840}):
        try:bind(bad,chain,'FINAL' if bad['compiled_rows']<0 else 'NATIVE')
        except AssertionError:pass
        else:raise AssertionError('Corrupt physical ledger admitted')
    from itertools import permutations
    from model import compile_batch
    cases=0
    for n in range(1,7):
        for b in range(1,n+1):
            for ids in permutations(range(n),b):
                owners=list(range(n));position=list(range(n));mutations=[]
                for id in ids:
                    row=position[id];last=len(owners)-1;moved=owners[-1] if row!=last else -1
                    mutations.append([0,id,len(owners),row,last,moved,n,len(owners)-1])
                    if moved>=0:owners[row]=moved;position[moved]=row
                    owners.pop();position[id]=-1
                oracle=compile_batch(range(n),ids);group=np.array(mutations)
                assert expected(group,'NATIVE')['reference_moves']==len(oracle['commands'])
                wave=expected(group,'WAVES');assert wave['levels']==(max(oracle['levels'],default=-1)+1 if b>1 else 0)
                compiled=expected(group,'FINAL');assert compiled['compiled_rows']==(len(oracle['final']) if b>1 else 0)
                cases+=1
    print(f'PASS:{cases} independent model/counter cases,dependent schedules and corrupt ledger rejection;0 GPU starts')

if __name__=='__main__':test()
