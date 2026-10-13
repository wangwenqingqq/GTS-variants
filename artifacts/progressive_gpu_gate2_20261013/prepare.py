"""Generate a minimal private harness adapter; freeze before the first GPU start."""
import argparse,difflib,os,subprocess,sys,time
from pathlib import Path
from pre_cost import HERE,ART,read,save,sha
OWNED=('CONTRACT.json','NUMERICS.md','PRIOR_ART.md','SOURCES.json','DESIGN.md','progressive.cuh','fixtures.hpp','prepare.py','campaign.py','static_evidence.py','pre_cost.py','analyze.py','test_gate2.py','cost/PRE_GPU_COST.json','cost/REPLAY_SCREEN.json')
GUARD_DEPENDENCIES=('artifacts/unified_target_workflow/run.py','artifacts/unified_search_update/run.py','artifacts/unified_search_update/protocol.py','artifacts/par_range_update/reproduce.py','artifacts/par_range_update/fixtures.py','diagnostics/region_exec_20261008/audit_closure.py')
def sources():
    paths=[HERE/x for x in OWNED]
    paths += [ART/x for x in ('query_tile_padding_20261012/batch.cu','external_closure/range_service.cu','external_closure/static_guard.py','external_closure/common.py','non_padded_b1_baseline_20261012/campaign.py','non_padded_b1_baseline_20261012/prepare.py','non_padded_b1_baseline_20261012/b1_distance.cuh','exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json','exact_scan_breakdown_20261011/evidence/NATIVE_IDENTITY.json')]
    paths += [ART.parent/x for x in GUARD_DEPENDENCIES]
    return {str(p.relative_to(ART.parent)):sha(p) for p in paths}
def generate():
    original=(ART/'query_tile_padding_20261012/batch.cu').read_text()
    start=original.index('struct Batch : Scan {');end=original.index('int main(int argc,char** argv)try{')
    batch='''struct Batch : ProgressiveScan {
    int batch;
    void build_batch(const std::vector<float>& data,int n,int d,int b){
        if(b!=1)throw std::runtime_error("P1 B1-only");batch=b;build(data,n,d);
    }
    void invoke(const float* q,float radius,std::vector<Answer>& answers){
        range(q,radius,answers[0].ids,answers[0].dist,answers[0].raw);
    }
};
'''
    candidate=original[:start]+batch+original[end:]
    candidate=candidate.replace('"../external_closure/range_service.cu"','"'+str(ART/'external_closure/range_service.cu')+'"')
    candidate=candidate.replace('#undef main','#undef main\n#include "'+str(HERE/'progressive.cuh')+'"\n#include "'+str(HERE/'fixtures.hpp')+'"')
    candidate=candidate.replace('int main(int argc,char** argv)try{','int main(int argc,char** argv)try{\n    if(argc==2&&std::string(argv[1])=="--fixtures")return progressiveFixtures();')
    candidate=candidate.replace('bool diagnostic=std::stoi(argv[7]);','int diagnostic=std::stoi(argv[7]);')
    candidate=candidate.replace('b<1||b>128','b!=1||diagnostic<0||diagnostic>3')
    candidate=candidate.replace('double build=ms(tick);','double build=ms(tick);scan.audit_mode=diagnostic;scan.audit_prefix=out;')
    candidate=candidate.replace('diagnostic&&i==8','diagnostic==1&&i>=8')
    candidate=candidate.replace('pass=ms(tick);tick=Clock::now();scan.release();','pass=ms(tick);scan.write_audit(out);tick=Clock::now();scan.release();')
    oldmeta=r'<<",\"squared_bytes\":"<<size_t(b)*n*4'
    newmeta=r'<<",\"diagnostic_mode\":"<<diagnostic<<",\"squared_bytes\":0,\"state_buffer_bytes\":"<<size_t(n)*32<<",\"flags_bytes\":"<<size_t(n)<<",\"output_capacity_bytes\":"<<size_t(n)*16<<",\"count_bytes\":"<<4'
    assert candidate.count(oldmeta)==1
    candidate=candidate.replace(oldmeta,newmeta)
    return original,candidate
