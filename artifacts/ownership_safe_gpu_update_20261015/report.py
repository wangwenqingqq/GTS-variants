"""Generate bounded research conclusions from verified scalars;never edit raw evidence."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from common import HERE,load
from analyze import compare,distribution

def ratio(r):return f"{r['median_ratio']:.4f};paired95%[{r['paired_95_CI'][0]:.4f},{r['paired_95_CI'][1]:.4f}]"
def median(d):return d['median']
def write(name,text):
    with (HERE/name).open('x') as f:f.write(text.rstrip()+'\n')

def main():
    t=load(HERE/'results/TIMING.json');e=load(HERE/'results/EXTENSIONS.json');p=load(HERE/'evidence/PRIMARY_SCALARS.json');ncu=load(HERE/'results/NCU.json')
    execution=load(HERE/'evidence/EXECUTION.json');assert execution['complete'] and execution['admitted_GPU_targets']==340
    service=t['whole_service'];micro=t['micro'];comp=t['comparisons']
    gain=comp['FINAL_over_CURRENT_service_ms'];operator=comp['FINAL_over_NATIVE_D_512']
    value='strong engineering signal' if gain['median_ratio']<=.8 and gain['paired_95_CI'][1]<1 else 'positive engineering signal' if gain['median_ratio']<=.9 and gain['paired_95_CI'][1]<1 else 'bounded effect requiring the reported uncertainty/tradeoff review'
    report=['# Ownership-safe update transformation — complete bounded study','',
        f"**Decision: {value};scientific novelty is not admitted.** FINAL's W2 events+release median is {median(service['FINAL']['service_ms']):.6f} ms versus {median(service['CURRENT']['service_ms']):.6f} ms for the unchanged same-card CURRENT Frozen-PDX control:time reduction {100*(1-gain['median_ratio']):.2f}%,speedup {1/gain['median_ratio']:.3f}x. The paired geometric ratio is {gain['paired_geometric_ratio']:.4f},95% interval [{gain['paired_95_CI'][0]:.4f},{gain['paired_95_CI'][1]:.4f}],with {gain['wins']}/6 process wins.",
        '', '## Data,scope and correctness','',
        '- GIST1M:1,000,000 x960 FP32 coordinates,3.84GB raw vectors;one SM120 RTX PRO6000 Blackwell GPU,CUDA13.1. B1 exact inclusive range queries,not ANN/kNN.',
        '- W2:500,000 replacement pairs,1,000,000 point updates,977 delete+977 insert ACKs,160 formal queries and8 excluded warmups. Build and full-state export are excluded;release is included. Incoming vectors are the inherited rotated-coordinate payload.',
        '- 341 attempts preserve one invalid foreign-activity interruption;340 admitted targets include42 qualification,6 screen,192 primary,54 synthetic shape,36 calibration and10 profiler targets. No passed target was rerun. The initial callback false alarm was corrected offline without rerunning its GPU target.',
        '- All complete query members/fields,independently replayed occurrence maps and final vectors pass. All262 new GIST processes additionally bind full allocated-capacity bytes(including retired rows) and exact per-ACK physical execution to mutation witnesses. Qualifying diagnostic runs check every changed row after ACK. Synthetic bit tests do not admit NaNs to search.',
        '- CPU proof:125,664 exhaustive sequences,576 randomized cases and15 invalid cases;C++ reverses permitted within-wave orders. Memcheck/racecheck/synccheck,high-entropy full-capacity cases and two sequential stream slots pass. Graph,simultaneous readers and production are not admitted.',
        '', '## Full same-campaign service','',
        'All numbers are medians of6 process values,not sums of independent medians. See TIMING.json for p10/p90,all process values,paired ratios and order strata.','',
        '| Variant | events+release ms | query ms | update ms | release ms | known owned bytes |',
        '|---|---:|---:|---:|---:|---:|']
    for u in ('S1','CURRENT','NATIVE','WAVES','FINAL'):
        r=service[u];report.append(f"| {u} | {median(r['service_ms']):.6f} | {median(r['query_ms']):.6f} | {median(r['update_ms_including_statistics']):.6f} | {median(r['release_ms']):.6f} | {median(r['device_owned_peak_bytes']):.0f} |")
    report+=['','| Comparison | Candidate/base service ratio;paired interval |','|---|---|']
    for target,base in (('NATIVE','CURRENT'),('WAVES','CURRENT'),('FINAL','CURRENT'),('FINAL','S1'),('FINAL','WAVES')):
        report.append(f"| {target}/{base} | {ratio(comp[f'{target}_over_{base}_service_ms'])} |")
    native=compare(service['NATIVE']['service_ms']['process_values'],service['FINAL']['service_ms']['process_values'])
    report.append(f"| FINAL/NATIVE(audited) | {ratio(native)} |")
    report+=['','S1 is the inherited Progressive internal control;CURRENT is the unchanged Frozen-PDX native-update control. This is not an external Faiss/CAGRA or original-GTS-tree comparison.','',
        '## Whole Host-return operator ACK','',
        'Each entry is the median of6 within-process means. Replacement includes both operations;its outer ACK is not added to its sub-ACKs. Finite p50/p95 and throughput are retained in TIMING.json.','',
        '| Operator | B | NATIVE ms | WAVES ms | FINAL ms | FINAL/NATIVE;paired interval |','|---|---:|---:|---:|---:|---|']
    for op in ('I','D','R'):
        for b in (1,32,512):
            values=[median(micro[f'{u}_{op}_{b}']['mean_ACK_ms']) for u in ('NATIVE','WAVES','FINAL')]
            report.append(f"| {op} | {b} | {values[0]:.6f} | {values[1]:.6f} | {values[2]:.6f} | {ratio(comp[f'FINAL_over_NATIVE_{op}_{b}'])} |")
    report+=['','## Query tails,CPU consumption and memory','',
        '| Variant | finite query p95 ms | events CPU user+system s | process max RSS KiB |','|---|---:|---:|---:|']
    for u in ('CURRENT','NATIVE','WAVES','FINAL'):
        rows=[r for r in p if r['job']['kind']=='service' and r['job']['update']==u]
        cpu=distribution([r['service_detail']['cpu_events_user_s']+r['service_detail']['cpu_events_system_s'] for r in rows])
        report.append(f"| {u} | {median(e['service_detail'][u]['operators']['Q']['p95_ACK_ms']):.6f} | {median(cpu):.6f} | {median(e['service_detail'][u]['metadata']['process_peak_RSS_KiB_including_client_inputs']):.0f} |")
    report += [f"",f"FINAL/CURRENT formal query-total ratio:{ratio(comp['FINAL_over_CURRENT_query_ms'])}. CPU consumption is not pure CPU computation or isolated waiting. Known owned allocations are not an instrumented absolute GPU peak;cudaMemGetInfo values are point observations. FINAL adds4096 device bytes. The shared Host audit ledger is present in new NATIVE/WAVES/FINAL;CURRENT directly measures the unchanged comparator.",
        '', '## What is redundant?','',
        'The immutable W2 witness inventory has977 delete batches,500,000 native moves and500,000 distinct final destination assignments,with0 RAW/WAW/WAR edges. Thus **W2 eliminates no vector-row movement**. Its causal opportunity is execution/control granularity,not a proven reduction in necessary vector payload. Counts refer to provenance assignments,not data-dependent identical-value elimination.','',
        '| Variant | delete copy APIs | kernel launches | D2D memcpy payload bytes | kernel copy payload bytes | plan H2D bytes | delete syncs |','|---|---:|---:|---:|---:|---:|---:|']
    for u in ('NATIVE','WAVES','FINAL'):
        rows=[r['physical']['D'] for r in p if r['job']['kind']=='service' and r['job']['update']==u]
        assert all(r==rows[0] for r in rows);r=rows[0]
        report.append(f"| {u} | {r['copy_APIs']} | {r['launches']} | {r['D2D_bytes']} | {r['kernel_payload_bytes']} | {r['H2D_plan_bytes']} | {r['syncs']} |")
    report+=['','WAVES retains every native row move in safe stream-ordered CUDA batch levels. FINAL composes tail provenance,proves source/destination nonaliasing,and materializes final row assignments with coalesced GPU loads/stores. At B1 it dispatches native;one final row uses memcpy. Both keep the same logical map and query layout. All planning,validation,bookkeeping,submission,destruction and wait costs are inside primary ACK.',
        '', '## Dependent synthetic shapes — narrower timing scope','',
        'The frozen ACK_ms column is actually submission+wait **before local set/BatchPlan destruction**,not the main complete Host-return ACK. N4096/B512,2 warmups+32 intervals per dimension/process,6 processes;setup/reset/readback excluded. Do not promote these ratios to GIST service or compare their absolute denominator with the main table.','',
        '| Shape | D | NATIVE interval ms | WAVES interval ms | FINAL interval ms | FINAL/NATIVE;paired interval | FINAL compiled rows |','|---|---:|---:|---:|---:|---|---:|']
    for shape in ('random','localized','chain'):
        for d in (128,960):
            cell=e['shapes'][f'{shape}_D{d}'];v=[median(cell[u]['mean_ACK_ms']) for u in ('NATIVE','WAVES','FINAL')]
            report.append(f"| {shape} | {d} | {v[0]:.6f} | {v[1]:.6f} | {v[2]:.6f} | {ratio(cell['comparisons']['FINAL_over_NATIVE'])} | {median(cell['FINAL']['compiled_rows']):.0f} |")
    report+=['','The adversarial chain reduces512 native moves/512 safe levels to1 final row assignment under strict capacity compatibility. This is structural/correctness evidence plus a narrow synthetic timing interval,not a dependency-rich mixed-query service result.','',
        '## Diagnostic attribution and limits','',
        'TIMELINES.json and the six normalized CSVs preserve all NSYS ranges,API partitions,DMA/kernel overlays,sampled GPU activity and completeness warnings. Each update is bound chronologically to the physical ledger. Profiled ACKs never replace the native table;DMA and kernel time are not added to overlapping API/sync spans.',
        '', 'NCU.json retains every exported value/unit and explicit unavailability. FINAL update-kernel counts exclude metadata copies and CPU work;no corresponding native copy-engine counter denominator exists. Therefore total update DRAM savings are **unknown**,not zero and not established by requested payload counts. Query counters cover only the actually launched nonempty progressive stages/fields;launch counts are independently bound to validated stage inputs and answer counts. Calibration ratios retain all MARKED/PLAIN matched observations with the later-phase caveat in METHODS.md.','',
        '| NCU capture | selected launches | denominator | L2 read sectors | L2 write sectors | unavailable metrics |','|---|---:|---|---:|---:|---|']
    for name,record in ncu.items():
        metric=record['per_query'] or record['per_update_ACK'];unit='query' if record['per_query'] else 'delete ACK'
        report.append(f"| {name} | {record['launches']} | per {unit} | {metric['lts__t_sectors_op_read.sum']:.2f} | {metric['lts__t_sectors_op_write.sum']:.2f} | {','.join(record['unavailable_metrics']) or 'none'} |")
    report+=['','An exported n/a is null/unknown,never zero. The predeclared uncontrolled-cache/unmodified-clock warnings remain disclosed. These are profiler observations,not native latency or a complete device-traffic denominator.',
        '', '## Five research answers and next decision','',
        '1. Native swap order fixes occurrence/row semantics,but not every intermediate vector copy. Full-capacity provenance composition removes overwritten intermediate assignments when such dependencies exist.',
        '2. Strict physical compatibility holds on all declared tests without query indirection,tombstones or weakened ACK visibility. Unsupported B>512 and invalid IDs remain rejected.',
        '3. W2 measures a control/executor change,not vector-payload elimination. The physical ledger and profiler must distinguish Host call counts,internal transfer activities,kernel payload and hardware traffic.',
        '4. B1/32/512 operator results,W2 and all synthetic regressions are retained separately. Missing concurrency,Graph,other datasets/GPUs and inclusive cold-start costs limit promotion.',
        '5. Known gather/scatter/compaction already explains much of this execution design. W2 alone cannot validate new ownership-mechanism novelty. Preserve the engineering result;before a paper claim,compare a generic GPU gather/scatter implementation and a repeated-live-occurrence GIST mixed-query trace under the same complete ACK/service contract. No such extra campaign was silently launched.']
    write('REPORT.md','\n'.join(report))
    write('README.md',f"""# Ownership-safe GPU update transformation

