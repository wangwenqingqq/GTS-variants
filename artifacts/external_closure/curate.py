#!/usr/bin/env python3
"""Whitelist Stage A proof summaries; never copy raw receipts, paths or vectors."""
import argparse,json
from pathlib import Path
from common import outside_repo
import qualify
sha=qualify.cpu.sha

def main(a):
    destination=outside_repo(a.output);destination.mkdir(parents=True,exist_ok=False)
    proof=json.loads((a.work/'FINAL_QUALIFICATION.json').read_text())
    binding_path=a.binding or a.work/'ADMISSION_BINDING.json'
    binding=json.loads(binding_path.read_text())
    from verify_a import verify
    actual=verify(a.work,proof,a.work/'CPU_TREE_EDGES_V2.json',a.work/'CPU_FLAT_EDGES_V2.json')
    assert all(binding[k]==v for k,v in actual.items())
    assert binding['original_proof_sha256']==sha(a.work/'FINAL_QUALIFICATION.json')
    assert proof['GPU_RANGE_admission'] and proof['CPU_tree_admission'] and proof['CPU_FLAT_INCLUSIVE_ADAPT_admission']
    assert not proof['GPU_TREE_admission'] and proof['primary_processes']==0
    checks={}
    for name,r in proof['checks'].items():
        checks[name]=dict(passed=r['passed'],queries=len(r['per_query']),
            failed_queries=[q['query'] for q in r['per_query'] if not q['passed']],
            minimum_recall=min((q['recall_tie_aware'] for q in r['per_query'] if q.get('recall_tie_aware') is not None),default=None),
            native_squared_observed=r['native_squared_observed'],output_hashes=r['output_sha256'])
    result=dict(status=proof['status'],source='5598585c9405574de3fee8451c5b0d9b5d98dbcd',
        scope=dict(dataset='original FP32 GIST',N=1000000,D=960,B=1,K=8,radius_bits='0x3f34a3d8',snapshots=['initial','first_rebuilt'],
            queries_per_snapshot_per_supported_task=32,timing='qualification/development only; no new primary performance claim'),
        CPU_selected=proof['CPU_selected'],CPU_development=[{k:r[k] for k in ('method','leaf','cost_ms')} for r in proof['CPU_rows']],
        development_coordinate_disjointness=proof['development_coordinate_disjointness'],
        GPU_processes=proof['GPU_processes'],new_primary_processes=0,primary_ceiling=102,
        checks=checks,receipts=proof['receipts'],tree_first_call_byte_and_selected_tree_identity=proof['tree_first_call_byte_and_selected_tree_identity'],
        GPU_TREE_blocker=proof['GPU_TREE_blocker'],GPU_TREE_admission=False,GPU_RANGE_admission=True,
        CPU_FLAT_native_boundary_passed=proof['CPU_FLAT_native_boundary_passed'],CPU_FLAT_INCLUSIVE_ADAPT_admission=True,
        CPU_boundary_proof_sha256=proof['CPU_boundary_proof_sha256'],CPU_FLAT_inclusive_proof_sha256=proof['CPU_FLAT_inclusive_proof_sha256'],
        complete_private_proof_sha256=sha(a.work/'FINAL_QUALIFICATION.json'),checker_sha256=proof['checker_sha256'],payload_checker_sha256=proof['payload_checker_sha256'])
    result.update(admission_binding_sha256=sha(binding_path),admission_binding=binding)
    qualify.save(destination/'A_RESULTS.json',result)
    print(destination/'A_RESULTS.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--binding',type=Path);a=p.parse_args();main(a)
