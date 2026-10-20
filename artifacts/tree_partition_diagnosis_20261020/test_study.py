"""Small independent arithmetic and high-ambient-dimensional structural fixtures."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import copy
from pathlib import Path
import numpy as np
from tree_study import build,center,native,pair_scores,evaluate,save,sha,HERE,outside_repo


def reference(x,q):
    result=[]
    for row in x:
        s=0.0
        for a,b in zip(row,x[q]):
            delta=float(a)-float(b);s=s+delta*delta
        result.append(s)
    return np.array(result,np.float64)


def run(path,out):
    out=outside_repo(out);out.mkdir();lib=native(path);rng=np.random.Generator(np.random.PCG64(2026102008));cases=0
    x=rng.normal(size=(64,7)).astype(np.float32)
    ids=np.arange(64,dtype=np.int64)
    chosen,mean,span=center(lib,x,ids)
    expected=np.zeros(7)
    for row in x:expected+=row.astype(np.float64)
    expected/=len(x)
    assert np.array_equal(mean,expected) and np.array_equal(span,x.max(axis=0).astype(float)-x.min(axis=0).astype(float))
    costs=[]
    for row in x:
        s=0.0
        for a,b in zip(row,expected):delta=float(a)-float(b);s=s+delta*delta
        costs.append(s)
    assert chosen==int(np.argmin(costs))
    scores=pair_scores(lib,x,ids,np.zeros(64,dtype=np.int64));assert np.array_equal(scores,reference(x,0))
    # A 960-dimensional representation can still be an easily pruned line.
    line=np.zeros((64,960),np.float32);line[:,0]=np.arange(64,dtype=np.float32)
    duplicate=np.zeros((64,4),np.float32)
    random=rng.normal(size=(64,7)).astype(np.float32)
    records=[]
    for name,a,radius in [('line960',line,float(np.float32(.01))),('duplicates',duplicate,0.0),('random',random,float(np.float32(1.0)))]:
        refs=np.stack([reference(a,q) for q in (0,21,63)])
        for kind in ('RANDOM_BALANCED','KD_MAXSPAN_MEDIAN','SAMPLED_PCA_MEDIAN'):
            tree=build(a,lib,kind,depth=3)
            rows,_,raw=evaluate(tree,refs,[0,21,63],radius,depth=3,d=a.shape[1])
            assert len(rows)==3 and not any(r['false_prune_nodes'] for r in rows)
            assert np.all(raw['minima'][:,0]==refs.min(axis=1))
            if name=='duplicates':assert all(r['retained_points']==64 for r in rows)
            if name=='line960' and kind!='RANDOM_BALANCED':assert all(r['retained_points']==8 for r in rows)
            records.append(dict(fixture=name,kind=kind,retained=[r['retained_points'] for r in rows]));cases+=1
    from verify_study import verify_counts
    rows,levels,raw=evaluate(tree,refs,[0,21,63],radius,depth=3,d=a.shape[1])
    good=dict(rows=rows,levels=levels)
    verify_counts(tree,refs,[0,21,63],radius,raw['reject'].astype(bool),good,depth=3,d=a.shape[1])
    rejected=0
    for where,field in [('rows','qid'),('rows','retained_fraction'),('levels','certificate_capture')]:
        bad=copy.deepcopy(good);bad[where][0][field]=-123
        try:verify_counts(tree,refs,[0,21,63],radius,raw['reject'].astype(bool),bad,depth=3,d=a.shape[1])
        except AssertionError:rejected+=1
        else:raise AssertionError('Counterfactual result accepted: '+field)
    assert rejected==3
    try:outside_repo(HERE/'raw_should_not_be_written')
    except ValueError:pass
    else:raise AssertionError('Raw output inside Git must be rejected.')
    # Boundary, duplicates, adjacent FP32 values, subnormals and large coordinates.
    special=np.array([[0,0],[0,0],[1,0],[np.nextafter(np.float32(1),np.float32(2)),0],
                      [np.nextafter(np.float32(0),np.float32(1)),0],[np.finfo(np.float32).max,0]],np.float32)
    got=pair_scores(lib,special,np.arange(6,dtype=np.int64),np.zeros(6,dtype=np.int64))
    assert np.array_equal(got,reference(special,0))
    result=dict(passed=True,structural_fixture_cases=cases,independent_scalar_mean_center_and_scores=True,
                high_ambient_low_intrinsic_control=True,boundary_scores_bit_equal=True,
                altered_scalar_records_rejected=3,raw_checkout_output_rejected=True,records=records,GPU_starts=0)
    save(out/'TESTS.json',result);print('QUALIFICATION_PASS:9 tree fixtures;independent scalar scores/center;960D line prunes;0 GPU')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run(a.library.resolve(),a.out.resolve())
