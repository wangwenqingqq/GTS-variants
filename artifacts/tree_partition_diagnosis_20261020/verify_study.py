"""Fresh O0 geometry, split membership and owner-array oracle reconstruction."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from tree_study import HERE,ROOT,bind,source_ids,load,sha,save,native,center,pair_scores,interval,ball_keep,validate,outside_repo,runtime_identity


def verify_counts(tree,refs,qids,radius,reject,result,depth=12,d=960):
    n=refs.shape[1];nn=len(tree['centers']);leaf=(nn-1)//2;threshold=radius*radius
    owner=np.empty(n,np.int64)
    for node in range(leaf,nn):
        b=int(tree['starts'][node]);e=b+int(tree['sizes'][node]);owner[tree['perm'][b:e]]=node-leaf
    minima=np.full((len(refs),nn),np.inf)
    for qi in range(len(refs)):np.minimum.at(minima[qi,leaf:],owner,refs[qi])
    for node in range(leaf-1,-1,-1):minima[:,node]=np.minimum(minima[:,2*node+1],minima[:,2*node+2])
    oracle=minima>threshold;assert not np.any(reject&~oracle)
    assert len(result['rows'])==len(refs) and len(result['levels'])==len(refs)*(depth+1)
    for qi,row in enumerate(result['rows']):
        reached=np.zeros(nn,bool);reached[0]=True
        for node in range(1,nn):reached[node]=reached[(node-1)//2] and not reject[qi,(node-1)//2]
        live=reached[leaf:]&~reject[qi,leaf:]
        retained=int(tree['sizes'][leaf:][live].sum());visits=int(reached.sum())
        truth=refs[qi]<=threshold;assert np.all(live[owner[truth]])
        omass=int(tree['sizes'][leaf:][oracle[qi,leaf:]].sum())
        cmass=int(tree['sizes'][leaf:][reject[qi,leaf:]].sum())
        p10,p50,p90=np.quantile(np.sqrt(refs[qi]),(.1,.5,.9))
        expected=dict(query=qi,qid=int(qids[qi]),true_hits=int(truth.sum()),visited_nodes=visits,
            retained_points=retained,retained_fraction=retained/n,oracle_retained_points=n-omass,
            oracle_prunable_fraction=1-(n-omass)/n,flat_leaf_oracle_prunable_fraction=omass/n,
            flat_leaf_certificate_prunable_fraction=cmass/n,flat_leaf_certificate_capture=cmass/omass if omass else None,
            flat_leaf_missed_prunable_points=omass-cmass,coordinate_proxy_bytes=(visits+retained)*d*4+d*4,
            node_metadata_read_proxy_bytes=visits*32,full_scan_coordinate_bytes=n*d*4+d*4,
            distance_p10=float(p10),distance_p50=float(p50),distance_p90=float(p90),
            distance_contrast=float((p90-p10)/p50) if p50 else None,false_prune_nodes=0)
        assert row==expected,('query metrics',qi)
        for dep in range(depth+1):
            cell=result['levels'][qi*(depth+1)+dep];lo=2**dep-1;hi=2**(dep+1)-1
            o=int(tree['sizes'][lo:hi][oracle[qi,lo:hi]].sum());z=int(tree['sizes'][lo:hi][reject[qi,lo:hi]].sum())
            expected=dict(query=qi,qid=int(qids[qi]),depth=dep,nodes=hi-lo,
                oracle_rejected_nodes=int(oracle[qi,lo:hi].sum()),certificate_rejected_nodes=int(reject[qi,lo:hi].sum()),
                oracle_prunable_points=o,certificate_pruned_points=z,oracle_prunable_fraction=o/n,
                certificate_pruned_fraction=z/n,certificate_capture=z/o if o else None,
                radius_mean=float(tree['radii'][lo:hi].mean()),radius_p90=float(np.quantile(tree['radii'][lo:hi],.9)))
            assert cell==expected,('level metrics',qi,dep)
    return minima


def census(run):
    names={'REGISTERED.json','BUILD.json','START.json','STARTS.jsonl','COMPLETE.json',
           'build/geometry.so','build/compile.stdout','build/compile.stderr',
           'qualification.stdout','qualification.stderr','qualification/TESTS.json'}
    files={'REGISTERED.json','RESULTS.json','COMPLETE.json'}|{n+'.npy' for n in
        ('perm','centers','radii','starts','sizes','split','minima','center_scores','reject')}
    for kind in load(HERE/'CONTRACT.json')['builders']:
        names|={kind+'/'+n for n in files}
        names|={'receipts/'+kind+'.'+suffix for suffix in ('command.json','exit.json','stdout','stderr')}
    assert len(names)==59
    actual=set();dirs=set()
    for p in run.rglob('*'):
        assert not p.is_symlink()
        (actual if p.is_file() else dirs).add(str(p.relative_to(run)))
    assert actual==names,'Missing or extra campaign output/attempt'
    expected_dirs={str(p) for n in names for p in Path(n).parents if str(p)!='.'}
    assert dirs==expected_dirs
    return {n:sha(run/n) for n in sorted(names)}


def verify_one(data,references,libpath,run,kind,out):
    assert os.getpriority(os.PRIO_PROCESS,0)==10
    out=outside_repo(out)
    assert census(run)==load(run.with_name(run.name+'.ANCHORS.json'))['files']
    c,x,refs=bind(data,references);t=run/kind;out.mkdir()
    complete=load(t/'COMPLETE.json')
    assert complete['passed'] and complete['GPU_starts']==0
    assert {p.name for p in t.iterdir() if p.is_file()}==set(complete['files'])|{'COMPLETE.json'}
    assert all(sha(t/n)==h for n,h in complete['files'].items())
    reg=load(t/'REGISTERED.json');assert reg['sources']==source_ids() and reg['kind']==kind and reg['nice']==10
    assert reg['runtime']==runtime_identity()==load(run/'REGISTERED.json')['runtime']
    names=('perm','centers','radii','starts','sizes','split')
    tree={n:np.load(t/(n+'.npy'),allow_pickle=False) for n in names};validate(tree,len(x),12)
    n,d=x.shape;nn=8191;leaf=4095;lib=native(libpath)
    order=np.random.Generator(np.random.PCG64(c['tree']['random_seed'])).permutation(n)
    rank=np.empty(n,np.int64);rank[order]=np.arange(n)
    for node in range(nn):
        begin=int(tree['starts'][node]);count=int(tree['sizes'][node])
        ids=np.sort(tree['perm'][begin:begin+count]).astype(np.int64,copy=False)
        chosen,mu,span=center(lib,x,ids)
        assert chosen==tree['centers'][node],('center',node)
        reverse=pair_scores(lib,x,np.full(count,chosen,np.int64),ids)
        radius=float(interval(reverse,d)[1].max())
        assert np.float64(radius).view(np.uint64)==tree['radii'][node].view(np.uint64),('cover',node)
        if node>=leaf:continue
        if kind=='RANDOM_BALANCED':key=rank[ids];split=-1
        elif kind=='KD_MAXSPAN_MEDIAN':
            split=int(np.argmax(span));key=x[ids,split].astype(np.float64)
        else:
            m=min(512,count)
            sample=ids if m==count else np.sort(ids[np.argpartition(rank[ids],m-1)[:m]])
            y=x[sample].astype(np.float64)-mu
            split=int(np.argmax(np.sum(y*y,axis=0)))
            v=np.zeros(d);v[split]=1
            for _ in range(8):
                w=y.T@(y@v);norm=float(np.sqrt(np.dot(w,w)))
                if norm>0:v=w/norm
            key=np.empty(count)
            for a in range(0,count,4096):
                group=ids[a:a+4096];key[a:a+len(group)]=(x[group].astype(np.float64)-mu)@v
        assert tree['split'][node]==split
        expected=np.sort(ids[np.lexsort((ids,key))][:count//2])
        actual=np.sort(tree['perm'][begin:begin+count//2])
        assert np.array_equal(actual,expected),('median split membership',node)
    # Full query-center recomputation on old32 only, separate from the stored references.
    qids=np.array(c['task']['qids'],np.int64)
    actual=pair_scores(lib,x,np.tile(tree['centers'],32),np.repeat(qids,nn)).reshape(32,nn)
    expected=refs[:,tree['centers']]
    assert np.array_equal(actual.view(np.uint64),expected.view(np.uint64))
    assert np.array_equal(actual,np.load(t/'center_scores.npy',allow_pickle=False))
    radius=float(np.array([int(c['task']['radius_bits'],16)],np.uint32).view(np.float32)[0]);threshold=radius*radius
    reject=~ball_keep(actual,tree['radii'],d,radius)
    assert np.array_equal(reject,np.load(t/'reject.npy',allow_pickle=False))
    result=load(t/'RESULTS.json');assert result['passed'] and len(result['rows'])==32 and len(result['levels'])==32*13
    assert result['kind']==kind and result['GPU_starts']==result['heldout_query_evaluations']==0
    assert np.isfinite(result['construction_wall_seconds']) and result['construction_wall_seconds']>=0
    minima=verify_counts(tree,refs,qids,radius,reject,result)
    assert np.array_equal(minima,np.load(t/'minima.npy',allow_pickle=False))
    assert source_ids()==load(HERE/'SOURCE_FREEZE.json')['files']
    proof=dict(passed=True,kind=kind,all_nodes_geometry_reconstructed=nn,all_internal_splits_reconstructed=leaf,
               reverse_orientation_O0_cover=True,query_center_scores_bit_equal=32*nn,owner_oracle_all_pairs=32*n,
               every_query_and_level_checked=True,false_prune_nodes=0,GPU_starts=0,heldout_query_evaluations=0,
               result_sha256=sha(t/'RESULTS.json'),library_sha256=sha(libpath),
               population_anchor_sha256=sha(run.with_name(run.name+'.ANCHORS.json')))
    save(out/'PROOF.json',proof);print('VERIFICATION_PASS',kind,'all covers/splits/query centers/oracle;0 GPU',flush=True)


def main(data,references,run,out):
    assert os.getpriority(os.PRIO_PROCESS,0)==10
    out=outside_repo(out)
    out.mkdir();c=load(HERE/'CONTRACT.json');sources=source_ids()
    anchors=load(run.with_name(run.name+'.ANCHORS.json'))
    assert census(run)==anchors['files']
    assert sources==load(HERE/'SOURCE_FREEZE.json')['files']
    reg=load(run/'REGISTERED.json');assert reg['sources']==load(run/'START.json')['sources']==sources
    completed=load(run/'COMPLETE.json')
    assert completed['passed'] and completed['sources']==sources and completed['GPU_starts']==completed['heldout_query_evaluations']==0
    assert completed['records']==[load(run/'receipts'/(k+'.exit.json')) for k in c['builders']]
    starts=[json.loads(x) for x in (run/'STARTS.jsonl').read_text().splitlines()]
    assert starts==[dict(index=i,kind=k,GPU=False) for i,k in enumerate(c['builders'])]
    expected_compile=['g++','-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC',str(HERE/'geometry.cpp'),'-o',str(run/'build/geometry.so')]
    assert reg['compile_command']==expected_compile and reg['nice']==10
    assert sha(run/'build/geometry.so')==load(run/'BUILD.json')['library_sha256']==load(run/'START.json')['library_sha256']
    assert load(run/'START.json')['qualification_sha256']==sha(run/'qualification/TESTS.json')
    assert load(run/'qualification/TESTS.json')['passed']
    assert (run/'qualification.stderr').read_bytes()==(run/'build/compile.stderr').read_bytes()==b''
    lib=out/'geometry_O0.so'
    command=['g++','-std=c++17','-O0','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC',str(HERE/'geometry.cpp'),'-o',str(lib)]
    save(out/'REGISTERED.json',dict(before_verification=True,sources=sources,compile_command=command,original_run=str(run),nice=10,population_anchor_sha256=sha(run.with_name(run.name+'.ANCHORS.json')),runtime=runtime_identity()))
    assert load(out/'REGISTERED.json')['runtime']==reg['runtime']
    p=subprocess.run(command,capture_output=True,text=True)
    (out/'compile.stdout').write_text(p.stdout);(out/'compile.stderr').write_text(p.stderr)
    assert p.returncode==0 and not p.stderr,(p.stdout,p.stderr)
    p=subprocess.run(['python3',str(HERE/'test_study.py'),'--library',str(lib),'--out',str(out/'qualification')],capture_output=True,text=True)
    (out/'qualification.stdout').write_text(p.stdout);(out/'qualification.stderr').write_text(p.stderr)
    assert p.returncode==0,(p.stdout,p.stderr)
    proofs=[]
    with (out/'STARTS.jsonl').open('x') as ledger:
        for index,kind in enumerate(c['builders']):
            original=['python3',str(HERE/'tree_study.py'),'--data',str(data),'--references',str(references),'--library',str(run/'build/geometry.so'),'--kind',kind,'--out',str(run/kind)]
            assert load(run/'receipts'/(kind+'.command.json'))==dict(command=original,before_start=True,source_hashes=sources,library_sha256=sha(run/'build/geometry.so'))
            exit_record=load(run/'receipts'/(kind+'.exit.json'))
            assert exit_record['kind']==kind and exit_record['returncode']==0
            assert exit_record['complete_sha256']==sha(run/kind/'COMPLETE.json')
            assert (run/'receipts'/(kind+'.stdout')).read_text()==f'POPULATION_PASS {kind} 32 queries;8191 nodes;0 false prune;0 GPU\n'
            assert (run/'receipts'/(kind+'.stderr')).read_bytes()==b''
            command=['python3',str(HERE/'verify_study.py'),'--data',str(data),'--references',str(references),'--run',str(run),'--kind',kind,'--library',str(lib),'--out',str(out/kind)]
            save(out/(kind+'.command.json'),dict(command=command,before_start=True))
            ledger.write(json.dumps(dict(index=index,kind=kind,GPU=False))+'\n');ledger.flush()
            p=subprocess.run(command,capture_output=True,text=True,timeout=1800)
            (out/(kind+'.stdout')).write_text(p.stdout);(out/(kind+'.stderr')).write_text(p.stderr)
            assert p.returncode==0,(kind,p.stdout,p.stderr)
            proofs.append(load(out/kind/'PROOF.json'));print(p.stdout.strip(),flush=True)
    assert source_ids()==sources
    assert census(run)==anchors['files']
    save(out/'PROOF.json',dict(passed=True,sources=sources,records=proofs,
         exact_population_commands=3,original_population_starts=3,verification_starts=3,
         heldout_query_evaluations=0,GPU_starts=0,population_anchor_sha256=sha(run.with_name(run.name+'.ANCHORS.json')),
         raw_campaign_files=59,scope='Fixed development-only structural diagnosis;shared interval helper proof,not independent rederivation;not end-to-end timing'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--references',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--kind');p.add_argument('--library',type=Path)
    a=p.parse_args()
    if a.kind:verify_one(a.data.resolve(),a.references.resolve(),a.library.resolve(),a.run.resolve(),a.kind,a.out.resolve())
    else:main(a.data.resolve(),a.references.resolve(),a.run.resolve(),a.out.resolve())
