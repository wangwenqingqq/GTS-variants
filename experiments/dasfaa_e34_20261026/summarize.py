"""Summarize one intact epoch; never pool restarts or failed correctness gates."""
import csv,json,math,statistics,sys
from pathlib import Path

def process_value(path,q):
    with Path(str(path)+'.csv').open() as f:rows=[r for r in csv.DictReader(f) if int(r['iteration'])>=0 and int(r['batch'])==q]
    assert rows;return statistics.mean(float(r['batch_ms']) for r in rows)
def paired(p,s):
    assert len(p)==len(s)==6
    logs=[math.log(a/b) for a,b in zip(p,s)];m=statistics.mean(logs);h=2.570581835636314*statistics.stdev(logs)/math.sqrt(6)
    return {'ratio':math.exp(m),'lo':math.exp(m-h),'hi':math.exp(m+h),'P_wins':sum(a<b for a,b in zip(p,s)),'PS_order_ratio':math.exp(statistics.mean(logs[::2])),'SP_order_ratio':math.exp(statistics.mean(logs[1::2])),'marginal_median_ratio':statistics.median(p)/statistics.median(s)}
def slope(ns,ys):
    if len(ns)<2:return None
    x=[math.log(v) for v in ns];y=[math.log(v) for v in ys];mx=statistics.mean(x);my=statistics.mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/sum((a-mx)**2 for a in x)
