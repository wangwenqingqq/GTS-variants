"""CPU-only scalar/source consistency gate; not private full-payload validation."""
import csv,hashlib,json,math
from collections import Counter
from pathlib import Path
import numpy as np
from analyze import summary,classify
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(p):return json.loads((HERE/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
    with (HERE/p).open() as f:return list(csv.DictReader(f))
def same(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    return a==b
def main():
    identity=read('evidence/INPUT_IDENTITY.json');contract=read('CONTRACT.json')
    assert sha(HERE/'CONTRACT.json')==identity['contract_sha256']
    for p,h in identity['measurement_sources'].items():assert sha(ROOT/p)==h,p
    assert sha(HERE/'curate.py')==identity['curator_sha256']
    changed={p for p,h in identity['compiled_sources'].items() if h!=identity['measurement_sources'][p]}
    assert {Path(p).name for p in changed}=={'prepare.py','campaign.py','test_gate3.py'}
    a=read('timing/TRACE_A.json');assert a['stage']=='A' and a['decision']=='UNCLASSIFIED'
    pairs=a['paired_processes'];assert len(pairs)==6
    # Transcendental last bits differ across NumPy/platforms; gates use frozen values.
    for k,v in a['metrics'].items():assert same(summary([{m:p[m][k] for m in ('D0','D1')} for p in pairs]),v),k
    m=a['metrics'];assert classify(m['trace_ms']['ratio'],m['range_ms']['ratio'],m['insert_ms']['ratio'],m['delete_ms']['ratio'],m['trace_ms']['paired_CI95'][1],m['trace_ms']['wins'])=='UNCLASSIFIED'
    b=read('timing/TRACE_B.json');assert b['status']=='NOT_EXECUTED' and b['measurement'] is None and b['pairs']==0
    closure=read('evidence/EXECUTION_CLOSURE.json');assert closure['stage_counts']=={'qualification':10,'A':12} and closure['successful_processes']==22
    assert closure['total_top_level_starts']==23 and closure['budget_cap']==30 and len(closure['unexecuted_conditional_jobs'])==7
    assert not closure['full_dynamic_admission'] and not closure['thesis_admission'] and closure['all_isolation_receipts_valid']
    failure=read('evidence/FAILED_ATTEMPT.json');assert failure['phase']=='before CUDA initialization' and failure['no_payload_created']
    assert read('evidence/POSTPROCESSING_CLOSURE.json')['GPU_samples_repeated']==0
    rows=read('operations/OP_BREAKDOWN.json')['processes'];assert len(rows)==12
    for row in rows:
        label=row['label'];round_no=int(label.split('_')[0][1:]);mode=label.split('_')[1];p=pairs[round_no-1][mode]
        ops=csvrows(f'operations/raw/A/{label}.ops.csv');assert len(ops)==336 and Counter(r['flag'] for r in ops)==Counter({'0':40,'1':40,'2':128,'3':128})
        assert [int(r['step']) for r in ops]==list(range(336)) and all(float(r['rebuild_ms'])==0 for r in ops)
        totals={str(i):sum(float(r['ack_ms']) for r in ops if r['flag']==str(i)) for i in range(4)}
        for flag,key in zip(('0','1','2','3'),('insert_ms','delete_ms','range_ms','knn_ms')):assert math.isclose(totals[flag],row[flag],abs_tol=1e-9) and math.isclose(totals[flag],p[key],abs_tol=1e-9)
        assert math.isclose(row['trace_ms'],row['events_ms']+row['release_ms'],abs_tol=1e-9) and math.isclose(row['trace_ms'],p['trace_ms'],abs_tol=1e-9)
        assert row['unattributed_event_bookkeeping_ms']>=0
        assert len(csvrows(f'operations/raw/A/{label}.ownership.csv'))==80
        assert len(csvrows(f'operations/raw/A/{label}.queries.csv'))==256
    processes=read('evidence/QUALITY_PROCESSES.json');assert len(processes)==22 and all(p['passed'] for p in processes)
    parts=[p[k] for p in processes for k in ('measured','warmup')]
    assert sum(v['queries'] for v in parts)==4400 and sum(v['updates'] for v in parts)==2002
    assert sum(v['final_proof']['all_vector_bytes_bitwise_compared'] for v in parts)==107524753920
    for p in parts:assert p['passed'] and p['complete_members'] and all(p[k]==0 for k in ('false_negatives','false_positives','ownership_errors','final_state_errors'))
    assert sum(p.get('sanitizer_summary_zero',False) for p in processes)==6
    receipts=read('evidence/QUALITY_RECEIPTS.json');assert len(receipts)==22
    raw=read('evidence/RAW_IDENTITY.json')['files']
    for r in receipts:
        assert raw[f"{r['stage']}/{r['label']}.checked.json"]['sha256']==r['checked_sha256']
        for p,h in r['outputs'].items():assert raw[f"{r['stage']}/outputs/{p}"]['sha256']==h
        for p,h in r['guards'].items():assert raw[f"{r['stage']}/guards/{r['label']}/{p}"]['sha256']==h
    for stage,counts in [('A',Counter({0:40,1:40,2:128,3:128})),('B',Counter({0:400,1:400,2:100,3:100}))]:
        lines=(HERE/f'inputs/{stage}.logical').read_text().splitlines();assert [int(v) for v in lines[0].split()]==[sum(counts.values()),1000000,960]
        assert Counter(int(line.split()[0]) for line in lines[1:])==counts
        for suffix in ('.logical','.source.json','.cpu_state.json'):assert sha(HERE/f'inputs/{stage}{suffix}')==identity['input_hashes'][f'inputs/{stage}{suffix}']
    static=read('evidence/STATIC.json');assert static['passed'] and static['no_GPU_starts'] and static['D0_selected_identical_to_strengthened'] and static['D1_selected_identical_to_Gate2']
    resources=read('evidence/KERNEL_RESOURCES.json')['modes'];assert len(resources['D0'])==1 and len(resources['D1'])==5
    permanent=read('memory/PERSISTENT_MEMORY.json');assert permanent['D0_D1_identical'] and not permanent['D1_extra_ND_representation']
    mem=read('memory/TEMP_MEMORY.json')['records'];assert len(mem)==12
    for row in mem:assert row['GPU_owned_query_bytes']==(25006891 if row['label'].endswith('D0') else 57038379)
    probes=read('updates/STAGE_ROBUSTNESS.json');assert probes['B']['status']=='NOT_EXECUTED' and len(probes['A']['rows'])==128
    assert [s['step'] for s in probes['A']['snapshots']]==[-1,132,300,336] and all(s['queries']==32 for s in probes['A']['snapshots'])
    if (HERE/'figures/trace_latency.csv').exists():
        fig=csvrows('figures/trace_latency.csv');assert len(fig)==12
        for r in fig:assert float(r['service_ms'])==pairs[int(r['pair'])-1][r['mode']]['trace_ms']
        for r in csvrows('figures/range_ratio.csv'):assert math.isclose(float(r['ratio']),pairs[int(r['pair'])-1]['D1']['range_ms']/pairs[int(r['pair'])-1]['D0']['range_ms'],abs_tol=1e-15)
        assert len(csvrows('figures/operation_breakdown.csv'))==72 and len(csvrows('figures/stage_robustness.csv'))==12
    for name in ('README.md','DECISION.md','CLAIM_EVIDENCE.md','timing/TRACE_A.md'):
        text=(HERE/name).read_text();assert 'UNCLASSIFIED' in text
        assert '0.855934141' in text
    print('PASS: immutable sources, all six-pair estimators, gray stop/B omission, raw receipts, full scope counts and plot scalar consistency; CPU only')
if __name__=='__main__':main()