**Complete bounded engineering study;novelty not admitted.** GIST1M/D960(3.84GB),single-card exact range service. FINAL lowers same-campaign CURRENT Frozen-PDX W2 events+release by **{100*(1-gain['median_ratio']):.2f}%**({1/gain['median_ratio']:.3f}x);paired ratio95% interval **[{gain['paired_95_CI'][0]:.4f},{gain['paired_95_CI'][1]:.4f}]**. B512 delete mean-ACK reduction versus audited NATIVE is **{100*(1-operator['median_ratio']):.2f}%**.

The strongest caveat:W2 has **zero within-batch dependencies and zero removed row assignments**. Its gain is an executor/control improvement,not proof of a new ownership algorithm or DRAM-byte saving. Synthetic shape timing excludes plan/set destruction and is not the primary ACK denominator.

- [Full report and tables](REPORT.md),[methods](METHODS.md),[semantic proof](SEMANTICS.md),[novelty boundary](NOVELTY_BOUNDARY.md).
- [Claim/evidence map](CLAIM_EVIDENCE.md),[decision](DECISION.md),[reproduction](REPRODUCE.md),[audit](AUDIT.md).
- 341 preserved attempts,340 admitted targets;all passed samples retained,one invalid isolation attempt replaced only with explicit authorization. The original callback false alarm is retained and rechecked offline.
- [Timing scalars](results/TIMING.json),[shape/calibration detail](results/EXTENSIONS.json),[NSYS](results/TIMELINES.json),[NCU](results/NCU.json).

