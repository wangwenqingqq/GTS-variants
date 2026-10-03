#!/usr/bin/env python3
"""Long native multiset correctness replay using the frozen U0 observer."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import numpy as np
from campaign10k import ROOT,invoke,save,sha

SEEDS=(2026100431,2026100432,2026100433)

def generate(a):
    dest=ROOT/'native';dest.mkdir(exist_ok=True)
    source=a.u0/'run/fixtures/query_only.data'
    data=np.loadtxt(source,skiprows=1,dtype=np.int64);assert data.shape==(1000,128)
    # Exact integer metric; every FP32 dimension sum is below 2^24.
    norms=(data*data).sum(axis=1)
    sq=norms[:,None]+norms[None,:]-2*(data@data.T)
    assert sq.min()==0 and sq.max()<2**24
    for seed,radius in zip(SEEDS,(0,10000,512)):
        case=dest/str(seed)
        if case.exists():continue
        case.mkdir();(case/'data.txt').write_bytes(source.read_bytes())
        rng=random.Random(seed);base=np.arange(1000);alive=np.ones(1000,dtype=bool);buf=[];ops=[];expected=[];builds=[base.tolist()]
        def query():
            q=rng.randrange(len(base));step=len(ops);ops.append([2,q])
            live=np.r_[base[alive],np.array(buf,dtype=np.int64)]
            distances=sq[base[q],live];ids=np.flatnonzero(distances<=radius*radius)
            expected.append({'step':step,'qid':q,'tree_size':len(base),'buffer':len(buf),
                             'ids':ids.tolist(),'distances':np.sqrt(distances[ids].astype(np.float64)).astype(np.float32).tolist(),'active_size':len(live)})
        def update(flag,idx):
            nonlocal base,alive,buf
            ops.append([flag,idx])
            if flag==0:
                buf.append(int(base[idx]))
                if len(buf)==10:
                    base=np.r_[base[alive],np.array(buf,dtype=np.int64)];alive=np.ones(len(base),dtype=bool);buf=[];builds.append(base.tolist())
            else:
                positions=np.flatnonzero(alive)
                if idx<len(positions):alive[positions[idx]]=False
                else:buf.pop(idx-len(positions))
        for cycle in range(100):
            for pair in range(10):
                query()
                if cycle%2==0:
                    rank=rng.randrange(int(alive.sum()));update(1,rank);query();update(0,rng.randrange(len(base)));query()
                else:
                    update(0,rng.randrange(len(base)));query();update(1,int(alive.sum())+len(buf)-1);query()
            for i in range(70):query()
            assert len(base)==1000 and int(alive.sum())==1000 and not buf
        assert len(ops)==12000 and len(expected)==10000 and len(builds)==51
        (case/'events.txt').write_text('12000\n'+''.join(f'{f} {i}\n' for f,i in ops))
        save(case/'expected.json',{'seed':seed,'radius':radius,'operations':ops,'expected':expected,'build_base_maps':builds,
                                 'data_sha256':sha(case/'data.txt'),'events_sha256':sha(case/'events.txt'),
                                 'membership':'exact integer squared L2; live multiset ranks','fresh_external_arrivals':False})
    save(dest/'REGISTERED.json',{'seeds':SEEDS,'Q_each':10000,'events_each':12000,'insert_each':1000,'delete_each':1000,
                              'rebuilds_each':50,'timer':'U0 observer; correctness only, no performance promotion',
                              'binary_sha256':sha(a.u0/'run/bin/u0_rnum_reset_obs'),
                              'traces':{str(s):{'expected_sha256':sha(dest/str(s)/'expected.json'),'events_sha256':sha(dest/str(s)/'events.txt')} for s in SEEDS}})

def check(a,seed):
    sys.path.insert(0,str(a.u0))
    import u0
    case=ROOT/'native'/str(seed);manifest=json.loads((case/'expected.json').read_text())
    assert sha(case/'data.txt')==manifest['data_sha256'] and sha(case/'events.txt')==manifest['events_sha256']
    data=np.loadtxt(case/'data.txt',skiprows=1,dtype=np.int64).tolist();results=[];trees=[]
    log=ROOT/'runs'/f'u10_native_{seed}'/'stdout.log'
    for line in log.open():
        if line.startswith('U0_RESULT '):results.append(json.loads(line[10:]))
        elif line.startswith('U0_TREE '):trees.append(json.loads(line[8:]))
    assert len(results)==10000 and len(trees)==51,(len(results),len(trees))
    checked_members=0
    for tree,base_map in zip(trees,manifest['build_base_maps']):
        checked_members+=u0.tree_audit(tree,[data[i] for i in base_map])
    total=0
    for actual,expected in zip(results,manifest['expected']):
        for key in ('step','qid','tree_size','buffer'):assert actual[key]==expected[key],(seed,expected['step'],key)
        ids=actual['ids'];assert len(ids)==len(set(ids)) and set(ids)==set(expected['ids']),(seed,expected['step'],'membership')
        fields=dict(zip(expected['ids'],expected['distances']))
        assert len(ids)==len(actual['distances'])
        for idx,value in zip(ids,actual['distances']):
            ref=fields[idx];assert np.isfinite(value) and value>=0 and abs(value-ref)<=1e-5*max(1,ref),(seed,expected['step'],'field')
        total+=len(ids)
    result={'seed':seed,'state':'passed','query_checkpoints':10000,'actual_rebuilds':len(trees)-1,'events':12000,'results_checked':total,
            'ancestor_member_checks':checked_members,'FN':0,'FP':0,'duplicates':0,'invalid_IDs':0,'fields_pass':True,'raw_log_sha256':sha(log),
            'visibility':'serialized native loop; no concurrency/fresh-arrival claim','timing_scope':'correctness observer; no latency/QPS claim'}
    save(case/'CHECK.json',result);print(json.dumps(result),flush=True);return result

def run(a):
    generate(a);rows=[]
    for seed in SEEDS:
        case=ROOT/'native'/str(seed);m=json.loads((case/'expected.json').read_text())
        expected=json.loads((ROOT/'native/REGISTERED.json').read_text())['binary_sha256']
        binary=a.u0/'run/bin/u0_rnum_reset_obs';assert sha(binary)==expected
        invoke(a,f'u10_native_{seed}',[binary,case/'data.txt',case/'events.txt',2,m['radius'],case/'counts.txt'],14400)
        rows.append(check(a,seed));save(ROOT/'U10_NATIVE.json',rows)
    print('U10 NATIVE CORRECTNESS COMPLETE: 30000 query events, 150 threshold rebuilds',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('generate','run'));p.add_argument('--gpu',required=True)
    p.add_argument('--u0',type=Path,required=True);a=p.parse_args();globals()[a.phase](a)

if __name__=='__main__':main()
