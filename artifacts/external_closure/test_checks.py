#!/usr/bin/env python3
"""Regression checks for full-output gates and exact-source overlay isolation."""
import argparse,importlib.util,json,tempfile,struct,copy,csv,sys
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import numpy as np
import qualify
from prepare_tree import prepare,HERE

def check_payloads():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);x=np.array([[0.,0.],[0.,0.],[1.,0.]],np.float32)
        data=root/'x.f32bin';data.write_bytes(struct.pack('<iii',2,3,2)+x.tobytes())
        req=root/'queries.txt';req.write_text('1\n1 0 0 8\n');out=root/'out'
        Path(str(out)+'.queries.csv').write_text('task,query,qid,count,offset,ack_ms\nrange,0,0,2,0,1\n')
        np.array([0,1],'<i4').tofile(str(out)+'.ids.i32');np.zeros(2,'<f4').tofile(str(out)+'.dist.f32')
        assert qualify.check(data,req,out)['passed']
        try:qualify.check(data,req,out,native_squared_required=True)
        except AssertionError:pass
        else:raise AssertionError('missing native scores accepted')
        path=Path(str(out)+'.ids.i32');original=path.read_bytes();path.write_bytes(original+b'x')
        try:qualify.check(data,req,out)
        except AssertionError:pass
        else:raise AssertionError('trailing bytes accepted')
        path.write_bytes(original)
        np.array([0,2],'<i4').tofile(str(out)+'.ids.i32');assert not qualify.check(data,req,out)['passed']
        np.array([0,0],'<i4').tofile(str(out)+'.ids.i32');assert not qualify.check(data,req,out)['passed']
        np.array([0,1],'<i4').tofile(str(out)+'.ids.i32');np.array([0.,float('nan')],'<f4').tofile(str(out)+'.dist.f32');assert not qualify.check(data,req,out)['passed']
        Path(str(out)+'.ids.i32').write_bytes(b'')
        try:qualify.check(data,req,out)
        except AssertionError:pass
        else:raise AssertionError('truncation accepted')

