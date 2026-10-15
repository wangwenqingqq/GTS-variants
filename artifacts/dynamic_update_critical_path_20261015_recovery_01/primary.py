"""Lossless compact scalar ledger; native coordinates/IDs stay outside Git."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from quality import operator_group
from analyze import run

SERVICE_FIELDS=('service_ms','events_ms','release_ms','query_ms','update_ms_including_statistics','other_ms','cpu_events_user_s','cpu_events_system_s')


def compact(job,checked):
    result=dict(job=job)
    if job['kind']=='micro':
        kind={'I':1,'D':0,'R':2}[job['op']];rows=[r for r in checked['operator_samples'] if int(r['kind'])==kind]
        result['samples']=[[float(r['ack_ms']),float(r['delete_ms']),float(r['insert_ms']),int(r['D2D_bytes'])//3840] for r in rows]
        result['metadata']=checked['metadata']
    elif job['kind']=='service':result['parent_quality']=dict(metadata={k:checked['parent_quality']['metadata'][k] for k in SERVICE_FIELDS})
    else:
        assert job['kind']=='copy';result['samples']=[[int(r['round']),int(r['kind']),int(r['bytes']),float(r['ack_ms'])] for r in checked['samples']]
    return result


def expand(process):
    job=process['job'];out=dict(job=job)
    if job['kind']=='micro':
        b=job['batch'];op=('I','D','R').index(job['op']);rows=[]
        for index,(ack,delete,insert,swaps) in enumerate(process['samples']):
            assert isinstance(swaps,int) and 0<=swaps<=b
            def native(kind,time):
                return dict(sample=index,kind=kind,rows=b,ack_ms=time,delete_ms=time if kind==0 else 0,
                    insert_ms=time if kind==1 else 0,copy_calls=swaps if kind==0 else 1,H2D_bytes=b*3840 if kind==1 else 0,
                    D2D_bytes=swaps*3840 if kind==0 else 0,sync_calls=1)
            if op==0:assert ack==insert and delete==0 and swaps==0;group=[native(1,ack)]
            elif op==1:assert ack==delete and insert==0;group=[native(0,ack)]
            else:
                pair=dict(sample=index,kind=2,rows=b,ack_ms=ack,delete_ms=delete,insert_ms=insert,
                    copy_calls=swaps+1,H2D_bytes=b*3840,D2D_bytes=swaps*3840,sync_calls=2)
                group=[native(0,delete),native(1,insert),pair]
            operator_group(group,op,index,b);rows.extend(group)
        out['operator_samples']=rows
    elif job['kind']=='service':out['parent_quality']=process['parent_quality']
    else:out['samples']=[dict(round=r,kind=k,bytes=b,ack_ms=t) for r,k,b,t in process['samples']]
    return out


def analyze_compact(processes):return run([expand(p) for p in processes])


def test():
    job=dict(kind='micro',op='R',batch=32,K=32)
    source=dict(job=job,samples=[[5.1,3.,2.,20]])
    assert compact(job,dict(operator_samples=expand(source)['operator_samples'],metadata={}))['samples']==source['samples']
    bad=dict(job=job,samples=[[1.,3.,2.,20]])
    try:expand(bad)
    except AssertionError:pass
    else:raise AssertionError('Invalid paired time admitted')
    print('PASS:lossless scalar codec and corrupt-pair rejection;0 GPU starts')


if __name__=='__main__':test()