Run `PYTHONDONTWRITEBYTECODE=1 python3 artifacts/ownership_safe_gpu_update_20261015/verify.py` from the repository root for CPU-only source/manifest/statistical verification. No paper manuscript or raw data is included.
""")
    write('CLAIM_EVIDENCE.md',f"""# Claim-evidence map

| ID | Claim and denominator | State | Evidence | Allowed wording / boundary |
|---|---|---|---|---|
| C1 | Strict native occurrence ownership and all allocated vector bytes under bounded serial delete | measured | QUALITY.json,CPU_MODEL_R1.json,CPU_CPP_FINAL.json,SEMANTICS.md | Declared qualification and all262 new GIST targets pass;not arbitrary permutations/concurrent observers |
| C2 | W2 has977 batches,500000 moves=500000 final assignments and0 RAW/WAW/WAR | measured | CPU_NATIVE_W2_INVENTORY.json | No movement elimination is demonstrated on W2;counts are provenance,not value deduplication |
| C3 | B512 delete FINAL/NATIVE median mean-ACK ratio {operator['median_ratio']:.4f} | measured | TIMING.json,PRIMARY_SCALARS.json,physical witness proofs | Complete same-campaign Host-return ACK;all plan/audit/wait costs included;all other batches retained |
| C4 | W2 FINAL/CURRENT median events+release ratio {gain['median_ratio']:.4f} | measured | TIMING.json,192 primary receipts | Effect and paired uncertainty reported separately;not build-inclusive process wall,original GTS,Faiss or CAGRA |
| C5 | Dependency chain512 native moves to1 final assignment | partial | CPU proof,SHAPE_SCALARS.json,EXTENSIONS.json | Structural result and narrow synthetic interval;cleanup excluded,not dependency-rich GIST service |
| C6 | Internal execution/control granularity matters beyond Host API count | inferred | Physical ledger+TIMELINES.json | Interpret actual API/transfer/kernel counts;do not call API span pure CPU computation |
| C7 | Total update DRAM/L2 saving over native copy engines | unknown | NCU only selected FINAL kernels | Requested payload and kernel-only counters do not provide that total denominator |
| C8 | New general ownership algorithm / all-GPU-tree advantage | unvalidated | NOVELTY_BOUNDARY.md | Novelty not admitted;generic gather/scatter and repeated-live mixed-query comparison still needed |
| C9 | Production,Graph,concurrent readers,multi-GPU,1B vectors | unknown | no evidence | No such admission or scalability claim |

