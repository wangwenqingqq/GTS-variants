"""Revalidate every registered process and publish only scoped scalars/identities."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import collections
import json
from pathlib import Path
import numpy as np
from common import HERE, REPO, MODES, sha, load, save, expected_jobs, batches
from campaign import prepared, STAGES
from quality import check, table
from analyze import run as analyze
from traffic import query, maintenance
from audit_stage import stage_census


def main():
    p = argparse.ArgumentParser(); p.add_argument('--work', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); w = a.work.resolve(); out = a.out.resolve(); assert not out.exists()
    reg, ready = prepared(w); c = load(HERE/'CONTRACT.json'); cpu = load(w/'CPU_READY.json')
    frozen = load(w/'ANALYSIS_FREEZE.json'); assert frozen['before_primary'] and frozen['analyzer_sha256'] == sha(HERE/'analyze.py') and frozen['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert sha(reg['data']) == c['data_sha256']
    for n, r in cpu['files'].items(): assert sha(w/n) == r['sha256']
    for n, h in reg['reference_hashes'].items(): assert sha(Path(reg['reference'])/n) == h
    static = load(w/'STATIC.json'); assert static['passed']; receipts = []; checks = []; ledger_expected = []; census = {}
    for stage in STAGES:
        registered = load(w/stage/'REGISTERED.json'); results = load(w/stage/'RESULTS.json'); jobs = expected_jobs(stage)
        assert registered['jobs'] == jobs and registered['contract_sha256'] == sha(HERE/'CONTRACT.json')
        assert registered['executor_sha256'] == sha(HERE/'campaign.py') and results['complete'] and len(results['rows']) == len(jobs)
        census[stage] = stage_census(w, stage, jobs, results['rows'], reg)
        for row, job in zip(results['rows'], jobs):
            assert all(row[k] == v for k, v in job.items()) and row['status'] == 'passed'
            label = job['label']; g = w/stage/'guards'/label; receipt = load(g/'receipt.json')
            assert receipt['runtime_valid'] and receipt['exit_code'] == 0 and receipt['stop_reason'] is None
            assert receipt['observer'] == 'two-sided-starttime-v1' and receipt['gpu'] == reg['gpu']
            command = load(w/stage/(label+'.command.json'))['command']
            assert load(g/'command.json') == receipt['command'] == ['numactl', f"--cpunodebind={reg['numa']}", f"--membind={reg['numa']}", *command]
            assert receipt['binary_sha256'] == sha(command[0])
            assert sha(g/'receipt.json') == row['guard_sha256']
            for n, h in row['guard_files'].items(): assert sha(g/n) == h
            for n, r in row['reports'].items(): assert sha(w/stage/'reports'/n) == r['sha256'] and (w/stage/'reports'/n).stat().st_size == r['bytes']
            for name in ('before', 'after'): assert not load(g/(name+'.json'))['apps']
            assert all(not item['foreign'] for item in load(g/'checks.json'))
            original = load(w/stage/(label+'.checked.json')); assert sha(w/stage/(label+'.checked.json')) == row['checked_sha256']
            if job.get('kind') == 'selftest':
                assert original['passed'] and original['iterations'] == 100 and original['stream_slots'] == 2 and original['query_checks'] == 400
            else:
                current = check(w/stage/'outputs'/label, job, w, reg); assert current == original, ('quality drift', stage, label)
            if job.get('tool') in ('memcheck', 'racecheck', 'synccheck'):
                text = (g/'stdout.log').read_text()+(g/'stderr.log').read_text()
                assert ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text) and original['sanitizer_summary_zero']
            include = ('passed', 'N', 'workload', 'mode', 'diagnostic', 'complete_queries_including_warmup', 'formal_queries', 'false_negatives', 'false_positives',
                'exact_native_squared_bits', 'internal_FP64_bit_checks', 'internal_FP64_bit_mismatches', 'max_native_distance_scaled_error',
                'actual_mutation_witnesses', 'independent_final_maps', 'final_device_vector_bytes_compared', 'mean_check',
                'iterations', 'stream_slots', 'query_checks', 'empty_answers', 'full_hit_FP64_bit_checks', 'pointer_churn_epochs', 'max_batch', 'sanitizer_summary_zero')
            checks.append(dict(stage=stage, label=label, **{k: original[k] for k in include if k in original}))
            receipts.append(dict(stage=stage, label=label, checked_sha256=row['checked_sha256'], guard_sha256=row['guard_sha256'],
                guard_files=row['guard_files'], reports=row['reports'], raw_outputs=original.get('raw_outputs', {})))
            ledger_expected.append((stage, label, sha(w/stage/(label+'.command.json'))))
    starts = [json.loads(s) for s in (w/'STARTS.jsonl').read_text().splitlines()]
    assert len(starts) == c['max_GPU_starts'] == 117 and [r['start'] for r in starts] == list(range(1, 118))
    assert [(r['stage'], r['label'], r['command_sha256']) for r in starts] == ledger_expected
    out.mkdir(); (out/'evidence').mkdir(); (out/'results').mkdir()
    timing = analyze(w); save(out/'results/TIMING.json', timing)
    processes = []
    for row in load(w/'primary/RESULTS.json')['rows']:
        checked = load(w/'primary'/(row['label']+'.checked.json'))
        operations = table(str(w/'primary/outputs'/row['label'])+'.ops.csv'); summaries = {}
        for kind, name in ((0, 'delete'), (1, 'insert'), (2, 'query')):
            selected = [r for r in operations if int(r['kind']) == kind]
            ack = [float(r['ack_ms']) for r in selected]
            summaries[name] = dict(ACKs=len(selected), rows=sum(int(r['rows']) for r in selected),
                ACK_total_ms=sum(ack), ACK_quantiles_ms=dict(zip(('p50', 'p95', 'p99'), np.quantile(ack, [.5, .95, .99]).tolist())),
                statistics_submit_total_ms=sum(float(r['stats_submit_ms']) for r in selected),
                statistics_tail_inclusive_total_ms=sum(float(r['stats_tail_inclusive_ms']) for r in selected))
        processes.append(dict(job={k: row[k] for k in ('label', 'mode', 'workload', 'round', 'order')},
            queries=checked['all_target_query_records'], stages=checked['query_stage_records'], metadata=checked['metadata'],
            operation_totals_ms=checked['operation_totals_ms'], operation_summaries=summaries))
    save(out/'evidence/PRIMARY_PROCESSES.json', processes)
    traffic = {}
    for job in expected_jobs('query_ncu'):
        label = job['label']; checked = load(w/'query_ncu'/(label+'.checked.json'))
        cell = query(w/'query_ncu/reports'/(label+'.csv'), checked, c['NCU_metrics'])
        save(out/'evidence'/('NCU_'+label+'.json'), cell)
        traffic[label] = {k: v for k, v in cell.items() if k not in ('raw', 'queries')}
    save(out/'results/TRAFFIC.json', dict(scope='All query kernels,one independent NCU process/cell;no DMA or process CI', cells=traffic))
    job = expected_jobs('maintenance_ncu')[0]; label = job['label']; checked = load(w/'maintenance_ncu'/(label+'.checked.json'))
    stat = maintenance(w/'maintenance_ncu/reports'/(label+'.csv'), checked, c['NCU_metrics'], len(batches(2, 1000000)))
    save(out/'evidence/MAINTENANCE_NCU.json', stat)
    save(out/'results/MAINTENANCE.json', dict(profile={k: v for k, v in stat.items() if k != 'raw'},
        paired_tax={workload: r['incremental_update_tax'] for workload, r in timing['workloads'].items()},
        standalone_maintenance_ms=0, note='Incremental statistics fully charged within updates;profile kernel durations are diagnostic and not a service denominator'))
    save(out/'evidence/QUALITY.json', dict(passed=True, records=checks, sanitizer_scope='N65/N513 synthetic100iterations/two independent streams;not fullN',
        target_scope='all measured and warmup answers,all actual transition witnesses,complete final maps and every final device-vector byte',
        not_claimed=['concurrent overlap', 'CUDA Graph', 'growth beyond1M', '10k queries/process', 'production sustained', 'new mechanism']))
    save(out/'evidence/QUALITY_RECEIPTS.json', receipts); save(out/'evidence/STATIC.json', static)
    save(out/'evidence/STAGE_CENSUS.json', census)
    save(out/'evidence/INPUTS.json', dict(records=cpu['records'], files=cpu['files'],
        data_sha256=c['data_sha256'], initial_mean_sha256=c['global_means_sha256'], qids=c['qids'], radius=c['radius'],
        true_vs_anchor='initial FP32 anchor has measured small bias from trueFP64 mean;exact search is unaffected;true drift diagnostic never feeds live queries'))
    save(out/'evidence/INPUT_IDENTITY.json', dict(contract_sha256=sha(HERE/'CONTRACT.json'), parent_commit=c['parent_commit'],
        executed_sources=reg['sources'], generated_sources=reg['generated_sources'], binaries=ready['binaries'], libraries=ready['libraries'],
        registration_sha256=sha(w/'REGISTERED.json'), ready_sha256=sha(w/'READY.json'), cpu_ready_sha256=sha(w/'CPU_READY.json'),
        analysis_freeze=frozen, postprocessing_sources={n: sha(HERE/n) for n in ('curate.py', 'traffic.py', 'audit_stage.py')},
        original_reference_hashes=reg['reference_hashes'], replay_binary_sha256=ready['replay_binary_sha256'],
        placement='one initially idle same-model card,matched NUMA;private placement;no setting changes'))
    save(out/'evidence/EXECUTION.json', dict(complete=True, GPU_starts=117, max_GPU_starts=117, failed_or_replaced_samples=0,
        stage_counts=dict(collections.Counter(r['stage'] for r in starts)), all_two_sided_isolation_valid=True,
        start_ledger_sha256=sha(w/'STARTS.jsonl'), stage_result_hashes={s: sha(w/s/'RESULTS.json') for s in STAGES}))
    raw = {str(p.relative_to(w)): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in w.rglob('*') if p.is_file() and p.name != 'campaign.lock'}
    save(out/'evidence/RAW_MANIFEST.json', dict(scope='private raw payloads,inputs,CPU references,guards and profiler captures;identities only', files=raw))
    print('CURATED117/117;all sources,raw answers,fields,ownership,means and timings revalidated', flush=True)


if __name__ == '__main__': main()
