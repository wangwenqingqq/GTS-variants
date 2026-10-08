#!/usr/bin/env python3
"""Independently replay the frozen multiset and audit every retained process."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'region_exec_20261008'))
from audit_closure import integer_oracle, read, sha


def paired(values,orders=None):
    logs=np.log(values); rng=np.random.default_rng(202610081022)
    resamples=rng.integers(0,len(values),(20000,len(values)))
    interval=np.quantile(np.exp(logs[resamples].mean(axis=1)),[.025,.975])
    result=dict(raw_ratios=values,geomean=float(np.exp(logs.mean())),
                CI95=interval.tolist(),wins=sum(x>1 for x in values))
    if orders is not None:
        result.update(base_before=float(np.exp(logs[np.asarray(orders)].mean())),
                      base_after=float(np.exp(logs[~np.asarray(orders)].mean())))
    return result


def validate_qualification(root):
    source=read(root/'SOURCE.json');validation=read(root/'VALIDATION.json')
    assert validation['passed'] and validation['source_sha256']==sha(root/'SOURCE.json')
    for name,digest in source['sources'].items():assert sha(root/'native_timed/source'/name)==digest
    for name,key in (('region_exec','binary_sha256'),('region_counter','counter_binary_sha256'),
                     ('test_region','structural_binary_sha256'),('test_warp','test_warp_binary_sha256'),
                     ('micro_warp','micro_warp_binary_sha256')):
        assert sha(root/'native_timed'/name)==source[key]
    labels=sorted(d.name for d in (root/'runs').iterdir() if not d.name.startswith(('cost_','formal_')))
    assert len(labels)==42
    receipts={}
    for label in labels:
        directory=root/'runs'/label;receipt=read(directory/'receipt.json')
        assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
        for side in ('before','after'):assert not read(directory/(side+'.json'))['apps']
        assert all(not x['foreign'] for x in read(directory/'checks.json'))
        receipts[label]=sha(directory/'receipt.json')
    for row in validation['structural']+[read(root/'MICRO.json')]:
        directory=root/'runs'/row['label']
        for name in ('receipt','stdout','stderr'):
            suffix='json' if name=='receipt' else 'log'
            assert sha(directory/(name+'.'+suffix))==row[name+'_sha256']
        assert sha(root/'registrations'/(row['label']+'.json'))==row['registration_sha256']
    return dict(state='independently_guard_and_hash_audited',qualification_processes=42,
                structural_and_direct_processes=12,mixed_update_processes=24,
                full_counter_processes=5,bounded_micro_processes=1,all_guards_valid=True,
                all_frozen_source_and_binary_hashes_valid=True,
                raw_validation_sha256=sha(root/'VALIDATION.json'),receipt_sha256=receipts)


def validate(root):
    source=read(root/'SOURCE.json'); registration=read(root/'REGISTERED.json')
    assert sha(root/'SOURCE.json')==registration['source_sha256']
    for name,digest in source['sources'].items():
        assert sha(root/'native_timed/source'/name)==digest, name
    for name,digest in registration['input_sha256'].items():
        assert sha(root/name)==digest, name
    for name,digest in read(root/'ADMISSION.json')['evidence_sha256'].items():
        assert sha(root/name)==digest, name
    data=np.loadtxt(root/'data.txt',skiprows=1,dtype=np.int64)
    operations=np.loadtxt(root/'events.txt',skiprows=1,dtype=np.int64).tolist()
    assert data.shape==(1000,128) and len(operations)==12000
    queries,states,rebuilds=integer_oracle(data,operations,read(root/'expected.json')['radius'])
    assert len(queries)==10000 and rebuilds==50
    formal=read(root/'FORMAL_ROWS.json'); cost=read(root/'COST_ROWS.json')
    assert len(formal)==30 and len(cost)==60
    identity=None; receipts={}
    for row in formal+cost:
        label=row['label']; prefix=root/'native_timed'/label
        for suffix,digest in row['outputs'].items():
            assert sha(Path(str(prefix)+suffix))==digest, (label,suffix)
        actual=[row['outputs'][s] for s in ('.ids.i32','.dist.f32','.queries.csv')]
        if identity is None:identity=actual
        assert actual==identity, label
        receipt=read(root/'runs'/label/'receipt.json')
        assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
        assert receipt['binary_sha256']==source['binary_sha256']
        for side in ('before','after'):assert not read(root/'runs'/label/(side+'.json'))['apps']
        assert all(not x['foreign'] for x in read(root/'runs'/label/'checks.json'))
        assert sha(root/'registrations'/(label+'.json'))==row['registration_sha256']
        receipts[label]=sha(root/'runs'/label/'receipt.json')
        ids=np.fromfile(str(prefix)+'.ids.i32',dtype='<i4')
        fields=np.fromfile(str(prefix)+'.dist.f32',dtype='<f4')
        records=list(csv.DictReader(open(str(prefix)+'.queries.csv')))
        assert len(records)==len(queries); offset=0
        for got,want in zip(records,queries):
            step,qid,n,buffer,expected=want
            assert [int(got[k]) for k in ('step','qid','tree_size','buffer')]==[step,qid,n,buffer]
            count=int(got['count']); assert int(got['offset'])==offset and count==len(expected)
            result=dict(zip(map(int,ids[offset:offset+count]),map(bytes,fields[offset:offset+count])))
            assert len(result)==count and result==expected, (label,step)
            offset+=count
        assert offset==len(ids)==len(fields)
        ops=list(csv.DictReader(open(str(prefix)+'.ops.csv')))
        if row['summary']['observe']:
            assert len(ops)==len(states)
            for step,(op,state) in enumerate(zip(ops,states)):
                assert int(op['step'])==step and int(op['flag'])==operations[step][0]
                assert tuple(int(op[k]) for k in ('base_before','buffer_before','base_after','buffer_after'))==state[:4]
                assert (float(op['rebuild_ms'])>0)==state[4]
                assert float(op['ack_ms'])>=float(op['rebuild_ms'])
        else:assert not ops
        assert row['region']['final_owned_bytes']==0 and row['region']['refreshes']==51
    orders=registration['orders']
    for index,order in enumerate(orders,1):
        assert [x['mode'] for x in formal if x['round']==index]==order
    results=read(root/'RESULTS.json')
    for pair,metrics in results['comparisons'].items():
        left,right=pair.split('/')
        xs=[x for x in formal if x['mode']==left]; ys=[x for x in formal if x['mode']==right]
        before=[o.index(left)<o.index(right) for o in orders]
        for key,estimate in metrics.items():
            ratios=[(x['summary'][key]/y['summary'][key] if key=='trace_ms'
                     else x['region'][key]/y['region'][key]) for x,y in zip(xs,ys)]
            actual=paired(ratios,before)
            for name in actual:assert np.allclose(actual[name],estimate[name],rtol=0,atol=1e-12), (pair,key,name)
    qualification=read(root/'COST_QUALIFICATION.json')
    assert len(qualification)==5
    for q in qualification:
        mode=q['mode']; ratios=[]
        for index in range(1,7):
            on=next(x for x in cost if x['label']==f'cost_{mode}_r{index}_on')
            off=next(x for x in cost if x['label']==f'cost_{mode}_r{index}_off')
            ratios.append(on['summary']['trace_ms']/off['summary']['trace_ms'])
        estimate=paired(ratios)
        for name in estimate:assert np.allclose(estimate[name],q[name],rtol=0,atol=1e-12)
        assert q['output_equal'] and q['admitted']==(estimate['CI95'][1]<=1.03)
    admitted=all(q['admitted'] for q in qualification)
    assert read(root/'FORMAL_TIMER.json')['observe']==admitted
    assert results['observer_admitted']==admitted
    assert all(x['summary']['observe']==admitted for x in formal)
    return dict(state='independently_audited',formal_processes=30,observer_processes=60,
                oracle='integer squared L2 and live-multiset replay; exact FP32 fields',
                queries_checked=900000,events_per_process=12000,rebuilds_per_process=50,
                ordered_outputs_identical=True,guard_receipts_valid=True,
                statistics_recomputed=True,observer_admitted=admitted,
                measured_binary_sha256=source['binary_sha256'],
                raw_source_manifest_sha256=sha(root/'SOURCE.json'),receipt_sha256=receipts)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--qualification',action='store_true');a=p.parse_args()
    assert not a.output.exists()
    result=(validate_qualification if a.qualification else validate)(a.raw)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='receipt_sha256'},indent=2))
