"""Verify complete external evidence, then export only portable scalar receipts."""
import argparse
import json
from pathlib import Path
from campaign import STAGES, verify_prepared, verify_stage
from prepare import read, save, sha

def curate(work,output):
    reg,ready,build=verify_prepared(work)
    for stage in STAGES:verify_stage(work,stage,reg['gpu'],reg['numa'])
    starts=[json.loads(v) for v in (work/'STARTS.jsonl').read_text().splitlines()]
    assert len(starts)==75 and [v['start'] for v in starts]==list(range(1,76))
    output.mkdir(exist_ok=False)
    samples=[];receipts=[]
    for stage in STAGES:
        for row in read(work/stage/'RESULTS.json')['rows']:
            q=read(work/stage/(row['label']+'.checked.json'))
            samples.append(dict(stage=stage,label=row['label'],B=row['B'],N=row['N'],round=row.get('round'),order=row.get('order'),diagnostic=bool(row['diagnostic']),mean_invocation_ms=q['mean_invocation_ms'],mean_query_ms=q['mean_query_ms'],continuous_pass_ms=q['pass_ms'],measured_invocation_ms=q['invocation_ms'],mean_measured_hits=q['mean_measured_hits'],scope='complete output ACK; profiler rows diagnostic-only'))
            receipts.append(dict(stage=stage,label=row['label'],passed=True,all_complete_members=q['all_complete_members'],max_native_scale_error=q['max_native_scale_error'],B1_original_payload_identity=q['B1_original_payload_identity'],payload_hashes=q['payload_hashes'],output_hashes=q['output_hashes'],command_record_sha256=sha(work/stage/(row['label']+'.command.json')),checked_sha256=row['checked_sha256'],guard_sha256=row['guard_sha256'],report_hashes=row['report_hashes']))
    inputs=dict(data_sha256=reg['data_sha256'],original_keeper_sha256=reg['keeper_sha256'],CPU_oracle_sha256=reg['cpu_sha256'],host_batch_binary_sha256=build['binary_sha256'],exact_libraries=build['libraries'],pool_hashes=ready['pool_hashes'],query_pool_seed=reg['seed'],original_pool_size=len(reg['q32']),extended_pool_size=len(reg['q128']),extended_pool_unique=len(set(reg['q128'])),CPU_bit_conformance=ready['CPU_bit_conformance'],query_pool_frozen_before_GPU=ready['query_pool_frozen_before_GPU'],registration_sha256=sha(work/'REGISTERED.json'),READY_sha256=sha(work/'READY.json'),build_registration_sha256=sha(work/'build/BUILD.json'),contract_sha256=ready['contract_sha256'],frozen_measurement_sources=ready['source_hashes'],placement='same prior privately pinned physical GPU and matching NUMA; private deployment identifiers excluded')
    save(output/'INPUT_IDENTITY.json',inputs)
    save(output/'PROCESS_SAMPLES.json',samples)
    save(output/'QUALITY_RECEIPTS.json',receipts)
    save(output/'EXECUTION_CLOSURE.json',dict(passed=True,top_level_starts=len(starts),planned_starts=75,budget_cap=80,stage_counts={s:sum(v['stage']==s for v in starts) for s in STAGES},same_physical_device=True,all_two_sided_isolation_receipts_valid=True,all_complete_output_checks_passed=True,all_raw_output_report_hashes_reverified=True,all_registered_queries_and_reference_hashes_reverified=True,raw_STARTS_sha256=sha(work/'STARTS.jsonl'),raw_stage_registration_hashes={s:sha(work/s/'REGISTERED.json') for s in STAGES},raw_stage_results_hashes={s:sha(work/s/'RESULTS.json') for s in STAGES},preserved_CPU_preflight_failures=1,GPU_failures=0))
    inventory=read(work/'qualification/NATIVE_LAUNCH_INVENTORY.json')
    save(output/'NATIVE_LAUNCH_INVENTORY.json',inventory)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();curate(a.work,a.output)
