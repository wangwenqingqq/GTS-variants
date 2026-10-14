"""Build the decision and systems map from completed scalar evidence into fresh scratch."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    load = lambda path: json.loads(Path(path).read_text())
    h = load(a.data / 'b1_information_floor/HEADROOM.json')
    analysis = load(a.data / 'evidence/ANALYSIS.json')
    assert analysis['final'] == 'NO_GO_LIMITS_THESIS' and h['gate_stability'] and h['B1_no_go']
    original = load(a.data / 'b1_information_floor/ORIGINAL_ORDER.json')
    global_v = load(a.data / 'b1_information_floor/QUERY_GLOBAL_ORACLE.json')['nominal']
    pair = load(a.data / 'b1_information_floor/PAIR_ORACLE.json')['nominal']
    b2 = load(a.data / 'b2_metadata_floor/BREAK_EVEN.json')
    b3 = load(a.data / 'b3_online_reuse/EXAMPLES.json')
    timing = load(a.repo / 'artifacts/progressive_gpu_gate2_20261013/timing/PRIMARY_TIMING.json')
    traffic = load(a.repo / 'artifacts/progressive_gpu_gate2_20261013/traffic/DRAM_ACCOUNTING.json')
    extra = ['artifacts/exact_representation_gate1_20261012/analyze.py',
             'artifacts/progressive_dynamic_gate3_20261013/DECISION.md',
             'artifacts/certificate_sector_packing_gate7_20261014/DECISION.md',
             'artifacts/sector_proof_per_byte_gate6_20261014/DECISION.md',
             'artifacts/progressive_lossless_gate0_20261013/DECISION.md']
    a.out.mkdir(parents=True, exist_ok=False)

    def text(name, value):
        dest = a.out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('x') as f:
            f.write(value.strip() + '\n')

    def write(name, value):
        text(name, json.dumps(value, indent=2, allow_nan=False))

    write('evidence/ADDITIONAL_PARENT_IDENTITIES.json', {'parent_commit': '01ad50f0520cb83c02e7b90edb87e773b48a505b',
          'role': 'post-population interpretation counterevidence; no change to frozen gates',
          'files': {name: hashlib.sha256((a.repo / name).read_bytes()).hexdigest() for name in extra}})
    rows = [
        {'system': 'Full exact scan', 'evidence': 'coordinate count plus historical same-campaign GPU timing',
         'extra_indexed_payload_bytes': 0, 'query_source_bytes': 3840000000, 'source_scope': 'one full FP32 coordinate scan; not actual DRAM',
         'actual_DRAM_bytes_per_query': traffic['modes']['B1']['means']['DRAM_bytes'], 'historical_static_Host_ready_ms': timing['modes']['B1']['median'],
         'update_maintenance': 'not measured by this static experiment; common base ownership excluded from x axis'},
        {'system': 'Tree/index', 'evidence': 'historical offline candidate/block identities; no executed layout traffic',
         'extra_indexed_payload_bytes': None, 'query_source_bytes': None, 'update_maintenance': 'UNKNOWN as a same-contract measured cost',
         'L0_block256_reach_percent_initial_rebuilt': [99.4633, 99.5585], 'L1_L3_block256_reach_percent_initial_rebuilt': [76.5477, 63.8589],
         'positive_counterexample': 'contiguity improves reach at identical candidate identities; not all layouts fail'},
        {'system': 'Progressive', 'evidence': 'historical source count plus actual GPU timing/NCU, static fixed32 range',
         'extra_indexed_payload_bytes': 0, 'query_source_bytes': 1014828776, 'extra_query_workspace_bytes_static': 33000000,
         'actual_DRAM_bytes_per_query': traffic['modes']['P1']['means']['DRAM_bytes'], 'historical_static_Host_ready_ms': timing['modes']['P1']['median'],
         'update_maintenance': 'separate bounded dynamic A misses service ratio0.85 gate:0.855934141; update-heavy B NOT_RUN',
         'scope': 'x excludes reusable per-query workspace, base IDs and common ownership; no dynamic near-optimality'},
        {'system': 'Compact metadata filter', 'evidence': 'conditional eager-metadata/full-raw-fallback plane; not realized',
         'extra_indexed_payload_bytes_range': [1000000, 256000000], 'query_source_bytes': None,
         'model': 'extra_bytes + (1-f)*3840000000; f is all-object rejection',
         'update_maintenance': 'UNKNOWN; extra payload is not latency', 'actual_rejection_fraction': None},
        {'system': 'Certified INT8 sidecar', 'evidence': 'design algebra only; parent stopped before population/GPU',
         'extra_indexed_payload_bytes': 968000000, 'query_source_bytes_at_F0': 968000000, 'query_source_bytes': None,
         'model': '968000000 + 3840*F; F includes all final hits and ambiguous objects',
         'update_maintenance': 'UNKNOWN runtime; at least the sidecar is an additional representation to maintain',
         'actual_fallback_or_rejection': None},
        {'system': 'Cross-query batching', 'evidence': 'uncapped long-run Poisson algebra, plus historical finite synthetic trace',
         'extra_indexed_payload_bytes': 0, 'extra_query_workspace_bytes': None, 'query_source_bytes': None,
         'ideal_source_at_5000qps_500us': b3['rows'][3]['source_bytes_per_query'], 'historical_finite_synthetic_source_at_5000qps_500us': 1092249600,
         'update_maintenance': 'UNKNOWN; one-version ownership and service backlog not evaluated',
         'scope': 'reference source comparison only; not a complete SLA/dynamic/mixed-output result'}]
    write('design_space/SYSTEMS_TABLE.json', {'axes': {'x': 'extra indexed payload beyond the shared FP32 database; decimal bytes',
          'y': 'conditional coordinate/metadata source model; not actual DRAM', 'updates': 'separate categorical/unknown field, never converted into bytes or assumed free'},
          'null_means': 'UNKNOWN, not zero; unpriced systems are not assigned fabricated plot positions', 'rows': rows,
          'counterexamples': {'sector_probe': '904744352 conditional source B/query;10.8476% below keeper; unpriced retention/reconstruction',
                              'packed_probe': '817666504 conditional source B/query;19.4281% below keeper; p90 robustness and20% gates failed',
                              'lossless_representation': 'exact single representation validated;1025475825 source B/query exceeds keeper; no GPU'}})
    table = '\n'.join(f'| {name} | {v["mean"]:.8f} | {v["median"]:.1f} | {v["p90"]:.1f} | {v["p95"]:.1f} | {v["p99"]:.1f} |'
                      for name, v in [('Original', original), ('Query-global', global_v), ('Pair-specific', pair)])
    global_saving = h['global_coordinate_savings_fraction']['decimal'] * 100
    pair_saving = h['pair_coordinate_savings_fraction']['decimal'] * 100
    share = h['global_fraction_of_pair_headroom_removed']['decimal'] * 100
    f_low, f_high = [b2['rows'][i]['break_even_rejection_fraction']['decimal'] * 100 for i in (0, -1)]
    qps500, qps100 = b3['break_even_qps_at_500us']['decimal'], b3['break_even_qps_at_100us']['decimal']
    text('DECISION.md', f'''
# Decision: NO_GO_LIMITS_THESIS

**The frozen near-saturation thesis is rejected on the complete fixed population.**
The primary pair/original ratio is {h['pair_over_original']['decimal']:.12f},
below 0.40; query-global saves {global_saving:.6f}%, above 40%.
Both independently trigger the original B1 NO_GO rule. The guarded and ordinary
counts agree for every pair, so the decision is not a floating-order artifact.
No thresholds were relaxed, and B2 is not used to manufacture an algorithm.

## Q1. How far is the current progressive count from the pair oracle?

| Free coordinate certificate | Mean dims/object | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
{table}

There are 32,000,000 pairs and 6,590 true hits. The primary denominator is
the original ideal per-coordinate mean, **167.29161475**, not the
checkpoint-source-equivalent **253.707194**. Pair-specific counts save {pair_saving:.6f}%
of that ideal coordinate count. This is LARGE_HEADROOM in the restricted family,
not measured traffic, an implementable oracle, or a universal search lower bound.

## Q2. Can one query-global order remove most remaining coordinate headroom?

Yes **in the free, oracle-fitted diagnostic**: mean {global_v['mean']:.8f} dims,
{global_saving:.6f}% fewer than original, removing {share:.6f}% of the gap between
original and pair oracle. The hypothesis that most remaining count headroom is
unavoidably pair-specific is contradicted on this pool. However, the order is
fitted with all nonhit labels and all 960 contributions. Its construction is
O(ND), has no held-out evaluation, and is not a cheap online policy. Noncontiguous
access, sectors, exact-score reconstruction and update/runtime costs are untested.
BOND/PDX already cover related query-aware dimension-ordering mechanisms.

## Q3. What rejection rate does compact metadata need?

In the **conditional eager-metadata plus complete-raw-fallback model**,
1–256 B/vector requires **{f_low:.6f}%–{f_high:.6f}%** all-object safe rejection
just for equality with 1,014,828,776 source B/query. Strict improvement requires
strictly higher rejection. The claimed >=90% barrier is therefore
**B2_BARRIER_NOT_SUPPORTED**. This is not a realizable representation frontier,
not proof that small metadata easily produces a large gain, and not an actual
physical-byte lower bound. True-hit score coordinate reads are already included
in (1-f); control, output and maintenance remain unknown rather than free.

## Q4. Where is the online reuse break-even region?

For the ideal uncapped timer-on-first-query Poisson model, equality requires
lambda*W = 3840000000/1014828776 - 1, approximately
{qps500/2000:.12f}. At 500 us the rate is **{qps500:.9f} qps**; at 100 us it is
**{qps100:.9f} qps**. Exact fractions, not these rounded displays, drive gates.
At 5000 qps/500 us, ideal source is 1.097142857 GB/query, still above keeper.
Thus B3_FROZEN_REGION_BARRIER holds in the specified region. Outside it, the
algebra has winning regions, which are retained. No longer window, scheduler,
GPU service or complete SLA is executed or validated. This is not a bound on
every online batching strategy or dynamic workload.

## Q5. Can historical results be explained by one universal boundary?

No. Byte reduction is a useful accounting lens, not a demonstrated unavoidable
frontier. The static progressive mechanism genuinely reduced historical
all-kernel DRAM by 71.0181% and Host-ready range latency by 55.6625%
(2.255428x), but source bytes and DRAM are distinct. The bounded dynamic A
service ratio was 0.855934141 and missed its 0.85 admission gate; B was not run.
Contiguous tree packing and later sector/packing models show positive headroom.
INT8 has no population/GPU result. Batching has only the scoped synthetic-model
failure. These are not interchangeable proofs that every alternative fails.

## Separate dispositions and next action

- Implementation: the complete CPU diagnostic is correctness-qualified on this
  fixed workload: all 32M full authority scores match bitwise; no guarded false
  rejection; all reference/data hashes preserved.
- Mechanism: free query-aware ordering leaves large coordinate-count headroom.
  **No actual new algorithm, DRAM reduction or end-to-end speedup is admitted.**
- Thesis: **NO_GO_LIMITS_THESIS**; no lower-bound claim, paper outline, kernel,
  tuning sweep, new layout, batch execution or final GPU validation follows.
- Reopen only through a separately authorized, novelty-audited mechanism with
  charged ordering/metadata/update/output and decisive same-contract evidence.
  Do not rescue this thesis by dropping counterexamples or changing thresholds.

Confidence is high for the finite-population count decision and exact algebra;
generalization beyond these 32 range queries, one radius and one static GIST1M
snapshot remains unknown. Dynamic search in the title is the proposed thesis,
not a newly measured dynamic experiment.
''')
    text('design_space/BOUNDARY_SUMMARY.md', '''
# Source accounting is useful; near-saturation is falsified

| Redundancy | Mechanism / module | Observed or conditional effect | End-to-end status |
| --- | --- | --- | --- |
| Full reads of already certifiable nonhits | Progressive prefix rejection / compaction | Historical checkpoint payload1.014828776GB; measured DRAM1.119337016GB | Static exact range Host-ready2.255428x; not a full dynamic-workflow factor |
| Poor coordinate order | Free query-global and pair ordering / CPU diagnostic | Full32M counts44.01871025 and15.81336353125 vs167.29161475 | UNKNOWN: construction and physical execution not implemented |
| Scattered tree candidates | Offline contiguous block ownership | Block256 reach improves to76.5477%/63.8589%, not universal failure | UNKNOWN: no executed layout timing |
| Reading raw after a compact filter | Metadata / complete fallback | Conditional equality needs73.5982%–80.2388% rejection | UNKNOWN: no representation is realized by algebra |
| Repeated high-precision reads | Frozen INT8 sidecar / certified refinement | 0.968GB first-pass model; fallback erodes4.61445% ideal source margin | NOT_RUN: no population or GPU qualification |
| Repeated database scans | Window/cap batching / shared version | Frozen-region ideal reuse remains above keeper; other analytic regions can win | UNKNOWN: service/SLA/update costs excluded |

Bytes on the map are conditional source payload, not NCU traffic. The x-axis
uses extra indexed payload beyond common raw FP32 storage; reusable query
workspace and update maintenance are separate table fields. Null/unknown costs
are not plotted as zero or used to assert dominance. A two-axis plot cannot
collapse heterogeneous maintenance costs into one meaningful numeric axis.

Retained positive counterexamples: sector S1's conditional904744352B/query;
packed P1's conditional817666504B/query; exact lossless ownership success even
though its source-byte gate failed. These do not establish an executable faster
system, but prevent cherry-picking historical NO_GOs into an impossibility claim.
''')
    text('CLAIM_EVIDENCE.md', '''
# Claim–evidence ledger

All new population evidence: parent01ad50f,2026-10-14,CPU diagnostic host,
32 original queries x GIST1M/D960 initial snapshot; no GPU process.
Data/reference/source identities and raw hashes are in evidence/.

| ID | Exact scoped claim | State | Evidence / denominator | Counterevidence and allowed wording |
| --- | --- | --- | --- | --- |
| L1 | A free sorted pair certificate averages15.81336353125 coordinates | measured | PAIR_ORACLE.json;complete32M pairs, includes6590 hits charged960 | Restricted partial-sum diagnostic only; construction/full scores free, not physical lower bound |
| L2 | One free query-global order averages44.01871025 coordinates | measured | QUERY_GLOBAL_ORACLE.json;all nonhit means, same32M population | Oracle labels, O(ND) construction and no held-out generalization; not an online algorithm |
| L3 | Current ideal count is not saturated under the frozen B1 gate | rejected | HEADROOM.json;pair/original0.094525739111<0.40;global savings73.6874%>40% | Rejects near-saturation thesis, not progressive's historical GPU benefit |
| L4 | The >=90% metadata barrier does not follow from the frozen formula | theoretical | BREAK_EVEN.json;1–256B/vector needs73.5982%–80.2388% equality rejection | Eager metadata/full-raw fallback only; actual achievable representation unknown |
| L5 | Frozen Poisson reuse region cannot beat the range-source reference | theoretical | BREAK_EVEN_SURFACE.json;best corner5000qps/500us1.097142857GB | Not a universal scheduler, complete SLA, or mixed/dynamic result; outside-region counterexamples retained |
| L6 | Progressive previously reduced static range Host-ready latency2.255428x | measured | Parent GPU Gate2 same-campaign six paired processes;2.57311653125/1.14085521875ms | Historical, not new; not dynamic100k workflow or all-query/domain claim |
| L7 | All32M new complete authority scores match existing references | measured | QUALIFICATION and full results;0 bit mismatch and0 guarded false rejection | Correctness of this CPU diagnostic; no new kernel/sanitizer or GPU gate |
| L8 | Universal GPU information/traffic lower bound and limits-paper novelty | unknown | No evidence; restricted prior-art models do not transfer automatically | NOT_ADMITTED; no paper, no arbitrary-index or representation impossibility |

Implementation, mechanism and thesis decisions are separate. A theoretical
opportunity does not establish realizability, and an unexecuted mechanism is
not relabeled an empirical failure. Negative evidence retains its workload,
keeper, added unknown costs, gate, and reopen condition in DECISION.md.
''')
    text('README.md', f'''
# Exact GPU search limits Gate1: NO_GO_LIMITS_THESIS

Complete CPU evaluation of **32,000,000 fixed query–object pairs** rejects
the proposed near-saturation thesis. No GPU, manuscript or production change.

| Certificate order | Mean ideal coordinates/object |
| --- | ---: |
| Original | {original['mean']:.8f} |
| Query-global oracle | {global_v['mean']:.8f} |
| Pair-specific oracle | {pair['mean']:.11f} |

These are free-construction references within a restricted partial-sum family,
not achievable traffic or speedups. The ordinary and guarded counts coincide.
The checkpoint-source-equivalent denominator is253.707194, separately retained.

- [Decision and five required answers](DECISION.md)
- [Numerical scope](NUMERICS.md), [prior art](PRIOR_ART_LIMITS.md)
- [Unified systems table](design_space/SYSTEMS_TABLE.json), [causal chain](design_space/BOUNDARY_SUMMARY.md)
- [Claim–evidence ledger](CLAIM_EVIDENCE.md), [reproduction](REPRODUCE.md)
- [Figures and captions](figures/README.md)

B2's >=90% barrier is unsupported by its own conditional algebra. B3 retains
a barrier only in the frozen Poisson collection region. Neither rescues B1.
The earlier static progressive speedup remains valid within its old contract;
the dynamic workflow is not admitted as near-optimal. Dataset, complete raw
arrays, placement and third-party paper snapshots stay outside Git.
''')
    print('PASS: decision, counterexamples and unknown maintenance preserved')


if __name__ == '__main__':
    main()
