#!/usr/bin/env python3
"""Portable bounded-probe evidence; never promotes the strict API or E2 gates."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
from audit import HERE,sha,save


def curate(root,reference,out):
    out.mkdir(exist_ok=False)
    probe=root/'probe_v7_gpu7'
    guard=json.loads((root/'probe_v7_gpu7_guard/receipt.json').read_text())
    if not guard['runtime_valid']:raise ValueError('invalid whole-probe guard')
    oracle=reference.read_bytes();n,d,q,k=struct.unpack_from('<4i',oracle)
    expected=(struct.pack('<4i',n,d,2,k)+oracle[16:16+2*k*4]+
              oracle[16+q*k*4:16+q*k*4+2*k*8])
    subsets={}
    for tool in ['memcheck','initcheck','synccheck']:
        for mode in ['G0','G3']:
            label=tool+'_'+mode;folder=probe/label
            receipt=json.loads((folder/'receipt.json').read_text())
            log=(folder/'stdout.log').read_text()+(folder/'stderr.log').read_text()
            if receipt['exit_code'] or receipt['timed_out'] or 'ERROR SUMMARY: 0 errors' not in log:raise ValueError(label)
            if (folder/'out.bin').read_bytes()!=expected:raise ValueError('reference mismatch '+label)
            subsets[label]={'exit_code':0,'reported_errors':0,'API_reporting':'no',
                           'query_count':2,'oracle_bitwise_equal':True,'strict_API_pass':False}
    smokes={}
    smoke_guard=json.loads((root/'api_smoke_guard/receipt.json').read_text())
    if not smoke_guard['runtime_valid']:raise ValueError('API smoke ownership invalid')
    for name,errors in [('plain',0),('original_headers',2)]:
        folder=root/'api_smoke'/(name+'_default_memcheck')
        log=(folder/'stdout.log').read_text()
        if 'ERROR SUMMARY: '+str(errors)+' errors' not in log:raise ValueError('smoke summary drift')
        rc=json.loads((folder/'receipt.json').read_text())['exit_code']
        if rc!=(86 if errors else 0):raise ValueError('smoke exit drift')
        smokes[name]={'exit_code':rc,'reported_errors':errors,'query_executed':False,
                     'API_reporting':'default','binary_sha256':sha(root/'api_smoke'/name),
                     'error_kind':'cuLibraryGetKernel CUDA_ERROR_NOT_FOUND(500)' if errors else None}
    save(out/'SANITIZER_SUMMARY.json',{'stage':'partial localization; not full E2 or strict API pass',
        'tool':'compute-sanitizer 2025.4.1.0','probe_binary_sha256':json.loads((probe/'IDENTITY.json').read_text())['bench_sha256'],
        'first_two_dev_ids':list(map(int,(probe/'first2.qid').read_text().split()))[1:],
        'v7_subsets':subsets,'default_API_smokes':smokes,'whole_probe_exclusive_valid':True,
        'v6_failure':{'initcheck':'uninitialized 8-byte CUB ThreadLoad<NavKey> read',
            'original_layout':'double score; int id; implicit 4-byte padding',
            'time_limit_seconds':600,'whole_guard_valid':False,
            'timeout_orphans_stopped':'exact owned UID/command/starttime checks; no foreign signals'},
        'uniform_v7_fix':'explicit zero-initialized reserved int, same sizeof 16',
        'strict_API_gate_passed':False,'full_E2_matrix_passed':False,'formal_processes_used':0,
        'diagnosis':'Original unmodified-header smoke reproduces API failure without tree/query/memo; not proof of a harmless API waiver.'})
    module_path=HERE.parent.parent/'diagnostics/native_knn_faiss_ivf_20261003/analyze_profiles.py'
    spec=importlib.util.spec_from_file_location('shared_profile_analyzer',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result={}
    for mode in ['G0','G3']:
        folder=probe/('nsys_'+mode)
        if (folder/'out.bin').read_bytes()!=expected:raise ValueError('profile reference mismatch')
        t=module.trace(folder/'trace.sqlite')
        t['scope']='First two frozen E1 dev queries K8/B1; resident query ID input; diagnostic-only; legacy NVTX formal.query_pass is not E3'
        result[mode]=t
    save(out/'NSYS_SUMMARY.json',{'stage':'diagnostic-only','tool':'Nsight Systems 2025.5.2.266',
        'whole_guard_exclusive_valid':True,'shared_analyzer_sha256':sha(module_path),
        'profiles':result,'CPU_utilization_measured':False,'NCU_collected':False,
        'strict_API_gate_passed':False,'formal_processes_used':0})
    save(out/'RAW_MANIFEST.json',{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})
    print('PASS portable sanitizer/NSYS subset receipts; E2 and strict API remain incomplete')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('reference',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();curate(a.root,a.reference,a.out)
