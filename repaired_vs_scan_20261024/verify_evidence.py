"""CPU-only independent receipt, schedule, median and paired-CI verification."""
import csv,gzip,hashlib,json,math,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
    p=HERE/'evidence/measured_20261025'
    result=json.loads((HERE/'RESULTS.json').read_text())
    assert result==json.loads((p/'RESULTS_COMPLETE.json').read_text())
    blob=gzip.decompress((p/'PROCESS_EVIDENCE.json.gz').read_bytes())
    checks=json.loads((p/'COLLECTION_CHECKS.json').read_text())
    assert hashlib.sha256(blob).hexdigest()==checks['process_evidence_uncompressed_sha256']
    bundle=json.loads(blob);samples=list(csv.DictReader((p/'raw_samples.csv').open()))
    complete=json.loads((p/'TIMING_COMPLETE.json').read_text());schedule=json.loads((p/'TIMING_SCHEDULE.json').read_text())
    assert len(samples)==1080 and len(bundle)==530 and len(schedule)==18
    assert sum(c['quality_eligible'] for c in result['cases'])==17
    by={}
    for row in samples:
        key=(row['dataset'],int(row['target_index']),int(row['Q']),row['arm'],int(row['round']))
        by.setdefault(key,[]).append(row)
    assert len(by)==360
    for label,entry in bundle.items():
        r=entry['receipt.json'];assert r['gpu_uuid']==complete['gpu_uuid']
        assert entry['before.json']['idle'] and entry['after.json']['idle']
        assert not any(t['foreign'] for t in entry['checks.json'])
        # Live after-initial processes may only be a known task PID; stable final
        # snapshots have no apps. No missing/unobserved intervals are invented.
        known={int(pid) for t in entry['checks.json'] for pid in t['known_owned_pids']}
        known.add(r['pid'])
        for row in csv.reader(entry['after_initial.json']['apps'].splitlines()):
            if row:assert int(row[0]) in known
        if label.startswith('time_'):
            assert r['valid'] and r['exit_code']==0 and r['reps']==3 and r['warmups']==3
            assert not r['dump'] and not r['instrumented'] and not r['tool']
            assert entry['result.json']['correct']
        if r['tool']:
            assert r['valid'] and r['exit_code']==0
            assert 'ERROR SUMMARY: 0 errors' in entry['stdout.log']+entry['stderr.log']
    for c,sc in zip(result['cases'],schedule):
        assert (c['dataset'],c['Q'],c['target'])==(sc['kind'],sc['Q'],[10,100,1000][sc['k']])
        med={}
        for arm,a in c['arms'].items():
            if arm not in sc['timed_arms']:
                assert a['status']=='correctness_failed' and not a['process_medians_ms']
                continue
            med[arm]=[]
            for g,order in enumerate(sc['orders']):
                rows=by[(c['dataset'],sc['k'],c['Q'],arm,g)]
                assert sorted(int(r['iteration']) for r in rows)==[0,1,2]
                assert all(r['order']==order for r in rows)
                v=statistics.median(float(r['batch_ms']) for r in rows)
                med[arm].append(v)
                label=f"time_g{g}_{c['dataset']}_k{sc['k']}_q{c['Q']}_{arm}"
                r=bundle[label]['receipt.json'];assert (r['kind'],r['k'],r['Q'],r['arm'])==(c['dataset'],sc['k'],c['Q'],arm)
                original='iteration,batch_ms\n'+''.join(f"{t['iteration']},{float(t['batch_ms']):.12g}\n" for t in sorted(rows,key=lambda t:int(t['iteration'])))
                assert hashlib.sha256(original.encode()).hexdigest()==r['result_files']['result.csv']
                assert r['binary_sha256']==complete['binary_hashes'][Path(r['command'][0]).name]
            assert med[arm]==a['process_medians_ms']
            assert statistics.median(med[arm])==a['median_process_median_ms']
        for name,ratio in c['ratios'].items():
            other=name[-1];v=[math.log(x/y) for x,y in zip(med['R'],med[other])]
            center=sum(v)/6;half=2.5705818366*statistics.stdev(v)/math.sqrt(6)
            for got,want in zip([ratio['paired_geomean'],*ratio['CI95']],[math.exp(center),math.exp(center-half),math.exp(center+half)]):
                assert math.isclose(got,want,rel_tol=1e-12)
            assert sum(order.index('R')<order.index(other) for order in sc['orders'])==3
        assert c['native_ordered_output_sha256']['A']==c['native_ordered_output_sha256']['R']
        for k in ['node_distance_calls','leaf_distance_calls','dp_cells','coordinates','candidate_leaves','active_leaf_threads']:
            assert c['work_counts']['A'][k]==c['work_counts']['R'][k]
    audit=json.loads((p/'FULL_OUTPUT_CPU_AUDIT.json').read_text())
    assert len(audit)==63 and sum(v['status']=='pass' for v in audit.values())==60
    for label,v in audit.items():
        assert v['native_output_sha256']==bundle[label]['receipt.json']['result_files']['result.native.bin']
        if v['status']!='pass':
            assert v['mismatches']==[{'query_index':585,'query_id':427451,'extra':[417457],'missing':[],'distance_mismatch_ids':[]}]
    assert len(json.loads((p/'SANITIZERS.json').read_text()))==42
    assert len(json.loads((p/'WORK_COUNTS.json').read_text()))==63
    manifest=json.loads((p/'FROZEN_INPUTS_END.json').read_text())
    frozen=json.loads((HERE/'evidence/CPU_ORACLE.json').read_text())
    for name,h in manifest.items():
        expected=frozen['calibration_sha256'] if name=='fixtures/calibration.json' else frozen['files'][name]['sha256']
        assert h==expected
    assert hashlib.sha256((HERE/'CONTRACT.md').read_bytes()).hexdigest()==frozen['files']['CONTRACT.md']['sha256']
    print('PASS real evidence: one GPU, 18 accounted / 17 valid workloads, 360 processes, 1080 samples, paired CIs, 42 sanitizer runs, 63 counters, frozen hashes')
if __name__=='__main__':main()
