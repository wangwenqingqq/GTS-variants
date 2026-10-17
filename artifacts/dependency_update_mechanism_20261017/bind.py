"""Independent post-run closure;no GPU launch and no mutation of raw evidence."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,datetime,os,subprocess,json,re,sys
from pathlib import Path
from protocol import HERE,REPO,STAGES,load,save,sha,jobs
from quality import check
from campaign import command
def digest(path,expected,size=None):
    assert Path(path).is_file() and sha(path)==expected,('Digest mismatch',str(path))
    if size is not None:assert Path(path).stat().st_size==size
def census(rows,expected):
    assert len(rows)==len(expected) and all(r['status']=='passed' for r in rows)
    assert [{k:v for k,v in r.items() if k not in ('status','checked_sha256','guard_sha256')} for r in rows]==expected
def payloads(prefix,expected):
    actual={p.name:p for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()};assert set(actual)==set(expected),'Missing/extra output payload'
    for name,spec in expected.items():digest(actual[name],spec['sha256'],spec['bytes'])
def exact_stage(stage,expected):
    labels={j['label'] for j in expected};files={'REGISTERED.json','RESULTS.json'}
    files.update(label+suffix for label in labels for suffix in ('.command.json','.checked.json','.outer.log'))
    assert {p.name for p in stage.iterdir()}==files|{'guards','outputs','reports'},'Extra/missing stage entry'
    for name in files:assert (stage/name).is_file() and not (stage/name).is_symlink()
    assert {p.name for p in (stage/'guards').iterdir()}==labels,'Extra/missing guard directory'
    guardfiles={'command.json','before.json','checks.json','after.json','stdout.log','receipt.json','gpu.csv','stderr.log'}
    outputs=set();reports=set()
    for j in expected:
        label=j['label'];guard=stage/'guards'/label
        assert guard.is_dir() and not guard.is_symlink() and {p.name for p in guard.iterdir()}==guardfiles
        assert all((guard/n).is_file() and not (guard/n).is_symlink() for n in guardfiles)
        if j['kind']!='selftest':
            names=set(load(stage/(label+'.checked.json'))['raw_outputs']);assert names and all(n.startswith(label+'.') and Path(n).name==n for n in names);outputs.update(names)
        if j.get('tool')=='nsys':reports.update((label+'.nsys-rep',label+'.sqlite'))
        if j.get('tool')=='ncu':reports.add(label+'.csv')
    for folder,wanted in (('outputs',outputs),('reports',reports)):
        assert {p.name for p in (stage/folder).iterdir()}==wanted,('Extra/missing '+folder)
        assert all((stage/folder/n).is_file() and not (stage/folder/n).is_symlink() for n in wanted)
def device_identity(receipt,before,after,gpu,uuid):
    assert receipt['gpu']==str(gpu),'Receipt GPU differs from registration'
    for state in (before,after):
        fields=[v.strip() for v in state['device'].split(',')]
        assert fields[:2]==[str(gpu),uuid] and not state['apps'],'Guard actual device differs from pre-target identity'
def inventory(w):
    reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');digest(w/'REGISTERED.json',ready['registration_sha256']);assert ready['passed']
    source=w/'source' if (w/'source').is_dir() else REPO;sealed=set();external=set()
    for stage in STAGES:
        assert reg['schedule'][stage]==jobs(stage);exact_stage(w/stage,reg['schedule'][stage])
        sealed.update(p for p in (w/stage).rglob('*') if p.is_file())
    for folder in ('build','cpu','logs','postrun_versions'):
        if (w/folder).exists():sealed.update(p for p in (w/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    sealed.update(p for p in w.iterdir() if p.is_file() and p.name not in ('campaign.lock','CLOSED_IDENTITY.json','DERIVED_IDENTITY.json'))
    for name in reg['sources']:sealed.add(source/name)
    for name in ('bind.py','export.py','test_bind.py'):sealed.add(source/'artifacts/dependency_update_mechanism_20261017'/name)
    for name in load(w/'POSTPROCESSOR_SOURCE.json')['files']:sealed.add(source/'artifacts/dependency_update_mechanism_20261017'/name)
    for name in reg['inputs']:sealed.add(Path(name))
    dependencies=load(w/'DEPENDENCIES_BEFORE_GPU.json');external.update(Path(n) for n in {**dependencies['linked_libraries'],**dependencies['CCCL_header_hashes']})
    before=load(w/'HOST_BEFORE_GPU.json');external.update(Path(before['commands'][n]['command'][0]) for n in ('nvcc','nsys','ncu'))
    external.update(p for p in sealed if not p.is_relative_to(w));return {p for p in sealed if p.is_relative_to(w)},external
def require_closed(w):
    w=Path(w);proof=load(w/'CLOSED_IDENTITY.json')
    assert proof.get('schema')==2 and proof['passed'] and proof['CPU_rechecked_GIST_targets']==338 and proof['source_guard_ready_command_census_complete'] and proof['raw_payload_set_and_hash_complete']
    digest(w/'REGISTERED.json',proof['registration_sha256']);assert proof['closure_validator_sha256']==sha(Path(__file__))
    study,external=inventory(w)
    assert set(proof['study_files'])=={str(p.relative_to(w)) for p in study} and set(proof['external_files'])=={str(p) for p in external},'Closed inventory is incomplete/extra'
    for name,r in proof['study_files'].items():digest(w/name,r['sha256'],r['bytes'])
    for name,r in proof['external_files'].items():digest(name,r['sha256'],r['bytes'])
    return proof
def derived_names(w):
    return {'analysis/PROCESSES.json','analysis/SUMMARY.json','profile_analysis/SUMMARY.json'}|{'profile_analysis/'+j['label']+'.json' for j in jobs('profile') if j.get('tool')=='nsys'}
def derived_sources(w):
    source=w/'source' if (w/'source').is_dir() else REPO
    here=source/'artifacts/dependency_update_mechanism_20261017'
    return {**{n:sha(here/n) for n in ('analyze.py','profile.py')},'bind.py':sha(Path(__file__))}
def require_derived(w,closed=None):
    w=Path(w);closed=closed or require_closed(w);proof=load(w/'DERIVED_IDENTITY.json')
    assert proof['passed'] and proof['independently_recomputed'] and proof['closed_identity_sha256']==sha(w/'CLOSED_IDENTITY.json') and proof['sources']==derived_sources(w)
    assert set(proof['files'])==derived_names(w)
    for folder in ('analysis','profile_analysis'):
        assert {folder+'/'+p.name for p in (w/folder).iterdir()}=={n for n in derived_names(w) if n.startswith(folder+'/')}
    for n,r in proof['files'].items():digest(w/n,r['sha256'],r['bytes'])
    return proof
def seal_derived(w):
    require_closed(w);assert not (w/'DERIVED_IDENTITY.json').exists();recheck=w/'derived_recheck';recheck.mkdir()
    source=w/'source' if (w/'source').is_dir() else REPO;here=source/'artifacts/dependency_update_mechanism_20261017'
    for script,folder in (('analyze.py','analysis'),('profile.py','profile_analysis')):
        with (recheck/(script+'.log')).open('x') as f:subprocess.run([sys.executable,str(here/script),'--work',str(w),'--out',str(recheck/folder)],stdout=f,stderr=f,check=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    for folder in ('analysis','profile_analysis'):
        assert {folder+'/'+p.name for p in (w/folder).iterdir()}=={n for n in derived_names(w) if n.startswith(folder+'/')}
        assert {folder+'/'+p.name for p in (recheck/folder).iterdir()}=={n for n in derived_names(w) if n.startswith(folder+'/')}
    for n in derived_names(w):assert sha(w/n)==sha(recheck/n),('Derived result differs from independent reconstruction',n)
    require_closed(w);save(w/'DERIVED_IDENTITY.json',dict(passed=True,independently_recomputed=True,closed_identity_sha256=sha(w/'CLOSED_IDENTITY.json'),sources=derived_sources(w),files={n:dict(sha256=sha(w/n),bytes=(w/n).stat().st_size) for n in sorted(derived_names(w))}));require_derived(w);print('DERIVED_IDENTITY_PASS',flush=True)
def run(w):
    assert not (w/'CLOSED_IDENTITY.json').exists();reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');digest(w/'REGISTERED.json',ready['registration_sha256']);assert ready['passed']
    source=w/'source' if (w/'source').is_dir() else REPO
    for name,h in reg['sources'].items():digest(source/name,h)
    for name,h in load(w/'POSTPROCESSOR_SOURCE.json')['files'].items():digest(source/'artifacts/dependency_update_mechanism_20261017'/name,h)
    for name,h in reg['generated'].items():digest(w/name,h)
    for trace,h in ready['binaries'].items():digest(w/'build'/trace/'service',h)
    digest(w/'build/oracle.so',ready['oracle_sha256']);digest(source/'artifacts/dependency_update_mechanism_20261017/GPU_CONTRACT.json',reg['contract_sha256'])
    for name,h in reg['inputs'].items():digest(name,h)
    for stage in STAGES:exact_stage(w/stage,reg['schedule'][stage])
    uuid=re.search(r'GPU UUID\s*:\s*(GPU-\S+)',load(w/'HOST_BEFORE_GPU.json')['commands']['GPU']['output']).group(1)
    starts=[json.loads(line) for line in (w/'STARTS.jsonl').read_text().splitlines()];assert len(starts)==368;at=0;rechecked=0;sealed=set();first_guard=None
    for stage in STAGES:
        expected=jobs(stage);assert expected==reg['schedule'][stage];registered=load(w/stage/'REGISTERED.json');assert registered['jobs']==expected and registered['registration_sha256']==sha(w/'REGISTERED.json')
        assert registered['campaign_sha256']==reg['sources']['artifacts/dependency_update_mechanism_20261017/campaign.py']
        result=load(w/stage/'RESULTS.json');assert result['complete'];census(result['rows'],expected)
        for row,j in zip(result['rows'],expected):
            label=j['label'];prefix=w/stage/'outputs'/label;cmd=command(j,w,reg,prefix);cp=w/stage/(label+'.command.json');assert load(cp)==dict(command=cmd)
            at+=1;assert starts[at-1]==dict(start=at,stage=stage,label=label,command_sha256=sha(cp))
            checked_path=w/stage/(label+'.checked.json');digest(checked_path,row['checked_sha256']);old=load(checked_path)
            guard=w/stage/'guards'/label;digest(guard/'receipt.json',row['guard_sha256']);r=load(guard/'receipt.json')
            wanted=['numactl','--cpunodebind='+str(reg['numa']),'--membind='+str(reg['numa']),*cmd];assert r['command']==wanted and load(guard/'command.json')==wanted
            assert r['runtime_valid'] and r['exit_code']==0 and r['stop_reason'] is None and r['observer']=='two-sided-starttime-v1';digest(cmd[0],r['binary_sha256'])
            device_identity(r,load(guard/'before.json'),load(guard/'after.json'),reg['gpu'],uuid)
            assert not load(guard/'before.json')['apps'] and not load(guard/'after.json')['apps'] and all(not c['foreign'] for c in load(guard/'checks.json'))
            first_guard=min(first_guard or (guard/'before.json').stat().st_ctime,(guard/'before.json').stat().st_ctime)
            text=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
            if j['kind']=='selftest':
                native=next(json.loads(line) for line in text.splitlines() if line.startswith('{'));assert native['passed'] and native['query_checks']==400 and all(old[k]==v for k,v in native.items())
                assert old['capacity_bit_cases']==36 and old['invalid_rejections']==6 and 'BITCHECK capacity_cases=36 invalid_rejections=6' in text
                if j['tool']!='plain':assert old['sanitizer_zero'] and ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text)
            else:
                payloads(prefix,old['raw_outputs']);actual=check(prefix,j,w,reg);assert actual==old,('Independent CPU quality recheck',label);rechecked+=1
            if j.get('tool')=='nsys':assert (w/stage/'reports'/(label+'.nsys-rep')).is_file() and (w/stage/'reports'/(label+'.sqlite')).is_file()
            if j.get('tool')=='ncu':assert (w/stage/'reports'/(label+'.csv')).is_file()
        for p in (w/stage).rglob('*'):
            if p.is_file():sealed.add(p)
    assert at==368 and rechecked==338
    dependencies=load(w/'DEPENDENCIES_BEFORE_GPU.json');assert dependencies['passed'] and dependencies['GPU_starts']==0 and dependencies['ready_sha256']==sha(w/'READY.json')
    admission=datetime.datetime.fromisoformat(dependencies['verified_UTC']).timestamp();assert admission<first_guard
    external={}
    for name,h in {**dependencies['linked_libraries'],**dependencies['CCCL_header_hashes']}.items():
        p=Path(name);digest(p,h);assert p.stat().st_ctime<=admission and p.lstat().st_ctime<=admission,('Dependency changed since pre-target capture',p.name);external[str(p)]=dict(sha256=h,bytes=p.stat().st_size)
    env={**os.environ,**reg['environment']};resolved=set()
    for trace in ready['binaries']:
        linked=subprocess.check_output(['ldd',str(w/'build'/trace/'service')],env=env,text=True);assert 'not found' not in linked
        for line in linked.splitlines():
            fields=line.split()
            if '=>' in fields and len(fields)>2 and fields[2].startswith('/'):resolved.add(fields[2])
    assert resolved==set(dependencies['linked_libraries'])
    before=load(w/'HOST_BEFORE_GPU.json');tooltime=datetime.datetime.fromisoformat(before['verified_UTC']).timestamp();tools={}
    for label in ('nvcc','nsys','ncu'):
        command0=before['commands'][label]['command'];assert subprocess.check_output(command0,text=True)==before['commands'][label]['output'];p=Path(command0[0]);assert p.stat().st_ctime<=tooltime and p.lstat().st_ctime<=tooltime
        tools[label]=dict(sha256=sha(p),bytes=p.stat().st_size,version_captured_before_targets=True,hash_captured_after_targets=True,ctime_precedes_first_capture=True);external[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
    save(w/'DEPENDENCIES_AFTER_GPU.json',dict(passed=True,linked_libraries_and_CCCL_headers_unchanged=True,pre_target_hash_capture_sha256=sha(w/'DEPENDENCIES_BEFORE_GPU.json'),tools=tools,scope='Pre-target live linked-library/header hashes plus post-target exact hashes/ctime and ldd resolution;not per-process /proc maps or all dynamically loaded plugins'))
    sealed,expected_external=inventory(w);external={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in expected_external}
    # Current auxiliary guard files are sealed now;only receipt digests and
    # checked.raw_outputs were pinned at target completion by the old controller.
    proof=dict(schema=2,registration_sha256=sha(w/'REGISTERED.json'),closure_validator_sha256=sha(Path(__file__)),registered_GPU_and_pre_target_UUID_match_all_guards=True,passed=True,CPU_rechecked_GIST_targets=rechecked,source_guard_ready_command_census_complete=True,raw_payload_set_and_hash_complete=True,auxiliary_guard_files_sealed='post-campaign,not falsely claimed as per-target completion hashes',dependency_scope='Linked resolution/content identities,not process maps',study_files={},external_files=external)
    for p in sorted(sealed):
        if p.is_relative_to(w):proof['study_files'][str(p.relative_to(w))]=dict(sha256=sha(p),bytes=p.stat().st_size)
        else:proof['external_files'][str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
    save(w/'CLOSED_IDENTITY.json',proof);print('BIND_PASS',at,'targets',rechecked,'CPU quality rechecks',len(proof['study_files']),'sealed files',flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--check-seal',action='store_true');p.add_argument('--seal-derived',action='store_true');a=p.parse_args()
    if a.seal_derived:seal_derived(a.work.resolve())
    elif a.check_seal:require_closed(a.work);print('CLOSED_IDENTITY_PASS')
    else:run(a.work.resolve())
if __name__=='__main__':main()
