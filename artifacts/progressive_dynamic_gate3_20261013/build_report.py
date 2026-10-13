"""CPU-only report and four plots from immutable curated Gate3 observations."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
LABELS={'trace_ms':'Service events + release','events_ms':'Events','release_ms':'Native/device release','ack_sum_ms':'All ACKs','range_ms':'Range ACKs','knn_ms':'kNN ACKs','insert_ms':'Insert ACKs','delete_ms':'Delete ACKs'}
def read(p):return json.loads((HERE/p).read_text())
def write(p,s):
    q=HERE/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s.rstrip()+'\n')
def csvfile(name,header,rows):
    with (HERE/'figures'/name).open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(header);w.writerows(rows)
def reports():
    a=read('timing/TRACE_A.json');m=a['metrics'];t=m['trace_ms'];r=m['range_ms'];rows=read('operations/OP_BREAKDOWN.json')['processes']
    assert a['decision']=='UNCLASSIFIED' and read('timing/TRACE_B.json')['measurement'] is None
    table='| Metric | D0 median (ms) | D1 median (ms) | Median ratio D1/D0 | Paired geometric ratio | Paired 95% CI | Wins |\n| --- | ---: | ---: | ---: | ---: | --- | ---: |\n'
    for k,v in m.items():table+=f"| {LABELS[k]} | {v['modes']['D0']['median']:.6f} | {v['modes']['D1']['median']:.6f} | {v['ratio']:.9f} | {v['paired_geometric_ratio']:.9f} | [{v['paired_CI95'][0]:.9f}, {v['paired_CI95'][1]:.9f}] | {v['wins']}/6 |\n"
    sample='| Pair | Order | D0 service (ms) | D1 service (ms) | Paired D1/D0 |\n| --- | --- | ---: | ---: | ---: |\n'
    for i,p in enumerate(a['paired_processes'],1):sample+=f"| {i} | {'D0/D1' if i%2 else 'D1/D0'} | {p['D0']['trace_ms']:.6f} | {p['D1']['trace_ms']:.6f} | {p['D1']['trace_ms']/p['D0']['trace_ms']:.9f} |\n"
    write('timing/TRACE_A.md',f'''# A: fixed 336-event integration trace

**UNCLASSIFIED.** The primary ratio of process-total medians is {t['ratio']:.9f}; the required <=0.85 is not reached. No sample replacement or threshold change was made.

{table}
All values aggregate inside each fresh process before statistics. The primary estimator is the ratio of medians, not the paired geometric ratio. The interval bootstraps six matched log ratios, 20,000 replicates, seed 2026101303. Events are not independent performance samples. [Timer boundary](../TIMING_BOUNDARY.md) limits the denominator to events + native/device/live-map release; retained Host-container destruction is unmeasured.

{sample}
Primary p10/median/p90 (ms): D0 {t['modes']['D0']['p10']:.6f}/{t['modes']['D0']['median']:.6f}/{t['modes']['D0']['p90']:.6f}; D1 {t['modes']['D1']['p10']:.6f}/{t['modes']['D1']['median']:.6f}/{t['modes']['D1']['p90']:.6f}.

Primary order strata: forward geometric ratio {t['order_strata']['forward']['ratio']:.9f}, 3/3 wins; reverse {t['order_strata']['reverse']['ratio']:.9f}, 3/3 wins. No order stratum is discarded.
''')
    write('timing/TRACE_B.md','''# B: not executed

The 1000-event CPU-frozen trace (400I/400D/100R/100K) exists, but A is UNCLASSIFIED. All six formal B jobs and the D1 stage-probe job remain unexecuted. Zero measured pairs is missing evidence, not a measured zero latency, zero error or regression. No update-heavy robustness or full dynamic admission is asserted.
''')
    knn_share=float(np.mean([v['3']/v['events_ms'] for v in rows if v['label'].endswith('D0')]))
    event_stats=[]
    for mode in ('D0','D1'):
        by={str(i):[] for i in range(4)}
        for row in rows:
            if row['label'].endswith(mode):
                with (HERE/'operations/raw/A'/f"{row['label']}.ops.csv").open() as f:
                    for op in csv.DictReader(f):by[op['flag']].append(float(op['ack_ms']))
        for flag,values in by.items():event_stats.append(dict(mode=mode,operation={'0':'Insert','1':'Delete','2':'Range','3':'kNN'}[flag],events=len(values),p10_ms=float(np.quantile(values,.1)),median_ms=float(np.median(values)),p90_ms=float(np.quantile(values,.9))))
    write('operations/EVENT_DISTRIBUTIONS.json',json.dumps(dict(scope='pooled descriptive event distribution,not independent process-level performance inference',records=event_stats),indent=2))
    event_table='| Mode | Operation | Pooled events | p10 ACK (ms) | Median ACK (ms) | p90 ACK (ms) |\n| --- | --- | ---: | ---: | ---: | ---: |\n'
    for v in event_stats:event_table+=f"| {v['mode']} | {v['operation']} | {v['events']} | {v['p10_ms']:.9f} | {v['median_ms']:.9f} | {v['p90_ms']:.9f} |\n"
    write('README.md',f'''# Dynamic Progressive Integration Gate3

**Result: UNCLASSIFIED; B not executed; ENGINEERING_ONLY.** On GIST1M (1,000,000 FP32 vectors, D=960), the fixed 336-event workflow has 128 exact range requests, 128 native Faiss kNN requests (k=8), 40 inserts and 40 deletes. Six fresh paired rounds remeasure both systems, alternating order.

- Range total ACK median: {r['modes']['D0']['median']:.6f} -> {r['modes']['D1']['median']:.6f} ms; **{100*(1-r['ratio']):.2f}% lower**, {1/r['ratio']:.6f}x.
- Segmented service median: {t['modes']['D0']['median']:.6f} -> {t['modes']['D1']['median']:.6f} ms; **{100*(1-t['ratio']):.2f}% lower**, ratio **{t['ratio']:.9f} > 0.85**. Six of six pairs improve, but the frozen >=15% GO gate fails.
- Insert/delete total ACK ratios: {m['insert_ms']['ratio']:.6f}/{m['delete_ms']['ratio']:.6f}; no >1.5x update regression. Exact outputs and final state pass within the bounded trace.
- D1 adds 32,031,488 bytes of reusable O(N) query workspace, not an O(ND) persistent vector copy. No rebuild or changed kNN path.

The timer is **events + native/device/live-map release**, not complete process wall time. Full final-state validation is separately excluded; ordinary answer serialization and retained Host-container destruction happen after the timer. See [the retained deviation](TIMING_BOUNDARY.md). No broader complete-release claim is made.

## Mechanism and limit

Redundant coordinates after a safe rejection -> exact partial-distance rejection -> frozen 128/256/512/960 scan + stable compaction -> lower complete range ACK latency. The unchanged kNN path consumes {100*knn_share:.2f}% of D0 event time (mean of six per-process shares), limiting the observed workflow gain. Gate3 did not collect dynamic DRAM counters; Gate2 static traffic cannot be relabeled as dynamic evidence.

D0 keeps the strengthened non-padded scan; D1 changes only range and borrows the same raw-vector storage, stream and outputs. Updates append/swap-delete with identical logical-occurrence ownership. Progressive state is query-only, reserved before service ready and released at the charged device boundary. No tree, stored prefix index, representation reorder or production dispatch change.

## Evidence

| Gate | Status and scope |
| --- | --- |
| Source/input/binary/library freeze | Bound by SHA256; D0 distance SASS matches strengthened keeper, all five D1 progressive kernels match Gate2 |
| Qualification | 10/10 successful; memcheck/racecheck/synccheck on N=65/D960 synthetic fixtures, plus two full A dry runs |
| Formal timing | 12/12 successful; six matched fresh pairs, no extra probes in timed event streams |
| Correctness | Complete members, distance fields, multiplicity, mutation induction, actual full final maps and every final vector byte |
| Conditional B | NOT_EXECUTED, A was not GO |
| Novelty/thesis | Not admitted; prior partial-distance/cheap-update precedents remain binding |
| Launch accounting | 22 successful CUDA processes + one preserved pre-CUDA guard failure = 23/30 approved starts |

See [decision Q1–Q5](DECISION.md), [claim ledger](CLAIM_EVIDENCE.md), [novelty closure](NOVELTY_CLOSURE.md), [A samples/statistics](timing/TRACE_A.md), [memory](memory/README.md), [quality](correctness/README.md), and [reproduction](REPRODUCE.md).

## Figures

![Service latency](figures/trace_latency.png)
![Operation attribution](figures/operation_breakdown.png)
![Matched range ratio](figures/range_ratio.png)
![Fixed-pool stage robustness](figures/stage_robustness.png)

Vector PDF/SVG, 600-DPI PNG, source CSVs and [scope-bearing captions](figures/CAPTIONS.md) accompany all four plots. No B data is plotted.

## Publication boundary

This artifact publishes task-owned source, frozen logical event IDs, scalar observations and hashes. Private vector data, complete raw payloads, binaries, compiler/library placement, device identities and failure traces remain outside Git. [Raw identities](evidence/RAW_IDENTITY.json) are receipts, not the payloads themselves. The broader repository has pre-existing public history; this update is not an anonymous or whole-history-sanitized release. No manuscript or Overleaf content is included.
''')
    write('DECISION.md',f'''# Decision: UNCLASSIFIED

## Q1: how much static range benefit survives A?

A-local complete range ACK speedup is **{1/r['ratio']:.6f}x**, reduction {100*(1-r['ratio']):.2f}%. The prior static 2.255428x used a different 32-query pool; A has 128 range requests. A percentage of static gain retained would mix contracts and is not calculated. Service events + release improves {100*(1-t['ratio']):.2f}%, below the frozen >=15% requirement.

## Q2: are updates still cheap?

For the 40-event insert and delete totals, D0/D1 medians are {m['insert_ms']['modes']['D0']['median']:.6f}/{m['insert_ms']['modes']['D1']['median']:.6f} ms and {m['delete_ms']['modes']['D0']['median']:.6f}/{m['delete_ms']['modes']['D1']['median']:.6f} ms. Ratios {m['insert_ms']['ratio']:.6f}/{m['delete_ms']['ratio']:.6f} do not trigger >1.5x regression. This is fixed-D, preallocated, bounded evidence, not constant-time asymptotic complexity or unlimited churn qualification.

## Q3: index, rebuild or heavy maintenance?

No D1-specific persistent O(ND) device representation, tree or rebuild. One unchanged raw vector buffer and native kNN norms coexist with borrowed progressive access and an extra 32,031,488 bytes of O(N) reusable query workspace. Both retain a CPU input copy and logical maps. Preallocation/setup and library reservations are not free; see memory accounting.

## Q4: update-heavy exactness and selectivity?

**Unknown: B was not admitted or executed.** A's diagnostic fixed32 pool passes all 128 checkpoint queries; maximum per-query prefix-survivor change is 0.0007 percentage points across initial/20I20D/40I40D/final. This is descriptive small-update evidence, not a B or long-workflow claim. No numerical stability cutoff was invented.

## Q5: gate classification and action?

| Priority/test | Result |
| --- | --- |
| Correctness/ownership/final-state failure | None observed within qualified scope |
| Insert or delete total ACK ratio >1.5 | No |
| Range ratio <=0.60 | Pass: {r['ratio']:.9f} |
| Service ratio <=0.85 | **Fail: {t['ratio']:.9f}** |
| Paired primary CI upper <0.92 and >=5 wins | Pass: {t['paired_CI95'][1]:.9f}; 6/6 |
| Remaining NO_GO: service >=0.95 or range >0.75 | Neither |
| Uncovered interval | **UNCLASSIFIED, stop** |

Implementation is validated only for the declared bounded trace and fixture scopes. The progressive range mechanism retains a strong local ACK benefit. Full dynamic admission is withheld, and novelty remains ENGINEERING_ONLY. B, stages, mix, kNN, external comparisons, 100k events and large-scale matrices are not automatically pursued.

## Retained negative evidence and reopen condition

Keeper D0 and D1 were remeasured on the same GIST1M/D960 stream. D1 adds query workspace/compaction/control, cuts range ACK time, but unchanged kNN dominates the baseline and the primary ratio misses 0.85. This does not reject all progressive execution; it fails current workflow admission without resolving the declared gray interval. The broader complete-Host-release interpretation is additionally unvalidated, not inferred from this timer.

Do not revive this frozen candidate by resampling, picking another estimator, adjusting stages, changing query mix or modifying kNN. Reopening a paper direction requires a distinct non-incremental mechanism and decisive same-contract external evidence, separately authorized and preregistered; this artifact stays immutable.
''')
    write('CLAIM_EVIDENCE.md','''# Claim–evidence ledger

Experiment: `GTSPP_20261013_dynamic_progressive_gate3`; parent commit `6baaa376a4b7afe3192ab3ba1b4269993856d479`; measurement date 2026-10-13. Hardware/software identities are in `evidence/ENVIRONMENT.json`; source/binary/input/library bindings in `evidence/INPUT_IDENTITY.json`; raw identities and per-process receipts are retained. Numeric wording below uses the tables, not a different estimator.

| ID | State | Exact scope/denominator and strongest allowed wording | Evidence | Counterevidence/limit |
| --- | --- | --- | --- | --- |
| G3-RANGE | measured | Six paired fresh A processes: complete range ACK total median is 53.35% lower, 2.143573x | timing/TRACE_A.json; operations/raw/A; quality receipts | Different pool than Gate2; no dynamic DRAM profile |
| G3-SERVICE | measured | A events + native/device/live-map release median is 14.41% lower | timing/TRACE_A.json; TIMING_BOUNDARY.md | Not entire process wall/complete Host teardown; setup and offline proof excluded |
| G3-UPDATE | measured | Forty insert/delete ACK totals retain the same sub-ms magnitude; ratios 1.036157/0.961227 | updates/UPDATE_ROBUSTNESS.json; operation records | Fixed D960/capacity; not asymptotic O(1) or unlimited churn |
| G3-QUALITY | measured | Complete member/field/multiplicity and final-state checks pass for all 22 successful formal/qualification processes | correctness; evidence/QUALITY_PROCESSES.json | Update map validity uses induction, not actual full export each mutation; sanitizers are N65 fixtures |
| G3-MEMORY | measured | No D1 O(ND) persistent vector copy; D1 adds 32,031,488 query-workspace bytes | memory | Both keep CPU input; sampled device peak is not exact owned peak; CPU RSS unknown |
| G3-STAGE | partial | Fixed32 diagnostic pool changes by at most 0.0007 pp per query/prefix over A checkpoints | updates/STAGE_ROBUSTNESS.json | Descriptive, separate process, no B/long-update stability gate |
| G3-KNN-LIMIT | inferred | Unchanged kNN dominates measured D0 event time and limits current total savings | operation attribution | Measured component shares, not a causal new kNN experiment |
| G3-ADMISSION | inconclusive | UNCLASSIFIED: ratio 0.855934141 >0.85; stop without B | CONTRACT.json; analyze.py; DECISION.md | Six wins/CI do not waive the primary threshold |
| G3-B | unknown | Frozen update-heavy B has no GPU evidence | timing/TRACE_B.json | Must not report zero errors or latency |
| G3-THESIS | rejected | No current paper-thesis promotion; partial-distance and cheap-update principles already precedented | PRIOR_ART.md; NOVELTY_CLOSURE.md | No distinct non-incremental mechanism/same-contract external advantage |

No claim for dynamic DRAM reduction, progressive kNN, universal GPU-tree redundancy, 10k queries, 100k events, 1B vectors, capacity rollover, CUDA Graphs or production dispatch is supported by this campaign. Preserve current measurements and failure records; do not relabel an incomplete gate as GO.
''')
    write('operations/OP_BREAKDOWN.md',f'''# Operation attribution

The primary metric is each process's actual events + release, then its median. The figure instead stacks **means of per-process component totals**, so the components exactly sum to mean primary latency; it never stacks component medians. Raw operation, complete count/field-quality and ownership witnesses are preserved per process in `raw/A`.

{table}
Mean of D0 per-process kNN/event shares: {100*knn_share:.6f}%. kNN is byte-identical and its paired interval includes 1; do not claim a kNN optimization. The first measured lazy native kNN setup remains inside its ACK. CPU usage and result transfer/waits are included in event ACKs, not separated into a new CPU-wait benchmark.

Insert/delete pixels are tiny because the query-dominated trace has only 40+40 updates; use the table, not their plotted height, to assess regression. Formal samples contain no extra fixed32 probes. B attribution is unavailable.

## Descriptive individual-event distribution

{event_table}
Events are pooled across six processes for descriptive distributions only. They are not additional independent process observations or the estimator for update-regression gates. Lazy native kNN initialization remains charged in the first measured ACK, even when a pooled quantile does not display that rare tail. All events are retained in raw CSVs.
''')
    states=read('updates/STAGE_ROBUSTNESS.json')['A']['snapshots']
    st='| Checkpoint | after128 (%) | after256 (%) | after512 (%) |\n| --- | ---: | ---: | ---: |\n'
    for name,v in zip(('Initial','20I/20D','40I/40D','Final'),states):st+=f"| {name} | {v['mean_percent'][0]:.9f} | {v['mean_percent'][1]:.9f} | {v['mean_percent'][2]:.9f} |\n"
    write('updates/README.md',f'''# Bounded update and stage checks

{st}
Means cover the same 32 fixed diagnostic queries, not the 128 A range requests. The A dry process alone adds 128 probes at exact initial/20I20D/40I40D/final points (steps -1/132/300/336). All complete probe members, fields and prefix survivors match independent CPU references. Maximum per-query survivor drift at any prefix is 0.0007 percentage points. There is no repeated-process CI or invented stability threshold for this deterministic description.

Native append/swap-delete/norm updates are unchanged. Formal total ACK ratios stay below 1.5. B and unlimited/capacity-growing updates were not run; the seed-frozen B inputs are not measurements.
''')
    write('memory/README.md','''# Memory and maintenance accounting

A reserves capacity 1,000,040; all byte values are decimal bytes, not GiB. Persistent device vectors are one allocation in both variants. Forward/reverse logical maps live on the CPU.

| Owned storage | D0 (B) | D1 (B) |
| --- | ---: | ---: |
| Raw FP32 device vectors | 3,840,153,600 | 3,840,153,600 |
| Native kNN device norms | 4,000,160 | 4,000,160 |
| CPU forward-map capacity | 4,000,160 | 4,000,160 |
| CPU reverse-map capacity | 4,000,160 | 4,000,160 |
| Retained CPU input vectors | 3,840,153,600 | 3,840,153,600 |
| Reusable query workspace, total | 25,006,891 | 57,038,379 |
| PrefixState ping-pong, part of above | 0 | 32,001,280 |
| CUB reserved scratch, part of above | 2,047 | 32,255 |

D1 adds 32,031,488 query-workspace bytes. Common D0 buffers retained by D1 remain charged. Workspace reservation occurs before service ready; use and native/device release follow the service boundary. Query-only state is persistent across requests as reusable capacity, but it is not a maintained index or a precomputed O(ND) representation.

CUDA mem-info after events reports 6,165,364,736/6,198,919,168 bytes (D0/D1), including context/library reservations. Device memory after service release is 614,203,392 bytes in both; remaining context/library globals are not claimed free. Private 200ms device-wide samples give 5880/5912 MiB high-water marks, **not exact peak or ownership proof**. CPU RSS peak was not measured. Offline final validation transiently creates another CPU replay copy outside primary timing. Retained client/audit Host-container destruction is unmeasured.

No tree/rebuild, D1-specific duplicated database or representation maintenance is introduced. Monotonic logical IDs and fixed capacity were qualified only for these 40 inserts/40 deletes; eventual capacity exhaustion/growth/rollover remains outside scope.
''')
    q=read('evidence/QUALITY_PROCESSES.json');parts=[v[k] for v in q for k in ('measured','warmup')]
    write('correctness/README.md',f'''# Correctness scope and receipts

All 22 successful processes pass complete range IDs/multiplicity, tie-aware k=8 membership, declared native-field tolerance, mutation ownership and final state. Formal timing has six matched pairs; qualification and warmup are not extra performance samples.

- Ordinary measured/warmup queries checked: {sum(v['queries'] for v in parts):,}; plus 128 separate diagnostic probes.
- Mutation witnesses/replay transitions checked: {sum(v['updates'] for v in parts):,}.
- Actual final GPU vector bytes directly compared to independent CPU replay: {sum(v['final_proof']['all_vector_bytes_bitwise_compared'] for v in parts):,}.
- Range is inclusive ordered-FP64 membership, no false positive/negative. Equal vectors retain distinct logical occurrences. kNN permits exact-distance ties at kth, never drops a strictly closer member; native FP32 fields use frozen 5e-5 scale1 tolerance.
- Actual local mutation witnesses plus the frozen native mutation body support full independent map/live-set induction after every update. This is **not full actual-map export at each mutation**. Actual final full forward/reverse maps and every final vector byte are directly checked, not merely hashed.
- N65/D960 synthetic fixtures cover duplicate deletion, inserted-then-deleted rows, swap-last, row reuse, inclusive boundaries and later-stage coordinates. Both variants pass fixture memcheck/racecheck/synccheck. Full A dry checks run on 1M/D960; there is no full-1M sanitizer, CUDA Graph, unbounded churn or B qualification.

The first fixture guard failed before CUDA initialization because it received out-of-range probe IDs. Its failed record remains preserved; the approved recovery passed an empty fixture probe pool, changed no binary or input and repeated no passed sample. `evidence/RECOVERY.json` binds the original failure and the 30-start cap. One CPU-only resource-export assertion was corrected separately; all GPU observations remain unchanged (`evidence/POSTPROCESSING_CLOSURE.json`).

Public receipts contain hashes and scalar quality details; complete raw answer payloads, ordered score arrays, binary/vector contents and private placement are retained outside Git. Public scalar consistency checks are not a substitute for private full-payload revalidation.
''')
    write('REPRODUCE.md','''# Reproduction boundaries

## CPU-only published artifact check

From a complete repository checkout with Python/numpy installed:

```sh
python3 artifacts/progressive_dynamic_gate3_20261013/test_gate3.py
python3 artifacts/progressive_dynamic_gate3_20261013/check_artifact.py
python3 artifacts/progressive_dynamic_gate3_20261013/build_report.py
```

The last command requires matplotlib and writes the report, CSVs and PDF/SVG/600-DPI PNG plots. This is postprocessing only and never runs CUDA. Generated figure bytes may differ across font/library versions; scalar tables and contract decisions must agree.

## GPU remeasurement (separate authorization and registration)

This published run is closed at UNCLASSIFIED. Do not run B, reuse/overwrite its work directory or automatically retry. A new remeasurement needs its own approved budget and idle same-model GPU. The harness expects an accepted Gate2 prepared workspace (including the strengthened keeper's original336 trace) and the complete hash-matched GIST1M raw FP32 file plus frozen parents/references; hashes are in `evidence/INPUT_IDENTITY.json`. Missing private inputs are not fetched or reconstructed from scalar receipts.

```sh
export G3=artifacts/progressive_dynamic_gate3_20261013
# Set an unused directory outside the repository and the verified Gate2 parent.
python3 "$G3/prepare.py" --work "$NEW_WORK" --parent "$GATE2_WORK" --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 "$G3/static.py" --work "$NEW_WORK"
python3 "$G3/campaign.py" --work "$NEW_WORK" --stage qualification --gpu "$GPU_UUID" --numa "$NUMA_NODE"
python3 "$G3/campaign.py" --work "$NEW_WORK" --stage A --gpu "$GPU_UUID" --numa "$NUMA_NODE"
```

These commands are documentation, not authority to execute. Preparation freezes sources, generated shared native bodies, input vectors/event order, ordered CPU references and transitive guard imports; it compiles both variants and does not initialize CUDA. Static comparison binds exact selected SASS/full binary containers. Each campaign process uses shared advisory locking, two-sided PID/start-time isolation observation and NUMA affinity. The first failed guard/quality gate stops the campaign without an automatic retry. Apply `analyze.py`'s fixed priority; B is structurally blocked unless A is GO. The original budget is 29; this run's human-approved one-failure recovery cap is 30, total observed starts 23.

The preserved recovery was argument-only: empty fixture probe pool, unchanged data/binaries/query order/timers/quality, new work registration and retained first failure. Do not use recovery support as a general rerun mechanism. The measured source set remains immutable; report/curation changes are explicitly separate CPU postprocessing.

For full private revalidation, freeze `curate.py`'s SHA256 in a JSON file `{"curate.py":"<sha256>"}`, then use `curate.py --work "$EXISTING_CLOSED_WORK" --out "$UNUSED_EXPORT_DIR" --analysis-freeze "$FREEZE_JSON"`. It rechecks registrations, source/binary/library/input/output hashes, complete result/order and guard receipts before publishing only scalar evidence. The full ordered references/payloads are needed to independently recompute the original GPU quality checks; public hashes alone cannot do that.
''')

def plots(helper=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style=None
    if helper:
        sys.path.insert(0,str(helper));import paper_style as style
        style.setup_style('acm_double',width_inches=3.35,height_ratio=.76,use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'figure.figsize':(3.35,2.55),'font.family':'serif','font.serif':['Nimbus Roman','Times New Roman','DejaVu Serif'],'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'pdf.fonttype':42,'svg.fonttype':'none','savefig.bbox':'tight'})
    fdir=HERE/'figures';fdir.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout(pad=.45)
        if style:style.save_fig(fig,name,formats=('pdf','svg','png'),output_dir=fdir,dpi=600,target_width_inches=3.35,min_font_size=6,strict=True)
        else:
            for ext in ('pdf','svg','png'):fig.savefig(fdir/f'{name}.{ext}',dpi=600,bbox_inches='tight',pad_inches=.02)
        svg=fdir/f'{name}.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
        plt.close(fig)
    a=read('timing/TRACE_A.json');v=a['metrics']['trace_ms'];fig,ax=plt.subplots()
    med=np.array([v['modes'][m]['median'] for m in ('D0','D1')]);lo=np.array([v['modes'][m]['p10'] for m in ('D0','D1')]);hi=np.array([v['modes'][m]['p90'] for m in ('D0','D1')]);err=np.stack((med-lo,hi-med))[:,:,None]
    if style:style.grouped_bars(med[:,None],['A: 336 events'],['D0','D1'],ylabel='Service latency (ms)',errors=err,ax=ax,colors=['#B0B0B0','#0072B2'],hatches=['///',''],legend=False)
    else:ax.bar([-.2,.2],med,width=.36,color=['#B0B0B0','#0072B2'],edgecolor='black',yerr=err[:,:,0],capsize=2.5);ax.patches[0].set_hatch('///');ax.set_xticks([0],['A: 336 events']);ax.set_ylabel('Service latency (ms)')
    bars=ax.patches[:2];csvrows=[]
    for i,m in enumerate(('D0','D1')):
        x=bars[i].get_x()+bars[i].get_width()/2;values=v['modes'][m]['process_totals'];ax.scatter(x+np.linspace(-.05,.05,6),values,s=14,facecolors='white',edgecolors='black',linewidths=.6,zorder=4)
        ax.text(x,med[i]*.5,m,ha='center',va='center',fontsize=9,color='black');ax.text(x,hi[i]+45,f'{med[i]:.1f}',ha='center',fontsize=8)
        csvrows.extend((j+1,m,y) for j,y in enumerate(values))
    ax.set_ylim(0,1450);save(fig,'trace_latency');csvfile('trace_latency.csv',['pair','mode','service_ms'],csvrows)
    rows=read('operations/OP_BREAKDOWN.json')['processes'];parts=[('3','kNN','#B0B0B0',''),('2','Range','#0072B2',''),('release_ms','Release','white','///'),('unattributed_event_bookkeeping_ms','Bookkeeping','white','...'),('0','Insert','black',''),('1','Delete','white','xx')]
    fig,ax=plt.subplots();bottom=np.zeros(2);opcsv=[]
    for key,name,color,hatch in parts:
        values=[float(np.mean([r[key] for r in rows if r['label'].endswith(m)])) for m in ('D0','D1')];ax.bar([0,1],values,width=.55,bottom=bottom,color=color,hatch=hatch,edgecolor='black',linewidth=.5,label=name);bottom+=values
        for r in rows:opcsv.append((r['label'],name,r[key]))
    totals=np.array([[r['trace_ms'] for r in rows if r['label'].endswith(m)] for m in ('D0','D1')]);assert np.allclose(bottom,totals.mean(axis=1),rtol=0,atol=1e-9)
    errors=np.stack((bottom-np.quantile(totals,.1,axis=1),np.quantile(totals,.9,axis=1)-bottom));assert (errors>=0).all()
    ax.errorbar([0,1],bottom,yerr=errors,fmt='none',ecolor='black',capsize=2.5,linewidth=.7)
    ax.set_xticks([0,1],['D0','D1']);ax.set_ylabel('Mean service latency (ms)');ax.set_ylim(0,1650);ax.legend(loc='upper center',ncol=3,frameon=False,fontsize=7,handlelength=1.2,columnspacing=.8);save(fig,'operation_breakdown');csvfile('operation_breakdown.csv',['process','component','total_ms'],opcsv)
    v=a['metrics']['range_ms'];ratios=np.array(v['modes']['D1']['process_totals'])/v['modes']['D0']['process_totals'];fig,ax=plt.subplots()
    for i,y in enumerate(ratios):ax.scatter(i+1,y,s=23,marker='o' if i%2==0 else '^',facecolor='white' if i%2==0 else '#0072B2',edgecolor='black',linewidth=.7)
    g=v['paired_geometric_ratio'];ci=np.array(v['paired_CI95']);ax.errorbar(7,g,yerr=np.array([[g-ci[0]],[ci[1]-g]]),marker='s',color='#0072B2',capsize=3,linewidth=1)
    ax.axhline(.60,color='black',linestyle='--',linewidth=.8);ax.text(.6,.62,'Range gate: 0.60',fontsize=8);ax.set_xticks(range(1,8),[str(i) for i in range(1,7)]+['Geo.']);ax.set_xlabel('Matched pair / geometric estimate');ax.set_ylabel('Range ACK ratio (D1 / D0)');ax.set_ylim(0,.72);ax.set_xlim(.4,7.6);save(fig,'range_ratio');csvfile('range_ratio.csv',['pair','order','ratio'],[(i+1,'forward' if i%2==0 else 'reverse',y) for i,y in enumerate(ratios)])
    states=read('updates/STAGE_ROBUSTNESS.json')['A']['snapshots'];vals=np.array([s['mean_percent'][:3] for s in states]);fig,ax=plt.subplots();names=['Initial','20I/20D','40I/40D','Final'];colors=['#0072B2','#777777','black'];marks=['o','s','^'];lines=['-','--',':']
    if style:style.trend_plot(np.arange(4),vals.T,labels=['128','256','512'],xlabel='A checkpoint',ylabel='Mean survivors (%)',ax=ax,colors=colors,markers=marks,linestyles=lines)
    else:
        for j in range(3):ax.plot(np.arange(4),vals[:,j],label=str([128,256,512][j]),color=colors[j],marker=marks[j],linestyle=lines[j],linewidth=1.2,markersize=4)
        ax.set_xlabel('A checkpoint');ax.set_ylabel('Mean survivors (%)')
    ax.set_xticks(np.arange(4),names);ax.set_ylim(0,80);ax.legend(title='Prefix dims',loc='center right',frameon=False,fontsize=7,title_fontsize=7);save(fig,'stage_robustness');csvfile('stage_robustness.csv',['checkpoint','step','prefix_dims','mean_survivor_percent'],[(name,s['step'],d,s['mean_percent'][j]) for name,s in zip(names,states) for j,d in enumerate((128,256,512))])
    write('figures/CAPTIONS.md','''# Figure captions and estimators

1. **trace_latency:** Range-only replacement lowers A's segmented service median by 14.41%, but does not reach the >=15% GO requirement. Bars: medians of six fresh process totals per system; whiskers: process p10–p90; white dots: all six totals. N=1M/D960, 336 fixed events, complete ACKs + native/device/live-map release. Not process wall/complete Host teardown; offline final proof and setup excluded. B not run.
2. **operation_breakdown:** Unchanged native kNN dominates the query-heavy stream and limits aggregate savings. Stack: arithmetic means of each per-process component total (including actual event bookkeeping + release), exactly summing to mean primary total; whiskers: p10–p90 of six primary process totals. This mean attribution is not the primary median estimator. Tiny insert/delete components are quantified in the operation table. Same A/timing boundary; no B.
3. **range_ratio:** Complete range ACK benefit remains in all six matched pairs. Points: D1/D0 process-total ratios, forward circles/reverse triangles; last square: paired geometric estimate with its 95% percentile bootstrap log-ratio CI (20,000 resamples, fixed seed). Dashed 0.60 is only the range criterion, not proof of workflow GO. N1M/D960, A's128 range ACKs per fresh process. No B.
4. **stage_robustness:** The same fixed32 diagnostic queries retain nearly identical prefix selectivity over A's small update sequence. Lines/markers encode 128/256/512 prefix dimensions. Means across32 queries at each checkpoint, one separate dry D1 process; descriptive, no process repetition/CI/stability cutoff. This is not A's128 query pool or B evidence. Maximum per-query change is 0.0007 percentage points; the zero-origin axis is intentionally not zoomed to exaggerate that drift.
''')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--style-helper',type=Path);p.add_argument('--no-plots',action='store_true');a=p.parse_args();reports()
    if not a.no_plots:plots(a.style_helper)
    print('REPORT UNCLASSIFIED; B not executed; CPU-only postprocessing')
