#!/usr/bin/env python3
"""Post-close verifier; explicitly distinguish frozen pins from later bindings."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);p.add_argument('data',type=Path);p.add_argument('native_reference',type=Path);a=p.parse_args();r=a.root;prior=a.prior
    old=read(prior/'CLOSURE.json');inputs=read(prior/'INPUTS.json');reg=read(r/'REGISTERED.json');contract=read(r/'CONTRACT.json');closure=read(r/'analysis_v1/CLOSURE.json')
    assert old['passed'] and old['inputs_sha256']==sha(prior/'INPUTS.json') and old['registration_sha256']==sha(prior/'REGISTERED.json')
    assert old['contract_sha256']==sha(prior/'CONTRACT.json') and closure['registered_sha256']==sha(r/'REGISTERED.json')
    assert closure['contract_sha256']==reg['contract_sha256']==sha(r/'CONTRACT.json')
    assert closure['result_sha256']==sha(r/'analysis_v1/RESULT.json') and closure['snapshot_manifest_sha256']==sha(r/'analysis_v1/SNAPSHOT_MANIFEST.json')
    assert reg['binary_sha256']==sha(r/'observer') and reg['build_log_sha256']==sha(r/'build.log') and reg['source_audit_sha256']==sha(r/'SOURCE_AUDIT.json')
    preverified={}
    for name,h in reg['source'].items():assert sha(r/'observer_source'/name)==h;preverified['observer_source/'+name]=h
    for name,h in reg['case'].items():assert sha(prior/'cases/target'/name)==h;preverified['case/'+name]=h
    retained=read(r/'PRIOR_RAW_FILE_MANIFEST.json');priorchecks={}
    for name,h in inputs['inputs'].items():
        if name.startswith(('checker/','deps/','P2/source/','cases/target/')) or name in ('P2/bench','P2/BUILD.json','P2/SOURCE_PINS.json'):
            assert sha(prior/name)==h;priorchecks[name]=h
    for name,h in inputs['reference'].items():
        assert sha(a.native_reference.parent/name)==h;priorchecks['native_reference/'+name]=h
    baseline={}
    for f in sorted((prior/'primary/outputs').glob('r1_P2.*')):
        name=str(f.relative_to(prior));assert sha(f)==retained[name]['sha256'];baseline[name]=sha(f)
    quality=read(prior/'primary/outputs/r1_P2.quality.json')
    for phase,report in quality.items():
        assert report['passed'];prefix=str(prior/'primary/outputs/r1_P2')+('' if phase=='measured' else phase)
        for suffix,h in report['payload_hashes'].items():assert sha(prefix+suffix)==h
    assert sha(a.data)==inputs['data_sha256']==contract['data_sha256']
    audit=read(r/'SOURCE_AUDIT.json')
    for name,h in audit['keeper_files'].items():assert sha(prior/'P2/source'/name)==h
    manifest=read(r/'summary_v2/SNAPSHOT_MANIFEST.json');assert manifest==read(r/'analysis_v1/SNAPSHOT_MANIFEST.json')
    for f in manifest:assert (r/'snapshots'/f['file']).stat().st_size==f['bytes'] and sha(r/'snapshots'/f['file'])==f['sha256']
    assert sha(r/'summary_v2/RESULT.json')==sha(r/'summary_v2_repeat/RESULT.json'),'CPU deterministic reanalysis'
    assert sha(r/'runtime/receipt.json')==closure['runtime_sha256']
    runtime=read(r/'runtime/receipt.json');assert runtime['runtime_valid'] and runtime['exit_code']==0 and runtime['stop_reason'] is None and runtime['binary_sha256']==reg['binary_sha256']
    assert not read(r/'runtime/before.json')['apps'] and not read(r/'runtime/after.json')['apps']
    assert all(not x['foreign'] for x in read(r/'runtime/checks.json'))
    current=subprocess.check_output(['nvidia-smi','-i','1','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip();assert not current
    q=read(r/'QUALITY.json');assert q['passed'] and sha(r/'QUALITY.json')==closure['quality_sha256']
    for suffix,h in q['payload_hashes'].items():assert sha(str(r/'outputs/observer')+suffix)==h
    post_bound={str(f.relative_to(r)):sha(f) for folder in ('scripts','analysis_v1','summary_v2','summary_v2_repeat','runtime') for f in sorted((r/folder).rglob('*')) if f.is_file()}
    post_bound.update({str(f.relative_to(r)):sha(f) for f in sorted((r/'outputs').glob('*')) if f.is_file()})
    analysis_count=sum((r/folder/'RESULT.json').is_file() for folder in ('analysis_v1','analysis_intermediate_v2','summary_v2','summary_v2_repeat'))
    report={'passed':True,'target_GPU_processes':1,'optional_GPU_repeat_used':False,'CPU_reanalyses_after_v1':analysis_count-1,'CPU_full_analyses_total':analysis_count,
      'contract_sha256':sha(r/'CONTRACT.json'),'registered_sha256':sha(r/'REGISTERED.json'),'original_closure_sha256':sha(r/'analysis_v1/CLOSURE.json'),
      'quality_sha256':sha(r/'QUALITY.json'),'final_result_sha256':sha(r/'summary_v2/RESULT.json'),'snapshot_manifest_sha256':sha(r/'summary_v2/SNAPSHOT_MANIFEST.json'),
      'prior_campaign_inputs_sha256':sha(prior/'INPUTS.json'),'prior_campaign_closure_sha256':sha(prior/'CLOSURE.json'),
      'prior_raw_file_manifest_sha256':sha(r/'PRIOR_RAW_FILE_MANIFEST.json'),
      'preregistered_observer_binary':reg['binary_sha256'],'preregistered_observer_source_and_case':preverified,
      'prior_frozen_dependencies_reverified':priorchecks,'prior_manifest_bound_baseline_outputs':baseline,'post_close_file_bindings':post_bound,
      'snapshot_files':len(manifest),'snapshot_bytes':sum(f['bytes'] for f in manifest),'all_snapshot_bytes_rehashed_on_host':True,
      'GPU_clear_after':True,'disclosure':'New registration bound binary/source/case but not every runner/checker/reference script; prior-campaign pins and raw manifest were reverified post-close. Scripts and CPU v2 changes are explicitly post-close bindings, not retroactive preregistration. Original contract, analysis and result retained.'}
    (r/'FINAL_CLOSURE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('passed','snapshot_files','snapshot_bytes','target_GPU_processes','final_result_sha256')}))
if __name__=='__main__':main()