def main(root,epoch,out):
    root,epoch,out=map(Path,(root,epoch,out))
    if not (epoch/'corrected_build_identity.json').exists():
        raise ValueError('Refuse historical/unidentified epoch; approved corrected sources required')
    invalid=any((epoch/name).exists() for name in ('INVALID_EPOCH.json','FAILED.json'))
    cases=json.loads((root/'DATA_MANIFEST.json').read_text())['cases'];rows=[]
    for c in cases:
        for q in (1,32,1024):
            key=f'{c["family"]}_{c["N"]}_q{q}'
            row={'family':c['family'],'N':c['N'],'Q':q,'synthetic':c['synthetic']}
            for arm in 'PS':
                quality=epoch/f'quality_{key}_{arm}.json'
                a=json.loads(quality.read_text()) if quality.exists() else {'state':'not-completed','correct':False}
                row[arm+'_quality']=a
                paths=[epoch/f'time_r{r}_{key}_{arm}'/'result' for r in range(6)]
                if invalid or not a['correct']:continue
                if all(Path(str(p)+'.csv').exists() and p.with_name('receipt.json').exists() and json.loads(p.with_name('receipt.json').read_text())['valid'] for p in paths):
                    values=[process_value(p,q) for p in paths]
                    row[arm+'_process_ms']=values
                    row[arm+'_ms']=math.exp(statistics.mean(map(math.log,values)))
                    row[arm+'_p10_median_p90_ms']=[statistics.quantiles(values,n=10,method='inclusive')[0],statistics.median(values),statistics.quantiles(values,n=10,method='inclusive')[8]]
            if all(a+'_process_ms' in row for a in 'PS'):
                row['comparison']=paired(row['P_process_ms'],row['S_process_ms'])
            cr=row.get('comparison')
            row['crossover']=bool(cr and cr['ratio']<1 and cr['hi']<1 and row['S_quality']['correct'] and row['P_quality'].get('tie_aware_recall',0)>=.999)
            rows.append(row)
    slopes=[]
    for family,synth in [('tloc',False),('tloc',True),('deep',False)]:
        for q in (1,32,1024):
            for arm in 'PS':
                keep=[r for r in rows if (r['family'],r['synthetic'],r['Q'])==(family,synth,q) and arm+'_ms' in r]
                slopes.append({'family':family,'synthetic':synth,'Q':q,'arm':arm,'Ns':[r['N'] for r in keep],'slope':slope([r['N'] for r in keep],[r[arm+'_ms'] for r in keep])})
    required=[r for r in rows if r['N']<=10000000]
    complete=all('comparison' in r for r in required) and all('S_ms' in r for r in rows)
    decision='A (measured qualifying loads only)' if any(r['crossover'] for r in rows) else 'B' if complete and not invalid else 'unknown: incomplete/correctness/isolation-failed matrix'
    nstars=[{'family':f,'synthetic':s,'Q':q,'N_star':min(r['N'] for r in rows if (r['family'],r['synthetic'],r['Q'])==(f,s,q) and r['crossover'])} for f,s in [('tloc',False),('tloc',True),('deep',False)] for q in (1,32,1024) if any((r['family'],r['synthetic'],r['Q'])==(f,s,q) and r['crossover'] for r in rows)]
    out.mkdir(exist_ok=True,parents=True)
    (out/'RESULTS.json').write_text(json.dumps({'epoch':epoch.name,'complete_epoch':(epoch/'COMPLETE.json').exists(),'timing_ineligible':invalid,'decision':decision,'N_stars':nstars,'rows':rows,'slopes':slopes},indent=2)+'\n')
    md=['# E4 intermediate report','',f'**Decision: {decision}.** Missing comparisons are not evidence of no crossover.','',f'Epoch: `{epoch.name}`. Old incident epochs are excluded; failed epochs contribute no timing.','',
        'Unit: host-ready batch milliseconds, six fresh processes per arm; k=8. P uses the approved archived-header correctness patch plus WORK-only macros (disabled for timing). S is native FAISS Flat64 plus timed CPU FP64 candidate refinement. Neither column is called universally exact. Q1024 repeats24 of1000 held-out queries.',
        '', '| Family | N | Q | P ms/state | S ms/state | P/S [95% CI] | P recall | S recall |', '|---|---:|---:|---|---|---|---|---|']
    for r in rows:
        def fmt(a):
            return format(r[a+'_ms'],'.6g') if a+'_ms' in r else r[a+'_quality'].get('state','correctness-passed; timing pending' if r[a+'_quality']['correct'] else 'correctness-failed')
        def recall(a):
            v=r[a+'_quality'].get('tie_aware_recall');return f'{v:.8f}' if v is not None else '—'
        cr=r.get('comparison');ratio=f'{cr["ratio"]:.5g} [{cr["lo"]:.5g}, {cr["hi"]:.5g}]' if cr else 'unavailable'
        md.append(f'| {r["family"]}{" (synthetic)" if r["synthetic"] else " (real)"} | {r["N"]} | {r["Q"]} | {fmt("P")} | {fmt("S")} | {ratio} | {recall("P")} | {recall("S")} |')
    md+=['','## Measured log latency / log N slopes','','| Family | Source | Q | Arm | N values | Slope |','|---|---|---:|---|---|---:|']
    for r in slopes:md.append(f'| {r["family"]} | {"synthetic" if r["synthetic"] else "real"} | {r["Q"]} | {r["arm"]} | {r["Ns"]} | {r["slope"] if r["slope"] is not None else "unavailable"} |')
    md+=['','## Boundaries and unfinished scope','',
        '- P/G N>10M is policy-infeasible (mandated workspace/tree_h=8 label), not run. The incident measured height8 at30M;20M Deep height is not measured. S retains larger N. Coordinate bounds alone do not establish runtime feasibility.',
        '- T-loc1/3/10M are real archived prefixes;30/100M are frozen fitted synthetic mixtures. Slopes never pool the two distributions.',
        '- Deep original queries failed exact-value isolation (16/63/201/379 matching base rows at1/3/10/20M); no substituted query set is presumed authorized.',
        '- G is compile-only/incomplete: native half-free-memory arena can overflow its signed-int slot count on a near-idle96GiB GPU. No G latency/recall is inferred.',
        '- Word61K/150K/300K, literal611K infeasibility, optional Protein/ChEMBL gradients, and E3 nine-dataset matrix remain separately tracked. C2/P-approx are not run.',
        '- Counters are separate instrumented processes; logical scan bytes are not measured DRAM bytes. Missing counters/sanitizer/final audit remain missing, not waived.',
        '- No extrapolated crossover replaces a missing or infeasible point. No priority/novelty claim follows from crossover alone.',
        '', 'Provenance: CONTRACT.md, append-only AMENDMENTS.md, DATA_MANIFEST.json, corrected build identity, input verification and retained raw run receipts.']
    (out/'E4_INTERIM.md').write_text('\n'.join(md)+'\n')
if __name__=='__main__':main(*sys.argv[1:])
