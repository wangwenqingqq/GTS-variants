"""Generate the four planned tables and figures from verified scalar exports."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np

def load(p):return json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def table(p,headers,rows,caption):
    p.write_text(caption+'\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows))

def report(a):
    root=a.artifact;raw=a.analysis;t=load(raw/'BATCH_SCALING.json');w=load(raw/'EXECUTED_WORK.json');m=load(raw/'TILE_MODEL_FIT.json');identity=load(raw/'FUNCTION_IDENTITY.json')
    assert m['final_decision_valid'],'Do not publish a causal verdict after failed B1 reproduction'
    for d in ('timing','counters','geometry','traffic','models','figures'):(root/d).mkdir(exist_ok=True)
    bs=list(map(int,w));seq=lambda key:[w[str(b)][key] for b in bs]
    dump(root/'timing/BATCH_SCALING.json',t);dump(root/'counters/EXECUTED_WORK.json',w)
    dump(root/'models/TILE_MODEL_FIT.json',m);dump(root/'geometry/FUNCTION_IDENTITY.json',identity)
    dump(root/'geometry/KERNEL_GEOMETRY.json',{b:v['geometry'] for b,v in w.items()})
    traffic={b:{k:v[k] for k in ('B','kernel_ms','DRAM_bytes','DRAM_read_bytes','DRAM_write_bytes','DRAM_bytes_per_query','DRAM_GBs','L2_bytes','SM_throughput_percent','occupancy_percent')} for b,v in w.items()}
    dump(root/'traffic/DRAM_SCALING.json',traffic)
    table(root/'counters/EXECUTED_WORK.md',['B','Kernel ms','Executed FP32 proxy G','Useful proxy G','Inflation','Inflation × B'],[[b,f"{w[str(b)]['kernel_ms']:.6f}",f"{w[str(b)]['executed_FP32_proxy']/1e9:.3f}",f"{w[str(b)]['useful_ops']/1e9:.3f}",f"{w[str(b)]['inflation']:.5f}",f"{w[str(b)]['inflation_times_B']:.5f}"] for b in bs],'# Executed work\n\nOne selected native distance invocation/B; predicated-on FADD + FMUL + 2×FFMA. Not complete-output ACK timing. No counter sampling CI is claimed.')
    table(root/'traffic/DRAM_SCALING.md',['B','Read GB','Write GB','Total GB','GB/query','GB/s','SM %','Occupancy %'],[[b,*[f'{w[str(b)][k]/1e9:.6f}' for k in ('DRAM_read_bytes','DRAM_write_bytes','DRAM_bytes','DRAM_bytes_per_query')],*[f'{w[str(b)][k]:.3f}' for k in ('DRAM_GBs','SM_throughput_percent','occupancy_percent')]] for b in bs],'# Measured DRAM\n\nDecimal GB; real NCU bytes divided by the same NCU native-kernel duration. Logical dataset payload is not substituted for measured traffic.')
    table(root/'timing/BATCH_SCALING.md',['B','Invocation ms','p10 / p90 ms','ms/query','Queries/s','32-invocation pass ms','vs repeated-single'],[[b,f"{t[str(b)]['invocation_ms']['median']:.6f}",f"{t[str(b)]['invocation_ms']['p10']:.6f} / {t[str(b)]['invocation_ms']['p90']:.6f}",f"{t[str(b)]['query_ms']['median']:.6f}",f"{t[str(b)]['queries_per_second']['median']:.3f}",f"{t[str(b)]['pass_ms']['median']:.6f}",'N/A'] for b in bs],'# Complete-output throughput\n\nMedian of six fresh process means; p10/p90 across process means, not a confidence interval. Query H2D, native distance, per-row complete compaction/fields/observer/D2H and completion are charged. Setup/build are outside ACK. B64/128 use the separately registered128 pool; no GTSPP or repeated-single speedup claim.')
    table(root/'geometry/KERNEL_GEOMETRY.md',['B','Function','Grid','Block','REG / allocated','Static / dynamic / driver shared B','Stack B','Normalized hash prefix'],[[b,g['runtime_function'],str(g['grid']),str(g['block']),f"{g['registers_per_thread']:g} / {g['allocated_registers_per_thread']:g}",f"{g['shared_static_bytes']:g} / {g['shared_dynamic_bytes']:g} / {g['shared_driver_bytes']:g}",f"{g['stack_bytes']:g}",g['normalized_sha256'][:16]] for b in bs for g in [w[str(b)]['geometry']]],'# Runtime geometry\n\nFull hashes and normalization metadata are in FUNCTION_IDENTITY.json. Stack metric is reported, not silently called zero spills/local traffic. No full runtime/JIT module image was acquired.')
    table(root/'models/TILE_MODEL_FIT.md',['Model','Median relative error','Max relative error'],[[k,f"{v['median_relative_error']:.8%}",f"{v['max_relative_error']:.8%}" if 'max_relative_error' in v else 'N/A'] for k,v in m['models'].items()],'# Frozen model comparison\n\nFit B=1,2,4,8,16,32,64 only. T64 is primary; T16/T32/T128 are fixed exclusions. B128 remains a boundary diagnostic. M0 constant inflation uses the arithmetic mean inflation across fit points.')

    sys.path.insert(0,str(a.figure_skill/'scripts'))
    from paper_style import setup_style,trend_plot,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',width_inches=3.5,height_ratio=.78,font_family='serif',use_scienceplots=False)
    configs=[
        ('batch_vs_inflation',seq('inflation'),[max(1,64/b) for b in bs],['Measured','Fixed-64 expectation'],'Executed/useful proxy (×)'),
        ('inflation_times_batch',seq('inflation_times_B'),[max(64,b) for b in bs],['Measured','Fixed-64 expectation'],'Inflation × batch size (×)'),
        ('dram_vs_flops_per_query',[w[str(b)]['DRAM_bytes_per_query']/w['1']['DRAM_bytes_per_query'] for b in bs],[w[str(b)]['executed_FP32_proxy']/b/w['1']['executed_FP32_proxy'] for b in bs],['DRAM/query','FP32 proxy/query'],'Normalized per-query work (B1 = 1)'),
        ('throughput_vs_batch',[t[str(b)]['queries_per_second']['median'] for b in bs],None,['Complete-output ACK'],'Throughput (queries/s)'),
    ]
    for name,y,other,labels,ylabel in configs:
        with (root/'figures'/(name+'.csv')).open('w') as f:
            writer=csv.writer(f,lineterminator='\n');writer.writerow(['B',*labels]);writer.writerows([[b,y[i]]+([] if other is None else [other[i]]) for i,b in enumerate(bs)])
        fig,ax,_=trend_plot(bs,[y] if other is None else [y,other],labels,xlabel='Native query batch size B',ylabel=ylabel,colors=['#0072B2'] if other is None else ['#0072B2','#333333'],markers=['o'] if other is None else ['o','s' if name=='dram_vs_flops_per_query' else ''],linestyles=['-'] if other is None else ['-','--'],legend_kwargs=dict(loc='best',fontsize=7))
        if name=='dram_vs_flops_per_query':
            ax.lines[1].set_markerfacecolor('none');ax.legend(loc='best',fontsize=7,frameon=False)
        ax.set_xscale('log',base=2);ax.set_xticks(bs,labels=list(map(str,bs)))
        if name in ('batch_vs_inflation','dram_vs_flops_per_query'):ax.set_yscale('log',base=2)
        if other is None:
            lo=np.array([t[str(b)]['queries_per_second']['p10'] for b in bs]);hi=np.array([t[str(b)]['queries_per_second']['p90'] for b in bs])
            ax.errorbar(bs,y,yerr=[np.array(y)-lo,hi-np.array(y)],fmt='none',ecolor='#0072B2',capsize=2)
            ax.set_ylim(bottom=0)
        fig.tight_layout(pad=.4)
        save_fig(fig,name,formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False)
        svg=root/'figures'/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n');plt.close(fig)

    tr=m['traffic'];g=m['geometry_support'];b1=m['B1_reproduction'];decision=m['decision']
    next_action='Only dispatch/kernel-route provenance; no optimization. Preserve the original traffic gate and distinguish database reuse from repeated database loads.' if decision=='PARTIAL_PADDING' else 'Stop the small-B tile explanation; the next separately admitted study is exact representation/compulsory-byte reduction.' if decision=='REJECT_PADDING' else 'Run the required upstream prior-art kill test before any optimization or research contribution claim.'
    (root/'DECISION.md').write_text(f'''# {decision}

Qualified diagnostic on GIST N1M/D960, FP32 row-major L2Unexpanded, same native library and admitted device. No new kernel, library change, layout change or optimization.

## Q1 — Does execution follow64/B?

Primary T64 median relative error: **{m['models']['T64']['median_relative_error']:.8%}** over all seven frozen fit points. B1 inflation **{w['1']['inflation']:.5f}×**; B64 **{m['B64_inflation']:.5f}×**. B128 is a held-out boundary, not used to refit T.

## Q2 — Does B64 approach useful work?

B64 inflation **{m['B64_inflation']:.5f}×**; declared limit1.5×. Useful scalar proxy is2.879G/query, not a count of all auxiliary operations.

## Q3 — Does traffic decouple?

B64/B1 per-query FP32 factor **{tr['FP32_per_query_normalized_B64']:.8f}**; measured DRAM factor **{tr['DRAM_per_query_normalized_B64']:.8f}**. Separation **{tr['separation_log2']:.8f} log2**, required≥1: **{'PASS' if tr['passed_decoupling_gate'] else 'FAIL'}**. Database reuse can decrease both curves together; failure does not refute arithmetic padding, but it prevents CONFIRM under the retained contract.

## Q4 — Is there independent geometry evidence?

Conservative predeclared geometry check: **{'PASS' if g['passed'] else 'FAIL'}**. Same normalized function/block/grid through B64: {g['same_function_block_grid_B1_through_B64']}. Actual B64 grid **{w['64']['geometry']['grid']}** changes to **{w['128']['geometry']['grid']}** at B128, with the same selected function hash. The original analysis predicate requires exactly one doubled axis with every other axis unchanged; its matching axes are {g['doubled_query_axis_candidates']}. A doubled query axis plus a reduced database axis is corroborative batch-route evidence, not evidence against padding, but does not pass that stricter predicate. No source tile constant or full runtime/JIT module image was recovered. Even a broader positive geometry interpretation cannot change the final verdict because the traffic gate fails.

## Q5 — Final decision

**{decision}**. B1 complete payloads reproduce the prior keeper exactly; FADD/FFMA and selected identity reproduce. Fresh original keeper stability ratio95% CI **[{b1['ratio_ci95'][0]:.6f}, {b1['ratio_ci95'][1]:.6f}]**, unpaired process bootstrap. Six processes/B and all eight NCU profiles passed the quality/isolation/provenance gates.

## Boundary and next action

{next_action}

Timing is complete-output native ACK, not tree/workflow/application E2E. Native batches change query shape and reuse; they are not a GTSPP speedup or a64× recoverable latency promise. Optional repeated-single was omitted (N/A). B64/128 use a separately frozen128-query pool. No detailed PRIOR_ART is produced unless CONFIRM. No manuscript update or optimization was authorized by this diagnosis.
''')
    (root/'CLAIM_EVIDENCE.md').write_text(f'''# Claim–evidence ledger

| ID | Claim | State | Evidence / denominator | Counterevidence and allowed wording |
| --- | --- | --- | --- | --- |
| C1 | Original B1 execution reproduced | measured | timing/BATCH_SCALING.json; models/TILE_MODEL_FIT.json; evidence/QUALITY_RECEIPTS.json | Exact original output payloads and function/counters; unpaired fresh-keeper stability, not a speedup |
| C2 | Fixed64 executed-work model | inferred | counters/EXECUTED_WORK.json + models/TILE_MODEL_FIT.json; one selected distance launch/B | Model error {m['models']['T64']['median_relative_error']:.8%}; no direct source constant or full JIT module image |
| C3 | Per-query traffic versus arithmetic | measured | traffic/DRAM_SCALING.json; same NCU denominator and frozen traffic gate | Traffic separation {tr['separation_log2']:.8f} log2; database reuse is an explicit alternative |
| C4 | Final causal verdict | {'inconclusive' if decision=='PARTIAL_PADDING' else 'inferred'} | DECISION.md; frozen CONTRACT.json | Only {decision}; no silent relaxation of failed conditions |
| C5 | Native batch complete-output throughput | measured | timing/PROCESS_SAMPLES.json and BATCH_SCALING.json; six process means/B | Different invocation shape, B64/128 registered extended pool; p10/p90 are not CI; repeated-single N/A |
| C6 | GTSPP/tree/workflow gain or novelty | unknown | no evidence in this diagnostic | No such claim or paper change; no optimization candidate introduced |

Provenance: base518d846, immutable measurement source/input/library pins and all75 job receipts in evidence/. Publication commit is recorded by Git, not backdated as the measured build revision.
''')
    (root/'README.md').write_text(f'''# Query-tile padding causal diagnosis

**Decision: {decision}.** Fixed64 model median error **{m['models']['T64']['median_relative_error']:.8%}**; inflation **{w['1']['inflation']:.5f}× → {m['B64_inflation']:.5f}×** (B1→B64). The strongest material caveat is the retained traffic gate: DRAM/query and FP32/query separation is **{tr['separation_log2']:.8f} log2**, threshold≥1.

B128 changes grid **{w['64']['geometry']['grid']} → {w['128']['geometry']['grid']}** without changing selected-function identity. This corroborates a batch route, but the conservative geometric predicate fails because more than one axis changes; it is not a refutation of fixed64 arithmetic. No direct source constant was recovered.

{next_action}

## Scope and validation

- GIST1,000,000×960 FP32, L2Unexpanded, radius bits0x3f34a3d8; same cuVS26.8.1 containers, CUDA13.1 and RTX PRO6000 Blackwell Server Edition188SM/96GB; same privately pinned prior GPU/NUMA.
- Only a host batch driver was added; original B1 Scan::range and all original output kernels/compaction semantics are unchanged.
-75 guarded top-level starts:13 qualification (8 bounded shapes,3 sanitizers,2 target-scale),6 immutable original keepers,48 primary,8 independent NCU. No GPU failure/retry. One pre-GPU CPU allocation-alias failure is retained in ATTEMPTS.md.
- Complete membership versus ordered-FP64 oracle; native/field scale tolerance5e-5; B1 original payload identity. All output/report/source/input hashes independently reverified before curation.
- B≤32 uses original32 pool; B64/128 separately registered128 distinct queries.8 warmup+32 measured invocations/process. Cyclic repeats across invocations are disclosed; no duplicate within a batch.
- Primary scope: query H2D, native distance, full per-row output compaction/fields, charged observer/D2H, completion. Context/data loading/build/expanded workspace are outside ACK; continuous pass and setup metadata remain external.
- NCU one first-measured invocation/B, all native distance launches covered; NSYS confirms target B128 has one native launch. Profiler time is not primary timing.

## Results

1. [Executed work](counters/EXECUTED_WORK.md)
2. [Measured traffic](traffic/DRAM_SCALING.md)
3. [Launch geometry](geometry/KERNEL_GEOMETRY.md)
4. [Complete-output throughput](timing/BATCH_SCALING.md)
5. [Frozen models](models/TILE_MODEL_FIT.md), [decision](DECISION.md), [claim ledger](CLAIM_EVIDENCE.md)

![Inflation](figures/batch_vs_inflation.png)

![Inflation times batch](figures/inflation_times_batch.png)

![Measured traffic versus arithmetic](figures/dram_vs_flops_per_query.png)

![Complete-output throughput](figures/throughput_vs_batch.png)

Figures1–3 show single-invocation diagnostic counters without invented uncertainty. Figure4 shows six-process median QPS with p10/p90 whiskers, not a CI. Each figure is authored at3.5-inch single-column width. CSV + PDF/SVG/PNG outputs are included; optional repeated-single is N/A.

## Reproduction and publication boundary

See REPRODUCE.md. CONTRACT.json and measurement source were frozen before GPU execution. Exact libraries/data/keeper/CPU oracle/source/pools and scalar quality receipts are in evidence/. Full vectors, reference arrays, all complete payloads, private placement, vendor reports and SASS remain outside Git, indexed by hashes. The manuscript is untouched. This is baseline diagnosis, not GTSPP novelty or tree/workflow E2E benefit.
''')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--figure-skill',type=Path,required=True);report(p.parse_args())
