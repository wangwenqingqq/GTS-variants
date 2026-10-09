#!/usr/bin/env python3
"""Independent ordered-FP64 exhaustive oracle; no tree pruning or early termination."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np

if not __debug__:
    raise RuntimeError("Assertions must remain enabled; Python -O is unsupported")


def load(path):
    path = Path(path)
    if path.suffix == '.f32bin':
        with path.open('rb') as f:
            d, n, m = struct.unpack('<iii', f.read(12))
        assert m == 2 and path.stat().st_size == 12 + 4 * n * d
        return np.memmap(path, dtype='<f4', mode='r', offset=12, shape=(n, d))
    return np.loadtxt(path, skiprows=1, dtype=np.float32, ndmin=2)


def scores(data, physical, query, chunk=4096):
    result = np.empty(len(physical), dtype=np.float64)
    q = np.asarray(query, dtype=np.float64)
    for start in range(0, len(physical), chunk):
        x = np.asarray(data[np.asarray(physical[start:start + chunk])], dtype=np.float64)
        acc = np.zeros(len(x), dtype=np.float64)
        for j in range(x.shape[1]):
            delta = np.subtract(x[:, j], q[j])
            acc = np.add(acc, np.multiply(delta, delta))
        result[start:start + len(x)] = acc
    return result


def check(data_path, events_path, prefix, radius, k, expected_mode=None):
    data = load(data_path)
    ops = np.loadtxt(events_path, skiprows=1, dtype=np.int64, ndmin=2)
    prefix = str(prefix)
    assert Path(prefix+'.ids.i32').stat().st_size%4==0 and Path(prefix+'.dist.f32').stat().st_size%4==0, 'trailing output bytes'
    actual_ids = np.fromfile(prefix + '.ids.i32', dtype='<i4')
    actual_fields = np.fromfile(prefix + '.dist.f32', dtype='<f4')
    with open(prefix + '.queries.csv') as f:
        rows = list(csv.DictReader(f))
    base = np.arange(len(data)); alive = np.ones(len(base), dtype=bool); buffer = []
    with open(prefix+'.ops.csv') as f:
        state_rows=list(csv.DictReader(f))
    assert len(state_rows)==len(ops),'missing operation ACK states'
    offset = qi = rebuilds = 0
    cutoff = np.float64(np.float32(radius)) ** 2
    for step, (flag, index) in enumerate(ops):
        before=(len(base),len(buffer))
        if flag == 0:
            buffer.append(int(base[index]))
            if len(buffer) == 10:
                base = np.concatenate([base[alive], np.asarray(buffer,dtype=np.int64)]); alive = np.ones(len(base), dtype=bool)
                buffer = []; rebuilds += 1
        elif flag == 1:
            positions = np.flatnonzero(alive)
            if index < len(positions):
                alive[positions[index]] = False
            else:
                buffer.pop(index - len(positions))
        else:
            physical = np.concatenate([base[alive], np.asarray(buffer,dtype=np.int64)])
            sq = scores(data, physical, data[base[index]])
            fields = np.sqrt(sq).astype(np.float32)
            if flag == 2:
                wanted = np.flatnonzero(sq <= cutoff)
            else:
                wanted = np.lexsort((np.arange(len(sq)), sq))[:k]
            ei = wanted.astype(np.int32); ef = fields[wanted]
            if flag == 3 and len(ei) < k:
                ei = np.pad(ei, (0, k-len(ei)), constant_values=-1)
                ef = np.pad(ef, (0, k-len(ef)), constant_values=np.inf)
            row = rows[qi]; qi += 1
            assert [int(row[key]) for key in ('step', 'qid', 'tree_size', 'buffer', 'offset', 'count')] == [step, index, len(base), len(buffer), offset, len(ei)]
            ai = actual_ids[offset:offset+len(ei)]; af = actual_fields[offset:offset+len(ei)]
            if flag == 2:
                # Public range order is the tree's canonical leaf order, then buffer;
                # compare membership/fields here and full order across A/B/C below.
                assert len(set(map(int, ai))) == len(ai)
                order = np.argsort(ai); ai, af = ai[order], af[order]
            assert np.array_equal(ai, ei), (step, 'complete membership/order', ai[:16], ei[:16])
            assert np.array_equal(af.view(np.uint32), ef.view(np.uint32)), (step, 'FP32 field bits')
            offset += len(ei)
        state=state_rows[step]
        assert [int(state[key]) for key in ('step','flag','base_before','buffer_before','base_after','buffer_after')]==[step,flag,*before,len(base),len(buffer)],'operation state mismatch'
        assert all(math.isfinite(float(state[key])) and float(state[key])>=0 for key in ('ack_ms','rebuild_ms')), 'invalid operation timing receipt'
    summary=json.loads(Path(prefix+'.summary.json').read_text())
    mirror=json.loads(Path(prefix+'.unified.json').read_text())
    region=json.loads(Path(prefix+'.region.json').read_text())
    numeric=json.loads(Path(prefix+'.numeric.json').read_text())
    assert summary['observe'] and summary['results']==offset
    assert mirror['refreshes']==numeric['refreshes']==numeric['epoch']==rebuilds+1
    assert not mirror['final_owned_bytes'] and not region['final_owned_bytes'] and not numeric['final_bytes']
    assert region['mode'] in (0,1) and mirror['knn_mode'] in ('FULL','BOUND')
    if expected_mode is not None:
        assert (region['mode'],mirror['knn_mode'])==expected_mode, 'execution mode differs from requested A/B/C'
    if region['mode']:
        assert region['refreshes']==rebuilds+1
        assert [r['epoch'] for r in region['refresh_rows']]==list(range(1,rebuilds+2))
    else:assert region['refreshes']==0
    assert mirror['neighbor_items_per_buffer']==((mirror['capacity']+255)//256)*k
    assert qi == len(rows) and offset == len(actual_ids) == len(actual_fields)
    return dict(queries=qi, rebuilds=rebuilds, output_items=offset,
                membership=True, field_bits=True, knn_order=True, operation_states=True, published_refreshes=True, released_owned_buffers=True,
                range_order='requires same-input cross-mode byte equality', oracle='CPU ordered dimension-wise FP64 exhaustive chunked')


def coverage(data_path, events_path, log_path):
    data=load(data_path)
    ops=np.loadtxt(events_path,skiprows=1,dtype=np.int64,ndmin=2)
    base=np.arange(len(data));alive=np.ones(len(base),dtype=bool);buffer=[];states=[base.copy()]
    for flag,index in ops:
        if flag==0:
            buffer.append(int(base[index]))
            if len(buffer)==10:
                base=np.concatenate([base[alive],np.asarray(buffer,dtype=np.int64)])
                alive=np.ones(len(base),dtype=bool);buffer=[];states.append(base.copy())
        elif flag==1:
            positions=np.flatnonzero(alive)
            if index<len(positions):alive[positions[index]]=False
            else:buffer.pop(index-len(positions))
    lines=Path(log_path).read_text().splitlines()
    trees=[json.loads(s[len('U0_TREE '):]) for s in lines if s.startswith('U0_TREE ')]
    bounds=[json.loads(s[len('TARGET_BOUNDS '):]) for s in lines if s.startswith('TARGET_BOUNDS ')]
    assert len(trees)==len(bounds)==len(states),'missing audited rebuild'
    pairs=nodes=0
    for epoch,(tree,bound,base) in enumerate(zip(trees,bounds,states),1):
        assert tree['n']==len(base) and bound['epoch']==epoch
        order=np.asarray(tree['order'],dtype=np.int64)
        assert np.array_equal(np.sort(order),np.arange(len(base)))
        records={r[0]:r for r in tree['nodes']};intervals={r[0]:r[1:] for r in bound['members']}
        for nid,(lo,hi) in intervals.items():
            _,pivot,_,count,start,_=records[nid]
            assert count>0 and 0<=pivot<len(base)
            q=np.asarray(data[base[pivot]],dtype=np.longdouble)
            members=base[order[start:start+count]]
            for begin in range(0,len(members),4096):
                x=np.asarray(data[members[begin:begin+4096]],dtype=np.longdouble)
                diff=x-q;norm=np.sqrt(np.sum(diff*diff,axis=1,dtype=np.longdouble))
                assert np.all(norm>=np.longdouble(lo)) and np.all(norm<=np.longdouble(hi)),(epoch,nid,'actual-member interval coverage')
                pairs+=len(x)
            nodes+=1
    return dict(epochs=len(states),nodes=nodes,member_pivot_pairs=pairs,all_member_coverage=True,
                crosscheck='CPU long-double norm for every emitted member interval; directed-interval proof in DESIGN.md')


def case(data, path, operations):
    path.mkdir(parents=True, exist_ok=False)
    with (path/'data.f32bin').open('wb') as f:
        f.write(struct.pack('<iii',data.shape[1],len(data),2));f.write(np.asarray(data,dtype='<f4').tobytes())
    (path/'events.txt').write_text(str(len(operations))+'\n'+''.join(f'{a} {b}\n' for a,b in operations))


TARGET_DATA_SHA256='f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'


def verify_target_data(path):
    data=load(path)
    assert data.shape==(1000000,960), 'registered GIST shape'
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8<<20),b''):digest.update(chunk)
    assert digest.hexdigest()==TARGET_DATA_SHA256, 'registered original FP32 GIST hash'
    return data


def event_case(path, operations):
    path.mkdir(parents=True,exist_ok=False)
    (path/'events.txt').write_text(str(len(operations))+'\n'+''.join(f'{a} {b}\n' for a,b in operations))


def fixtures(data_path, work, radius):
    x=verify_target_data(data_path)
    for n in (255,256,257,1023,1024,1025,4096,65536):
        case(x[:n],work/f'gist{n}',boundary_operations(n))
    # Separate synthetic zeros/threshold cases do not masquerade as GIST.
    for n in (255,256,257,1023,1024,1025):
        z=np.zeros((n,960),dtype=np.float32);z[:,0]=np.arange(n,dtype=np.float32)%5
        z[0,0]=0;z[1,0]=radius;z[2,0]=np.nextafter(np.float32(radius),np.float32(-np.inf))
        z[3,0]=np.nextafter(np.float32(radius),np.float32(np.inf))
        case(z,work/f'edge{n}',boundary_operations(n))
    extreme=np.zeros((255,960),dtype=np.float32)
    extreme[:,0]=np.finfo(np.float32).max;extreme[0,0]=-np.finfo(np.float32).max
    case(extreme,work/'extreme255',boundary_operations(255))
    # Use the registered binary and the parent's ties8 data in place; do not copy N1M.
    event_case(work/'million',[(2,0),(3,0),(0,0),(2,0),(3,0),(1,0),(2,0),(3,0)]
               +[(0,0)]*9+[(2,0),(3,0)])
    event_case(work/'growth',[(0,0)]*1010+[(2,0),(3,0)])


def boundary_operations(n):
    q = [(2,0),(3,0)]
    # Deleted pivot/query rows retain coordinates; buffer first and last deletion.
    return (q+[(1,n//2)]+q+[(0,n//2)]+q+[(1,n-1)]+q
            +[(0,0),(0,n-1)]+q+[(1,n)]+q+[(1,n-1)]+q
            +[(0,0)]*10+q)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('fixtures','check'))
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--work',type=Path)
    p.add_argument('--events',type=Path)
    p.add_argument('--prefix',type=Path)
    p.add_argument('--radius',type=float,default=struct.unpack('<f',struct.pack('<I',0x3f34a3d8))[0])
    p.add_argument('--k',type=int,default=8)
    a=p.parse_args()
    if a.stage=='fixtures':
        if a.work is None:p.error('--work is required for fixtures')
        fixtures(a.data,a.work,a.radius)
    else:
        if a.events is None or a.prefix is None:p.error('--events and --prefix are required for check')
        print(json.dumps(check(a.data,a.events,a.prefix,a.radius,a.k),indent=2))
