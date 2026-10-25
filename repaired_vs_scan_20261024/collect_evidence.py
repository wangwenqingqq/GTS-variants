"""Curate complete-epoch text evidence; retain large outputs privately by hash."""
import gzip,hashlib,json,re,subprocess,sys
from pathlib import Path
from analyze_campaign import summarize

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def redact(value,root):
    if isinstance(value,dict):return {k:redact(v,root) for k,v in value.items()}
    if isinstance(value,list):return [redact(v,root) for v in value]
    if isinstance(value,str):
        value=value.replace(str(root),'${TASK_SCRATCH}')
        value=re.sub(r'/(?:home|Users)/[^\s,\"\']+','${REDACTED_PATH}',value)
        return value
    return value

def main(root,epoch,out):
    root=Path(root).resolve();epoch=Path(epoch).resolve();out=Path(out).resolve();assert not out.exists();out.mkdir()
    assert epoch.parent==root/'runs' and (epoch/'TIMING_COMPLETE.json').exists() and not (epoch/'INVALID_EPOCH.json').exists()
    frozen=json.loads((root/'FROZEN_CPU_ORACLE.json').read_text());end_inputs={}
    for name,v in frozen['files'].items():
        if name.startswith('fixtures/'):
            got=sha(root/name);assert got==v['sha256'],name;end_inputs[name]=got
    assert sha(root/'fixtures/calibration.json')==frozen['calibration_sha256']
    end_inputs['fixtures/calibration.json']=frozen['calibration_sha256']
    (out/'FROZEN_INPUTS_END.json').write_text(json.dumps(end_inputs,indent=2)+'\n')
    summarize(epoch,out)
    bundle={};manifest={};sanitizer={};counters={}
    for run in sorted(epoch.iterdir()):
        if not run.is_dir() or not (run/'receipt.json').exists():continue
        rec=json.loads((run/'receipt.json').read_text())
        for name,digest in rec['result_files'].items():assert Path(name).name==name and sha(run/name)==digest,(run,name)
        entry={}
        for name in ['receipt.json','before.json','after_initial.json','after.json','admission_wait.json','settling.json','checks.json','result.json','result.work.json']:
            p=run/name
            if p.exists():entry[name]=json.loads(p.read_text())
        for name in ['stdout.log','stderr.log']:
            p=run/name
            if p.exists():entry[name]=p.read_text()
        bundle[run.name]=entry
        for p in run.iterdir():
            if p.is_file():manifest[str(p.relative_to(root))]={'sha256':sha(p),'bytes':p.stat().st_size,'publication':('normalized_raw_samples.csv' if p.name=='result.csv' else ('curated_process_bundle' if p.name.endswith(('.json','.log')) else 'hash_only'))}
        if rec['tool']:sanitizer[run.name]={'tool':rec['tool'],'arm':rec['arm'],'dataset':rec['kind'],'k':rec['k'],'exit_code':rec['exit_code'],'valid':rec['valid'],'receipt_sha256':sha(run/'receipt.json'),'stdout_sha256':sha(run/'stdout.log'),'stderr_sha256':sha(run/'stderr.log')}
        if rec['instrumented']:counters[run.name]={'dataset':rec['kind'],'Q':rec['Q'],'k':rec['k'],'arm':rec['arm'],'oracle_correct':rec['exit_code']==0,'work':entry['result.work.json'],'binary_sha256':rec['binary_sha256'],'receipt_sha256':sha(run/'receipt.json')}
    public=redact(bundle,root);text=json.dumps(public,separators=(',',':'))
    assert not re.search(r'/(?:Users|home|root)/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}',text,re.I)
    (out/'PROCESS_EVIDENCE.json.gz').write_bytes(gzip.compress(text.encode(),mtime=0))
    for name,v in [('RAW_MANIFEST.json',manifest),('SANITIZERS.json',sanitizer),('WORK_COUNTS.json',counters)]:
        (out/name).write_text(json.dumps(v,indent=2)+'\n')
    for name in ['admission.json','binaries.json','source_plan.json','FULL_QUALITY.json','GATES_PASS.json','COUNT_COLLECTED.json','TIMING_SCHEDULE.json','TIMING_COMPLETE.json']:
        value=redact(json.loads((epoch/name).read_text()),root);(out/name).write_text(json.dumps(value,indent=2)+'\n')
    diagnosis=json.loads((root/'logs/exactness_boundary_A.json').read_text())
    for case in diagnosis['mismatches']:
        for point in case['points']:
            point.pop('query_coordinates',None);point.pop('point_coordinates',None)
    diagnosis['raw_diagnosis_sha256']=sha(root/'logs/exactness_boundary_A.json')
    diagnosis['raw_input_coordinates_published']=False
    (out/'EXACTNESS_FAILURE.json').write_text(json.dumps(diagnosis,indent=2)+'\n')
    archives={}
    for other in (root/'runs').iterdir():
        if not other.is_dir() or other==epoch:continue
        markers={p.name:json.loads(p.read_text()) for p in other.glob('*.json') if any(s in p.name for s in ['FAILED','INVALID','STOPPED'])}
        if markers:archives[other.name]={'markers':redact(markers,root),'timing_process_directories':len(list(other.glob('time_*')))}
    (out/'RETAINED_ATTEMPTS.json').write_text(json.dumps(archives,indent=2)+'\n')
    source={}
    for name in ['campaign_quality_support_v4.py','quality_campaign_v4.py','bench_io.hpp','arborx_bench.cpp','arborx_count_fast.cpp','build_v3/bench.cu','build_v3/bench_count.cu','build_v3/source_pins.json']:
        source[name]={'sha256':sha(root/name),'bytes':(root/name).stat().st_size}
    for p in (root/'build_v3/source').rglob('*'):
        if p.is_file() and p.suffix in ('.cu','.cuh') and not p.name.startswith('._'):source[str(p.relative_to(root))]={'sha256':sha(p),'bytes':p.stat().st_size}
    pins=json.loads((root/'build_v3/source_pins.json').read_text())
    for name,digest in pins.items():assert sha(root/'original_source'/name[4:])==digest
    plan=json.loads((epoch/'source_plan.json').read_text())
    assert source['campaign_quality_support_v4.py']['sha256']==plan['monitor_sha256']
    assert source['quality_campaign_v4.py']['sha256']==plan['planner_sha256']
    dep={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in (root/'deps/install').rglob('libkokkos*.a')}
    config=root/'deps/install/include/KokkosCore_config.h';assert '#define KOKKOS_ARCH_BLACKWELL120' in config.read_text() and '#define KOKKOS_ENABLE_CUDA\n' in config.read_text()
    cal=json.loads((root/'fixtures/calibration.json').read_text());qset=set(cal['datasets']['words']['test_qids']);maxword=0;maxquery=0;rows=0
    with (root/'fixtures/words.txt').open('rb') as f:
        f.readline()
        for i,line in enumerate(f):
            length=len(line[:-1] if line.endswith(b'\n') else line);maxword=max(maxword,length)
            if i in qset:maxquery=max(maxquery,length)
            rows+=1
    assert rows==611756 and maxword<109 and maxquery<=40
    build={'word_layout_limits':{'max_original_loader_word_length':maxword,'max_frozen_query_word_length':maxquery,'original_stride':109,'scan_row_capacity':41},'original_source_pins_verified_at_end':True,'kokkos_commit':'82799e4577568f9666bde36265ac15d78da3e6c8','kokkos_release':'4.7.04','arborx_commit':'3a20eaba22bd8b6c13d6b32064a2086a3ce1c993','cuda':'13.1.115','driver':'590.48.01','arch':'sm_120','fast_math':False,'gts_nvcc_flags':'-std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -Xptxas=-v','kokkos_backends':['CUDA','SERIAL'],'native_CXX_standard':20,'native_target_optimization':'-O2 (last option after Release -O3 -DNDEBUG flags; explicit full-output if/exit checks remain active)','kokkos_config_sha256':sha(config),'source_artifacts':source,'native_static_libraries':dep,'user_local_install':True,'GPU_settings_changed':False,'normal_timing_binaries_unchanged_during_epoch':True}
    (out/'BUILD_PROVENANCE.json').write_text(json.dumps(build,indent=2)+'\n')
    for name in ['bench_v3.resources.txt','arborx.resources.txt']:
        p=root/'static'/name
        if p.exists():(out/name).write_text('\n'.join(line.rstrip() for line in redact(p.read_text(),root).splitlines())+'\n')
    checks={'process_evidence_uncompressed_sha256':hashlib.sha256(text.encode()).hexdigest(),'raw_manifest_entries':len(manifest),'sanitizer_runs':len(sanitizer),'instrumented_runs':len(counters),'full_frozen_input_hashes_match_at_end':True,'private_path_scan':'pass','GPU_samples_are_real':'synthetic CPU tests are separate and never included'}
    (out/'COLLECTION_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n');print('CURATED',checks)
if __name__=='__main__':main(*sys.argv[1:])
