"""Curate scalar evidence by whitelist;never edit or publish private raw inputs."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,csv,hashlib,os,re,shutil,tarfile
from pathlib import Path
from protocol import HERE,REPO,STAGES,load,save,sha
def hardware(w):
    x=load(w/'HOST_BEFORE_GPU.json')['commands'];cpu={r['field'].rstrip(':'):r['data'] for r in __import__('json').loads(x['CPU']['output'])['lscpu']};gpu=x['GPU']['output']
    def value(name):
        m=re.search(r'^\s*'+re.escape(name)+r'\s*:\s*(.+)$',gpu,re.M);assert m,name;return m[1].strip()
    return dict(CPU={k:cpu[k] for k in ('Model name','CPU(s)','Thread(s) per core','Core(s) per socket','Socket(s)','NUMA node(s)')},GPU=value('Product Name'),driver=value('Driver Version'),nvcc=x['nvcc']['output'],NCU=x['ncu']['output'],NSYS=x['nsys']['output'],placement='Single idle GPU with its local NUMA domain',settings='Unmodified device defaults;per-target clock/power/temperature samples retained in private guard logs',scope='New-CPU campaign only;historical old-CPU timings are not current controls')
def raw_files(w,reg):
    roots=[w/s for s in STAGES]+[w/n for n in ('build','cpu','logs','analysis','profile_analysis','derived_recheck','postrun_versions') if (w/n).is_dir()]
    raw={};paths={}
    def add(f,key):
        entry=dict(sha256=sha(f),bytes=f.stat().st_size)
        assert key not in raw or raw[key]==entry,('Conflicting archive member',key)
        raw[key]=entry;paths[key]=f
    for root in roots:
        for f in root.rglob('*'):
            if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts:add(f,str(f.relative_to(w)))
    source=w/'source' if (w/'source').is_dir() else REPO
    for name in reg['sources']:add(source/name,'source/'+name)
    for f in HERE.iterdir():
        if f.is_file():add(f,'curation_source/'+f.name)
    for f in w.iterdir():
        if f.is_file() and f.name not in ('campaign.lock',):add(f,f.name)
    return raw,paths
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--restore',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();w=a.work.resolve();restore=a.restore.resolve();out=a.out.resolve();assert not out.exists();out.mkdir();[(out/n).mkdir() for n in ('evidence','results','timeline')]
    from bind import require_closed,require_derived
    closed=require_closed(w);derived=require_derived(w,closed);reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');rows=[];quality=[];receipts=[]
    for stage in STAGES:
        result=load(w/stage/'RESULTS.json');assert result['complete'] and all(r['status']=='passed' for r in result['rows'])
        assert [{k:v for k,v in row.items() if k not in ('status','checked_sha256','guard_sha256')} for row in result['rows']]==reg['schedule'][stage]
        for row in result['rows']:
            label=row['label'];checked=load(w/stage/(label+'.checked.json'));assert sha(w/stage/(label+'.checked.json'))==row['checked_sha256'] and checked['passed']
            guard=w/stage/'guards'/label;receipt=load(guard/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and sha(guard/'receipt.json')==row['guard_sha256']
            assert not load(guard/'before.json')['apps'] and not load(guard/'after.json')['apps'] and all(not r['foreign'] for r in load(guard/'checks.json'))
            j={k:v for k,v in row.items() if k not in ('checked_sha256','guard_sha256')};rows.append(dict(stage=stage,**j));receipts.append(dict(stage=stage,label=label,guard_sha256=row['guard_sha256'],command_sha256=sha(w/stage/(label+'.command.json')),owned_observer=receipt['observer'],runtime_valid=True,exit_code=0,stop_reason=None,guard_wall_s=receipt['wall_s'],target_binary_sha256=ready['binaries'][str(row['trace'])]))
            q={k:v for k,v in checked.items() if k in ('passed','query_checks','empty_answers','full_hit_FP64_bit_checks','pointer_churn_epochs','capacity_bit_cases','invalid_rejections','sanitizer_zero','complete_queries','formal_queries','complete_hit_records','false_negatives','false_positives','native_squared_bits','internal_FP64_bits','max_native_scaled_error','actual_mutation_witnesses','independent_full_final_maps','all_allocated_bytes_compared','native_moves','final_assignments','expected_RAW','expected_WAW')};quality.append(dict(stage=stage,label=label,**q))
    assert len(rows)==len(receipts)==len(quality)==368 and len((w/'STARTS.jsonl').read_text().splitlines())==368
    save(out/'evidence/EXECUTION.json',dict(complete=True,attempts=368,admitted_targets=368,failed=0,unexecuted=0,stage_counts={s:len(reg['schedule'][s]) for s in STAGES},jobs=rows));save(out/'evidence/QUALITY.json',dict(passed=True,targets=quality));save(out/'evidence/RECEIPTS.json',receipts)
    save(out/'evidence/HARDWARE.json',hardware(w));save(out/'evidence/BUILD.json',dict(ready=ready,static=load(w/'STATIC.json'),generated_source_hashes=reg['generated'],registration_sha256=sha(w/'REGISTERED.json'),GPU_contract_sha256=reg['contract_sha256'],scope='Two freshly compiled containers,six runtime variants;unchanged query function SASS;not runtime evidence by itself'))
    deps=load(w/'DEPENDENCIES_BEFORE_GPU.json');libs={}
    for name,h in deps['linked_libraries'].items():
        key=Path(name).name
        if key in libs:assert libs[key]==h
        libs[key]=h
    cccl_root=Path('/usr/local/cuda-13.1/targets/x86_64-linux/include/cccl');headers={str(Path(n).relative_to(cccl_root)):h for n,h in deps['CCCL_header_hashes'].items()}
    save(out/'evidence/DEPENDENCIES.json',dict(passed=True,linked_libraries_by_filename=libs,CCCL_header_hashes=headers,scope='Content identities only;no library/header code redistributed'))
    def logical(path):
        p=Path(path)
        if str(p)==reg['data']:return 'dataset/GIST1M.f32bin'
        for root,prefix in ((w,'study'),(restore,'restored')):
            if p.is_relative_to(root):return prefix+'/'+str(p.relative_to(root))
        raise AssertionError(('Unreviewed private input route',p.name))
    save(out/'evidence/INPUT_IDENTITY.json',dict(files={logical(n):dict(sha256=h,bytes=Path(n).stat().st_size) for n,h in reg['inputs'].items()},reuse_audit={k:v for k,v in load(w/'INPUT_REUSE_AUDIT.json').items() if k!='portable_input_keys'}))
    save(out/'evidence/SOURCES.json',dict(parent_commit=reg['parent_commit'],executed_sources=reg['sources'],postprocessor_sources=load(w/'POSTPROCESSOR_SOURCE.json'),generator='generate.py reuses frozen NativeStore and all selected query functions;see BUILD for generated hashes'))
    save(out/'evidence/CLOSED_BINDING.json',dict(passed=True,proof_sha256=sha(w/'CLOSED_IDENTITY.json'),CPU_rechecked_GIST_targets=closed['CPU_rechecked_GIST_targets'],registered_GPU_and_pre_target_UUID_match_all_guards=closed['registered_GPU_and_pre_target_UUID_match_all_guards'],sealed_study_files=len(closed['study_files']),sealed_external_files=len(closed['external_files']),auxiliary_guard_hash_timing=closed['auxiliary_guard_files_sealed'],dependency_scope=closed['dependency_scope'],dependency_postcheck={k:v for k,v in load(w/'DEPENDENCIES_AFTER_GPU.json').items() if k!='tools'}))
    save(out/'evidence/DERIVED_BINDING.json',dict(**derived,proof_sha256=sha(w/'DERIVED_IDENTITY.json')))
    shutil.copy2(w/'cpu/traces/RESULTS.json',out/'evidence/CPU_TRACE_CENSUS.json');shutil.copy2(w/'cpu/CPU_EVIDENCE_R1.json',out/'evidence/CPU_EVIDENCE.json')
    for name in ('SUMMARY.json','PROCESSES.json'):shutil.copy2(w/'analysis'/name,out/'results'/name)
    profile=load(w/'profile_analysis/SUMMARY.json');assert profile['passed']
    for label,record in profile['records'].items():
        if label.startswith('ncu_'):
            record['records']=[{k:v for k,v in r.items() if k in ('ID','Kernel Name','Metric Name','Metric Unit','Metric Value','parsed_value')} for r in record['records']]
        else:
            trace=load(w/'profile_analysis'/(label+'.json'))
            with (out/'timeline'/(label+'.csv')).open('x') as f:
                writer=csv.DictWriter(f,fieldnames=list(trace['ranges'][0]),lineterminator='\n');writer.writeheader();writer.writerows(trace['ranges'])
    save(out/'results/PROFILE.json',profile)
    # Archive a closed raw/admin/source whitelist,not dataset or input symlinks.
    raw,paths=raw_files(w,reg)
    (w/'archives').mkdir();archive=w/'archives/STUDY_RAW_R1.tgz'
    with tarfile.open(archive,'x:gz',compresslevel=3) as tar:
        for name,entry in sorted(raw.items()):
            f=paths[name];assert sha(f)==entry['sha256'];tar.add(f,arcname='study/'+name,recursive=False)
    seen=set()
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            assert member.isfile() and member.name.startswith('study/');name=member.name[6:];assert name in raw and name not in seen;seen.add(name);h=hashlib.sha256();f=tar.extractfile(member)
            for block in iter(lambda:f.read(4<<20),b''):h.update(block)
            assert member.size==raw[name]['bytes'] and h.hexdigest()==raw[name]['sha256']
    assert seen==set(raw)
    save(out/'evidence/RAW_MANIFEST.json',dict(files=raw,scope='Private closed raw/admin/source whitelist;logical member names only;large vectors excluded'))
    save(out/'evidence/CUSTODY.json',dict(passed=True,archive='STUDY_RAW_R1.tgz',archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,members=len(raw),uncompressed_bytes=sum(r['bytes'] for r in raw.values()),every_member_size_and_SHA256_verified=True,public_archive_download=False,source_of_truth='Persistent private raw archive;public manifests establish identity,not public raw availability'))
    print('CURATED_AND_ARCHIVE_VERIFIED',len(raw),'members',archive.stat().st_size,'archive bytes',flush=True)
if __name__=='__main__':main()
