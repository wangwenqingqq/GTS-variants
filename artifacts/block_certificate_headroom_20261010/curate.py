#!/usr/bin/env python3
"""Whitelist count evidence; retain raw identities without publishing raw vectors."""
import argparse,json,shutil
from pathlib import Path
from run import HERE,sha

def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def main(a):
    r=a.static;u=a.update;dest=a.output;dest.mkdir(exist_ok=False)
    receipt=json.loads((u/'CLOSURE.json').read_text());assert receipt['passed'];assert receipt['static_proof_sha256']==sha(r/'PROOF.json') and receipt['static_verification_raw_sha256']==sha(r/'VERIFY.json') and receipt['update_proof_sha256']==sha(u/'PROOF.json') and receipt['update_results_raw_sha256']==sha(u/'UPDATE_LOCALITY.json')
    copies={'LAYOUT_RESULTS.json':'layout/LAYOUT_RESULTS.json','ORACLE_BLOCK_RESULTS.json':'oracle/ORACLE_BLOCK_RESULTS.json','CERT_SWEEP.json':'certificate/CERT_SWEEP.json','PROOF.json':'evidence/STATIC_PROOF.json','DECISION.json':'evidence/STATIC_DECISION.json','UPDATE_LOCALITY.json':'evidence/STATIC_UPDATE_DEFERRED.json'}
    for source,target in copies.items():p=dest/target;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/source,p)
    v=json.loads((r/'VERIFY.json').read_text());v['fresh_compiler_command']=[('${SOURCE_ROOT}/distance.cpp' if x.endswith('/distance.cpp') else '${RAW_VERIFY}/distance.so' if x.endswith('/distance.so') else x) for x in v['fresh_compiler_command']];v['raw_receipt_sha256']=sha(r/'VERIFY.json');v['curation']='Only source/output paths in compiler command made portable';write(dest/'evidence/STATIC_VERIFY.json',v)
    update=json.loads((u/'UPDATE_LOCALITY.json').read_text())
    for binding in update['bindings'].values():binding['affected_slots_checked_after_each_update']=binding.pop('all_slots_checked_after_each_update')
    update['curation']='Historical all_slots_checked boolean renamed affected_slots_checked; row/event/query numbers unchanged. Untouched slots preserved by construction.';update['raw_results_sha256']=sha(u/'UPDATE_LOCALITY.json');write(dest/'update/UPDATE_LOCALITY.json',update)
    for source,target in [('PROOF.json','D_PROOF.json'),('REGISTERED.json','D_REGISTERED.json'),('CLOSURE.json','CLOSURE.json')]:shutil.copyfile(u/source,dest/'evidence'/target)
    sp=json.loads((r/'PROOF.json').read_text())
    identity={'historical_static_source_hashes':sp['source_hashes'],'delivered_source_hashes':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.cpp','.json','.md') and p.is_file()},'static_driver_changes':['Explicit prior-campaign input replaces hardcoded prior capture directory','Automatic D admission now checks oracle<=30% jointly as specified; actual joint candidate set remains empty','Regression added for joint admission'],'D_driver_changes':['Entry binds static verification to exact proof and all raw files; closure verifies historical exact bindings','Affected-slot scope wording corrected'],'distance_cpp_unchanged':sp['source_hashes']['distance.cpp']==sha(HERE/'distance.cpp'),'historical_source_policy':'Executed copies retained outside Git; raw source hashes are not rewritten as the hardened delivered driver identities','raw_vector_policy':'Data, references, masks, score tables, layouts, ownership arrays and binaries remain outside Git with original manifests'}
    write(dest/'evidence/SOURCE_IDENTITY.json',identity)
    files={str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()};write(dest/'evidence/CURATION_MANIFEST.json',{'files':files,'raw_static_result_hashes':v['result_hashes'],'raw_update_results_sha256':sha(u/'UPDATE_LOCALITY.json'),'curation_scope':'Counts only; exact whitelist, compiler paths portable, affected-slot label corrected; no vector payloads'})
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('static','update','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