def rejects(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('incomplete evidence accepted')

def check_admission():
    from verify_a import EXPECTED,required_receipts,edge_matrix,HERE,sha
    rows=[dict(case=f'{folder}/{name}',runtime_valid=valid) for folder,jobs in EXPECTED.items() for name,valid in jobs.items()]
    required_receipts(rows)
    rejects(lambda:required_receipts(rows[:-1]))
    broken=copy.deepcopy(rows);broken[-1]['runtime_valid']=False
    rejects(lambda:required_receipts(broken))
    broken=copy.deepcopy(rows);broken[-1]=broken[0]
    rejects(lambda:required_receipts(broken))
    edge=dict(passed=True,inclusive_adapter=False,adapter_sha256=sha(HERE/'native_cpu.py'),checker_sha256=sha(HERE/'cpu_edges.py'),rows=[])
    for leaf in (32,128,512):
      for n in (0,1,7,513):
       for repeat in range(32):
        for task,radius in [('knn',None),*[( 'range',r) for r in (-1.,0.,1.,100.)]]:
         edge['rows'].append(dict(method='CPU_KD',leaf=leaf,N=n,repeat=repeat,task=task,radius=radius,passed=True))
    edge_matrix(edge,('CPU_KD',),False)
    broken=copy.deepcopy(edge);broken['rows'].pop();rejects(lambda:edge_matrix(broken,('CPU_KD',),False))
    broken=copy.deepcopy(edge);broken['adapter_sha256']='0'*64;rejects(lambda:edge_matrix(broken,('CPU_KD',),False))
    from cpu_edges import complete_knn
    sq=np.arange(7,dtype=np.float64)**2;ids=np.arange(7,dtype=np.int32);fields=np.arange(7,dtype=np.float32)
    assert complete_knn(ids,fields,sq,sq)
    for bad in (np.full(7,np.nan),fields[:-1],fields[::-1]):assert not complete_knn(ids,bad,sq,sq)
    assert not complete_knn(ids[::-1],fields[::-1],sq[::-1],sq)
    assert complete_knn(ids[:0],fields[:0],sq[:0],sq[:0])
    assert not complete_knn(ids[:0],fields[:1],sq[:0],sq[:0])

def check_cpu_order():
    sys.path.insert(0,str(qualify.cpu.HERE.parent/'unified_target_workflow/phase_b'))
    import oracle,campaign
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);x=np.c_[np.arange(32,dtype=np.float32),np.zeros(32,np.float32)]
        data=root/'x.f32bin';data.write_bytes(struct.pack('<iii',2,32,2)+x.tobytes())
        (root/'SNAPSHOT.json').write_text(json.dumps(dict(queries=[dict(physical_qid=i) for i in range(32)])))
        for order in (('knn','range'),('range','knn')):
            out=root/('_'.join(order));rows=[];parts=[];offset=0
            for task in order:
                for qi in range(32):
                    sq=((x.astype(np.float64)-x[qi])**2).sum(axis=1)
                    ids=np.argsort(sq,kind='stable')[:8] if task=='knn' else np.array([qi])
                    parts.append((ids,np.sqrt(sq[ids]),sq[ids]))
                    rows.append(dict(task=task,query=qi,qid=qi,count=len(ids),offset=offset));offset+=len(ids)
            with Path(str(out)+'.queries.csv').open('w') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            for i,suffix,dtype in ((0,'.ids.i32','<i4'),(1,'.dist.f32','<f4'),(2,'.native_squared.f64','<f8')):
                np.concatenate([r[i] for r in parts]).astype(dtype).tofile(str(out)+suffix)
            scores=lambda data,ids,q:((data[ids].astype(np.float64)-q)**2).sum(axis=1)
            with patch.object(campaign,'verify_cpu_library',return_value={'unit_test':True}),patch.object(oracle,'install',return_value=scores):
                qualify.cpu.check(SimpleNamespace(data=data,snapshot=root,output=out,library=None))
            assert json.loads(Path(str(out)+'.quality.json').read_text())['passed']

def check_overlay(upstream):
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp)/'prepared';prepare(upstream,out);source=upstream/'Source Code/GPU-Tree/include'
        for p in source.glob('*.cuh'):
            if p.name not in ('search.cuh','bplus_tree.cuh'):assert p.read_bytes()==(out/'include'/p.name).read_bytes()
        s=(out/'include/search.cuh').read_bytes().decode('utf-8',errors='surrogateescape')
        for name in ('isSatisfied','tree_num','tree_sum_prefix','node_sum_prefix'):
            s=s.replace(f'#ifndef CLOSURE_REUSE\n        cudaFree({name});\n#endif',f'cudaFree({name});')
        s=s.replace('cudaFree(pivot_flag);\n        cudaFree(tree_filter);\n        cudaFree(tree_filter_prefix);','cudaFree(pivot_flag);')
        s=s.replace('tree_idx++;\n#ifdef CLOSURE_TAIL_SAFE\n                if (i + 1 < isSatisfied[bid * PNUM + id])\n#endif\n                nid = node_sum_prefix[tree_idx];','tree_idx++;\n\t\t\t\tnid = node_sum_prefix[tree_idx];')
        assert s.encode('utf-8',errors='surrogateescape')==(source/'search.cuh').read_bytes()
        s=(out/'include/bplus_tree.cuh').read_bytes().replace(b'closure_capture_nodes(T, total_node_num);\n\t',b'')
        assert s==(source/'bplus_tree.cuh').read_bytes()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path);a=p.parse_args();check_payloads();check_admission();check_cpu_order()
    if a.upstream:check_overlay(a.upstream)
    print('PASS complete membership, duplicates, nonfinite/truncation rejection and optional exact reversible source overlay')
