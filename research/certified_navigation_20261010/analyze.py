#!/usr/bin/env python3
"""Curate portable, query-scoped E1 evidence; preserve private raw sources unchanged."""
import argparse
import csv
import json
from pathlib import Path
import shutil
from audit import sha,save
from verify import result,traces


def write_csv(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def curate(root,cpu_reference,out):
    validation=json.loads((root/'E1_FINAL_VALIDATION.json').read_text())
    guard=json.loads((root/'guard/receipt.json').read_text())
    if not guard['runtime_valid'] or validation['gpu_admission_pending']:raise ValueError('missing final exclusive receipt')
    oracle,shape=result(root/'oracle.bin')
    if cpu_reference.read_bytes()!=oracle:raise ValueError('independent CPU reference mismatch')
    work={m:list(csv.DictReader((root/m/'out.work.csv').open())) for m in ['G0','G1','G2','G3']}
    out.mkdir(parents=True,exist_ok=False);summary={};joint=[];thresholds=[]
    for mode,rows in work.items():
        memo=work['G1' if mode in ('G0','G1') else 'G3']
        timeline=traces(root/mode/'stdout.log')
        t=list(csv.DictReader((root/('timing_'+mode)/'out.csv').open()))
        if len(t)!=1:raise ValueError('unexpected diagnostic process count')
        geometry=[json.loads(x[9:]) for x in (root/mode/'stdout.log').read_text().splitlines() if x.startswith('GEOMETRY ')]
        if len(geometry)!=1 or geometry[0]['coverage_disabled_nodes']!=0:raise ValueError('geometry coverage gate drift')
        totals={k:sum(int(row[k]) for row in rows) for k in rows[0] if k!='qid'}
        summary[mode]={'query_count':len(rows),'work_totals':totals,'diagnostic_timing_ms':{k:float(v) for k,v in t[0].items() if k!='sample'},
                       'result_sha256':sha(root/mode/'out.bin'),'output_matches_two_independent_oracles':True,
                       'geometry':geometry[0]}
        shutil.copy2(root/mode/'out.work.csv',out/(mode+'_raw_work.csv'))
        shutil.copy2(root/('timing_'+mode)/'out.csv',out/(mode+'_raw_timing.csv'))
        for i,(row,paired_memo) in enumerate(zip(rows,memo)):
            trace=timeline[i*5:(i+1)*5];qid=int(row['qid'])
            leaf=int(row['leaf_calls'])
            if leaf!=trace[-1]['visited']*10:raise ValueError('leaf ownership/count bridge')
            joint.append(dict(mode=mode,query_id=qid,pivot_distance_calls=int(row['pivot_calls']),
                unique_pivot_rows=int(paired_memo['cache_insertions']),leaf_distance_calls=leaf,
                unique_distance_rows=int(paired_memo['full_computations']),
                repeat_pivot_to_pivot=int(paired_memo['pivot_hits']),repeat_pivot_to_leaf=int(paired_memo['leaf_hits']),
                repeat_leaf_to_leaf=0,full_distance_completions=int(row['full_computations']),
                coordinate_updates=int(row['coordinate_updates']),visited_internal_nodes=sum(x['visited'] for x in trace[:-1]),
                bound_tests=int(row['bound_tests']),visited_leaf_regions=leaf//10,verified_live_instances=leaf,
                cache_hits=int(row['pivot_hits'])+int(row['leaf_hits']),cache_insertions=int(row['cache_insertions']),
                cache_evictions=0,first_k_witness_step=next((x['level'] for x in trace if x['upper'] is not None),None),
                threshold_update_count=sum(x['upper']!=trace[j-1]['upper'] for j,x in enumerate(trace) if j),
                output_count=shape[3],correctness_pass=True))
            for x in trace:
                thresholds.append(dict(mode=mode,query_id=qid,boundary_id=x['level'],U_current=x['upper'],
                    visited_nodes=x['visited'],visit_digest=x['digest'],
                    retained_cross_layer_witnesses=sum(p[1] is not None for p in x['candidates']),
                    retained_witness_ids=json.dumps([p[0] for p in x['candidates'] if p[1] is not None])))
    write_csv(out/'query_work.csv',joint);write_csv(out/'threshold_trace.csv',thresholds)
    base=summary['G0']['work_totals']
    for mode,data in summary.items():
        w=data['work_totals'];data['coordinate_update_reduction_vs_G0']=1-w['coordinate_updates']/base['coordinate_updates']
        data['leaf_call_reduction_vs_G0']=1-w['leaf_calls']/base['leaf_calls']
        data['diagnostic_time_ratio_vs_G0']=data['diagnostic_timing_ms']['total_ms']/summary['G0']['diagnostic_timing_ms']['total_ms']
    save(out/'SUMMARY.json',dict(stage='E1 diagnostic-only; no E2/E3 promotion',shape=shape,results=summary,
        exclusive_campaign_valid=True,guard_raw_sha256=sha(root/'guard/receipt.json'),
        identity=json.loads((root/'campaign_identity.json').read_text()),
        same_semantics_trace_pairs=validation['same_semantics_trace_pairs'],counterfactual_G0_U_restores_G0_visits=validation['replay_checked'],
        exact_visit_bitsets_checked=validation.get('exact_visit_bitsets_checked',False),
        CPU_GPU_oracle_bitwise_equal=True,formal_processes_used=0,
        timing_scope='Resident-query-ID H2D to full K IDs/FP64 scores Host-ready; allocations, clearing, sorting, synchronizations included; one reverse-order process per mode',
        missing_gates=['full E2 small/tree/tie/capacity/invalidation/stress matrix','strict sanitizer API gate','formal paired confidence','full Host-query-vector submission scope'],
        missing_diagnostic_fields=['per-boundary CUDA-event timestamps','full G0 witness-ID trace','hardware DRAM traffic'],
        note='Unique/repeat counts in non-memo modes are derived from their bitwise same-trajectory memo partners, not additional GPU counters. Visit digest is supplementary, non-cryptographic. No timing CI or winner claim.'))
    save(out/'RAW_MANIFEST.json',{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})
    shutil.copy2(root/'oracle.bin',out/'oracle_result.bin')
    print(json.dumps({m:{'coordinate_saved':v['coordinate_update_reduction_vs_G0'],'leaf_saved':v['leaf_call_reduction_vs_G0'],'diagnostic_ms':v['diagnostic_timing_ms']['total_ms']} for m,v in summary.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('cpu_reference',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();curate(a.root,a.cpu_reference,a.out)
