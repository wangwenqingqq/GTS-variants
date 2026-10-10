#!/usr/bin/env python3
"""The new merger must preserve the frozen estimator and task denominators."""
from static_results2 import comparisons,original_comparisons,reports,input_identities,c

def main():
    records={name:dict(data_sha256='data',snapshot_sha256='snapshot',qids=[1]) for name in c.CONTRACT['snapshots']}
    assert input_identities({**records,'bounded':dict(data_sha256='bounded',qids=[0])})==records
    bad={**records,'initial':dict(data_sha256='data',qids=[1])}
    try:input_identities(bad)
    except KeyError:pass
    else:raise AssertionError('missing target snapshot identity admitted')
    rows=[]
    for job in c.jobs('primary'):
        scale=1. if job['method']=='GTSPP_P' else 2.
        row=dict(**job,preparation_ms=scale,build_ms=scale,release_ms=scale,warmup_ms=99999.,context_ms=99999.)
        if job['method']!='GPU_RANGE_COMPLETE':row['knn_pass_ms']=scale
        if job['method']!='GPU_FLAT_KNN':row['range_pass_ms']=scale
        rows.append(row)
    result=comparisons(rows);assert result==original_comparisons(rows)
    for scopes in result.values():
        assert len(scopes['knn_pass_ms'])==len(scopes['range_pass_ms'])==4 and len(scopes['both_task_lifecycle_ms'])==3
        assert all(label.startswith('CPU') for label in scopes['both_task_lifecycle_ms'])
        for group in scopes.values():
            for r in group.values():assert r['ratio']==2 and r['CI95']==[2.,2.] and r['wins']==6 and r['confirmed_speedup']
    for bad in (rows[:-1],list(reversed(rows)),[{**r,'knn_pass_ms':0.} if r['method']=='GTSPP_P' else r for r in rows]):
        try:comparisons(bad)
        except AssertionError:pass
        else:raise AssertionError('incomplete/invalid matrix admitted')
    tables=reports({'comparisons':result,'rows':rows})
    assert set(tables)=={'EXTERNAL_KNN_RESULTS.md','EXTERNAL_RANGE_RESULTS.md','EXTERNAL_LIFECYCLE_RESULTS.md'}
    for name,text in tables.items():
        assert 'All72 admitted processes' in text and 'CPU_FLAT_INCLUSIVE_ADAPT' in text
        assert 'retained-client-output destruction' in text
        if 'LIFECYCLE' in name:
            assert 'Phase medians (ms)' in text and '—' in text
            assert '| 10.000000 |' in text and '| 5.000000 |' in text
        else:assert '0.062500' in text and '0.031250' in text and 'not a confidence interval' in text
    print('PASS original estimator parity, exact72 order, positive times and dual-task-only lifecycle')
if __name__=='__main__':main()