def prepare(a):
    w=a.work.resolve();assert not w.exists() and ART not in w.parents
    old=read(a.keeper/'REGISTERED.json');b=read(a.keeper/'build/BUILD.json')
    cpu=read(a.cost/'RESULTS.json');public=read(HERE/'cost/REPLAY_SCREEN.json')
    assert cpu==public and cpu['complete'] and cpu['admitted'] and cpu['GPU_starts']==0
    assert sha(a.keeper/'build/candidate')==b['binary_sha256']
    assert old['q32']==read(HERE/'CONTRACT.json')['workload']['query_ids']
    recovery=read(a.recovery) if a.recovery else None
    if recovery:
        prior=Path(recovery['prior_work']);failed=read(prior/'qualification/RESULTS.json')
        assert recovery['human_approved'] and recovery['max_new_starts']==33 and recovery['max_total_starts']==34
        assert recovery['prior_starts']==len((prior/'STARTS.jsonl').read_text().splitlines())==1
        assert recovery['prior_ledger_sha256']==sha(prior/'STARTS.jsonl') and recovery['prior_failure_sha256']==sha(prior/'qualification/RESULTS.json')
        assert not failed['complete'] and len(failed['rows'])==1 and failed['rows'][0]['label']=='fixtures' and failed['rows'][0]['status']=='failed'
        assert not (prior/'qualification/guards/fixtures/receipt.json').exists()
    assert sha(old['data'])==old['data_sha256']
    for name,h in old['generated_sources'].items():assert sha(a.keeper/'build'/name)==h
    for name,h in old['reference_hashes'].items():assert sha(Path(old['reference'])/name)==h
    state=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
    apps=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip();assert not apps
    w.mkdir();(w/'build').mkdir();(w/'pool32.txt').write_text('\n'.join(map(str,old['q32']))+'\n')
    # Import the entire preserved guard chain without starting a CUDA process.
    preflight=subprocess.check_output([sys.executable,'-c','import static_guard; assert callable(static_guard.snapshot); assert callable(static_guard.outside_repo)'],cwd=ART/'external_closure',env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},text=True)
    save(w/'DEPENDENCY_PREFLIGHT.json',dict(passed=True,CUDA_initializations=0,source_hashes={x:sha(ART.parent/x) for x in GUARD_DEPENDENCIES},stdout=preflight))
    orig,candidate=generate();source=w/'build/candidate.cu';source.write_text(candidate)
    baseline=(a.keeper/'build/candidate.cu').read_text();assert baseline.count('diagnostic&&i==8')==2
    diag=baseline.replace('diagnostic&&i==8','diagnostic&&i>=8');dsource=w/'build/keeper_diagnostic.cu';dsource.write_text(diag)
    (w/'build/ADAPTER_DIFF.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),candidate.splitlines(True),fromfile='batch.cu',tofile='P1.cu')))
    (w/'build/KEEPER_DIAGNOSTIC_DIFF.patch').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),diag.splitlines(True),fromfile='B1.cu',tofile='B1_profile_all32.cu')))
    commands={}
    for name,s in [('candidate',source),('keeper_diagnostic',dsource)]:
        command=[str(s) if v.endswith('/candidate.cu') else str(w/'build'/name) if v.endswith('/build/candidate') else v for v in old['command']]
        if name=='candidate':command+=['--ftz=false','--fmad=false','-Xcompiler=-ffp-contract=off,-fno-fast-math']
        commands[name]=command
    registration=dict(before_GPU=True,source_hashes=sources(),recovery=recovery,dependency_preflight_sha256=sha(w/'DEPENDENCY_PREFLIGHT.json'),contract_sha256=sha(HERE/'CONTRACT.json'),keeper_directory=str(a.keeper.resolve()),gate1_directory=str(a.gate1.resolve()),cpu_screen_sha256=sha(a.cost/'RESULTS.json'),gpu=state,numa=a.numa,parent_registration_sha256=sha(a.keeper/'REGISTERED.json'),keeper_binary=str(a.keeper/'build/candidate'),keeper_sha256=b['binary_sha256'],readonly_binary=old['readonly_binary'],readonly_sha256=old['readonly_sha256'],environment=old['environment'],q32=old['q32'],radius=old['radius'],data=old['data'],data_sha256=old['data_sha256'],reference=old['reference'],reference_hashes=old['reference_hashes'],libraries=old['libraries'],commands=commands,generated_sources={s.name:sha(s) for s in (source,dsource)},registered_unix=time.time())
    save(w/'REGISTERED.json',registration);binaries={}
    for name,command in commands.items():
        with (w/'build'/(name+'.compile.log')).open('x') as log:subprocess.run(command,env={**os.environ,**old['environment']},stdout=log,stderr=log,check=True)
        ldd=subprocess.check_output(['ldd',str(w/'build'/name)],env={**os.environ,**old['environment']},text=True);assert 'not found' not in ldd
        libs={}
        for line in ldd.splitlines():
            v=line.split()
            if '=>' in v and len(v)>2 and v[2].startswith('/'):libs[v[0]]={'sha256':sha(v[2])}
        assert libs==old['libraries'],'linked-library drift';(w/'build'/(name+'.ldd.txt')).write_text(ldd)
        binaries[name]=sha(w/'build'/name)
    assert sources()==registration['source_hashes']
    save(w/'READY.json',dict(passed=True,registration_sha256=sha(w/'REGISTERED.json'),source_hashes=sources(),binaries=binaries,libraries=old['libraries']))
    print('PREPARED one candidate,immutable B1,all32 profile adapter;0 GPU starts',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','keeper','gate1','cost'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--recovery',type=Path)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    prepare(p.parse_args())
