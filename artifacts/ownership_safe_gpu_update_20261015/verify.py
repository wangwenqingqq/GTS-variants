"""Public reconstruction plus exact CPU ACK-callback accounting regression check."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,hashlib,math
import numpy as np
from common import HERE,REPO,load,sha,jobs
import scalars

def reconstructed(actual,expected):
    """Allow only finite aggregate roundoff;structure,types and integers stay exact."""
    assert type(actual) is type(expected)
    if isinstance(expected,dict):
        assert actual.keys()==expected.keys()
        for key in expected:reconstructed(actual[key],expected[key])
    elif isinstance(expected,list):
        assert len(actual)==len(expected)
        for a,b in zip(actual,expected):reconstructed(a,b)
    elif isinstance(expected,float):
        assert math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12)
    else:assert actual==expected

def ack_inventory(mutations,physical,job):
    at=0;changed=0;callbacks=0
    def consume(count):
        nonlocal at,changed,callbacks
        group=mutations[at:at+count];assert len(group)==count
        touched={int(m[3]) for m in group if int(m[0])==1 or int(m[3])!=int(m[4])}
        at+=count;changed+=len(touched);callbacks+=1
    if job['kind']=='micro':consume(job['K'] if job['op']=='I' else 0)
    for row in physical:consume(int(row['rows']))
    assert at==len(mutations)
    return dict(passed=True,ACK_callbacks=callbacks,changed_rows_checked=changed,mutations_replayed=at)

def test():
    reconstructed({'ratio':[math.nextafter(1.,2.)],'count':340},{'ratio':[1.],'count':340})
    for actual,expected in ((1.000001,1.),(float('nan'),float('nan')),(True,1),([1],[]),({'n':340},{'n':341})):
        try:reconstructed(actual,expected)
        except AssertionError:pass
        else:raise AssertionError('Invalid aggregate reconstruction admitted')
    empty=np.empty((0,8),dtype=int)
    assert ack_inventory(empty,[],dict(kind='micro',op='D',K=0))['ACK_callbacks']==1
    assert ack_inventory(empty,[],dict(kind='micro',op='R',K=0))['ACK_callbacks']==1
    assert ack_inventory(empty,[],dict(kind='service'))['ACK_callbacks']==0
    mutations=np.array([[0,0,4,0,3,3,4,3],[0,3,3,0,2,2,4,2],[1,4,2,2,2,-1,5,3]])
    answer=ack_inventory(mutations,[dict(rows=1)],dict(kind='micro',op='I',K=2))
    assert answer==dict(passed=True,ACK_callbacks=2,changed_rows_checked=2,mutations_replayed=3)
    try:ack_inventory(mutations,[dict(rows=2)],dict(kind='micro',op='I',K=2))
    except AssertionError:pass
    else:raise AssertionError('Mutation accounting truncation admitted')
    print('PASS:finite aggregate roundoff only,exact integer/structure rejection,empty initial D/R callback,initial I deduplication,service count and truncation rejection;0 GPU starts')

def verify():
    identity=load(HERE/'evidence/IDENTITY.json');recovery=load(HERE/'evidence/VALIDATOR_RECOVERY.json')
    for name,h in identity['executed_sources'].items():
        source=REPO/name
        if name==str((HERE/'quality.py').relative_to(REPO)):
            assert sha(HERE/'evidence/INITIAL_VALIDATOR.py')==h==recovery['original_validator_sha256']
            assert sha(HERE/'evidence/CONTINUATION_VALIDATOR.py')==recovery['corrected_validator_sha256']==identity['continuation']['corrected_validator_sha256']
            assert sha(source)==recovery['strengthened_public_validator_sha256']
        else:assert sha(source)==h,('Executed source drift',name)
    for name,h in identity['postprocessing_sources'].items():assert sha(HERE/name)==h
    bridge=load(HERE/'evidence/PUBLIC_SOURCE_BRIDGE.json');admin=load(HERE/'evidence/ADMIN_MANIFEST.json')
    assert bridge==identity['publication_source_revisions']
    recorded=identity['recorded_postprocessing_sources'];published=identity['postprocessing_sources']
    assert recorded.keys()==published.keys() and {n for n in recorded if recorded[n]!=published[n]}==set(bridge)
    for name,row in bridge.items():
        assert recorded[name]==row['recorded_source_sha256']==admin['files'][row['private_recorded_source_key']]['sha256']
        assert published[name]==row['published_source_sha256']
    assert sha(HERE/'resume.py')==identity['continuation']['controller_sha256']
    assert sha(HERE/'resume_primary.py')==identity['second_continuation']['controller_sha256']
    from generate import adapter,client
    for name,text in (('adapter.cuh',adapter()),('main.cu',client())):
        assert hashlib.sha256(text.encode()).hexdigest()==identity['generated']['build/'+name]
    for name in ('plan.hpp','update.cuh','shapes.cuh'):assert sha(HERE/name)==identity['generated']['build/'+name]
    from curate import extensions
    primary=load(HERE/'evidence/PRIMARY_SCALARS.json');assert [r['job'] for r in primary]==jobs('primary')
    reconstructed(scalars.run(primary),load(HERE/'results/TIMING.json'))
    reconstructed(extensions(primary,load(HERE/'evidence/SHAPE_SCALARS.json'),load(HERE/'evidence/CALIBRATION_SCALARS.json')),load(HERE/'results/EXTENSIONS.json'))
    execution=load(HERE/'evidence/EXECUTION.json');quality=load(HERE/'evidence/QUALITY.json')
    assert execution['complete'] and execution['total_GPU_starts']==execution['max_GPU_starts']==341 and execution['passed_targets_rerun']==0
    assert quality['passed'] and len(quality['records'])==340 and len(load(HERE/'evidence/RECEIPTS.json'))==341
    assert sum(execution['stage_attempt_counts'].values())==341 and sum(execution['admitted_stage_counts'].values())==340
    assert sum(r['admitted'] for r in load(HERE/'evidence/RECEIPTS.json'))==340
    assert sum(r['physical_witness_proof'] is not None for r in quality['records'])==262
    assert identity['qualification_admission']['unique_qualified_targets']==42 and recovery['prior_failure_retained'] and recovery['GPU_reruns']==0
    inventory=load(HERE/'evidence/CPU_NATIVE_W2_INVENTORY.json')
    assert inventory['total_batches']==977 and inventory['native_moves']==inventory['final_changed_rows']==500000
    assert inventory['RAW']==inventory['WAW']==inventory['WAR']==0
    manifest=load(HERE/'PUBLIC_MANIFEST.json')
    actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name!='PUBLIC_MANIFEST.json' and '__pycache__' not in p.parts}
    assert actual==set(manifest['files'])
    for name,r in manifest['files'].items():assert sha(HERE/name)==r['sha256'] and (HERE/name).stat().st_size==r['bytes']
    print('PASS:exact source bridge,341 attempts/340 admitted targets,public scalar reconstruction,frozen W2 inventory and complete manifest;0 GPU starts')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selftest',action='store_true');a=p.parse_args()
    test() if a.selftest else verify()