Raw custody:RAW_MANIFEST.json and private archive hashes. Source/binary/tool identities:IDENTITY.json. Rejected,invalid and earlier checkpoint records remain immutable;see STATUS_STOPPED_R1.md and AUDIT.md. All numbers are generated from the retained same-campaign scalars,not previous-campaign timings.
""")
    write('DECISION.md',f"""# Decision

- Implementation:bounded prototype passes declared exactness,strict full-capacity,sanitizer and same-card workflow gates. No production/concurrency/Graph admission.
- Engineering effect:{value};W2 median time reduction {100*(1-gain['median_ratio']):.2f}%,paired interval[{gain['paired_95_CI'][0]:.4f},{gain['paired_95_CI'][1]:.4f}]. All operator and query regressions remain in REPORT.md/TIMING.json rather than being hidden by the aggregate.
- Mechanism:strict tail-provenance composition is correct in the stated descending-last contract. Current W2 removes no row moves;ordinary coalesced indexed GPU copying explains its vector executor. Distinguish Host API counts from internal transfer granularity.
- Thesis:novelty **not admitted**. Generic gather/scatter/compaction and the weak dependency content of W2 prevent paper-level promotion from this result alone. Missing evidence is not an impossibility proof.
- Reopen condition:distinct nonincremental mechanism plus a strong generic GPU executor comparator on repeated-live dependent mixed-query traces,complete Host-return ACK and events+release,before any new paper claim. New datasets,larger batches,other architectures and inclusive cold start need their own frozen contracts.
- Retained negatives:ordinary CUDA batch API's full ratios;every B1/32/512 and shape regression;synthetic cleanup exclusion;unknown total update DRAM;one isolation failure and the original CPU callback false alarm. No raw record was overwritten or favorable-order sample selected.
""")
    print('Generated bounded report from verified process scalars')

if __name__=='__main__':main()
