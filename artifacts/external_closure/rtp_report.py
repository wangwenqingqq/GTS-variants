#!/usr/bin/env python3
"""Render measured R/T/P tables without combining historical ratios."""
import argparse,json
from pathlib import Path
import numpy as np

def render(x):
    assert x['status']=='MEASURED_FIXED_SHORT_RTP' and len(x['rows'])==18
    out=['# Direct cumulative and strengthened-reference R/T/P results','',
        '**All 18 fresh short-workflow processes passed complete ordered output and state checks.**',
        'This is internal evidence, not an external static or dynamic ranking.','',
        'Original FP32 GIST **N=1,000,000, D=960, B1, K8**, radius bits `0x3f34a3d8`.',
        'Each trace contains 336 events: 128 range, 128 kNN, 40 inserts, 40 deletes,',
        'and two real threshold-10 rebuilds. R uses common numerical/safety repairs,',
        'not untouched original GTS. T and P both use TILED construction.','',
        '| Mode | Range | kNN | Build |','|---|---|---|---|',
        '| R | Staged common-repair reference | FULL | NODE |',
        '| T | Same staged reference | FULL | TILED |',
        '| P | PAR_STRONG | FULL | TILED |','',
        '## Direct continuous workflow result','',
        '| Comparison | Paired geometric reference/candidate |95% paired interval|Wins|Time reduction|',
        '|---|---:|---:|---:|---:|']
    for name,v in x['comparisons']['trace_ms'].items():
        out.append(f"|{name}|{v['ratio']:.6f}x|[{v['CI95'][0]:.6f}, {v['CI95'][1]:.6f}]|{v['wins']}/6|{v['time_reduction_percent']:.2f}%|")
    out += ['', 'Ratios above 1 favor the denominator candidate. These are directly paired',
        'measurements, not the product of historical 1.684797x and 8.029943x.',
        'Continuous time includes complete Host-ready answers, serialized update ACKs,',
        'buffer preparation, compaction/construction, safe-bound refit, mirror/PAR',
        'refresh where required, and final service-device release/synchronization.',
        'Initial setup, cloned 19-event warmup, parsing and context initialization are',
        'separately recorded. Host answer allocation and complete D2H delivery are',
        'included; later client consumption/release of retained Host answers and',
        'file serialization are excluded. No leak-clean or production-ready claim.','',
        '|Round / order|R seconds|T seconds|P seconds|','|---|---:|---:|---:|']
    for i in range(1,7):
        rows={r['mode']:r for r in x['rows'] if r['round']==i}
        out.append(f"|{i} / {rows['R']['order']}|"+'|'.join(f"{rows[m]['trace_ms']/1000:.6f}" for m in 'RTP')+'|')
    out += ['', '## Setup-inclusive sensitivity (measured setup + continuous trace)','',
        '|Comparison|Paired ratio|95% interval|','|---|---:|---:|']
    for name,v in x['comparisons']['setup_plus_trace_ms'].items():
        out.append(f"|{name}|{v['ratio']:.6f}x|[{v['CI95'][0]:.6f}, {v['CI95'][1]:.6f}]|")
    out += ['', 'This second denominator still excludes warmup, parsing and initial context;',
        'it is not fresh-process wall time. The JSON includes every raw setup/warmup,',
        'marginal ratio, p10/median/p90, per-process tail latency and order stratum.','',
        '## Attribution boundaries','',
        '|Process diagnostic, median seconds|R|T|P|','|---|---:|---:|---:|']
    for label,fn in [('Range ACK sum',lambda r:r['ack']['range']['sum_ms']/1000),('kNN ACK sum',lambda r:r['ack']['knn']['sum_ms']/1000),
        ('Inclusive rebuild sum',lambda r:r['rebuild_inclusive_ms']/1000),('Trace CPU user',lambda r:r['cpu_user_s']),('Final device service release',lambda r:r['final_release_ms']/1000)]:
        out.append('|'+label+'|'+'|'.join(f"{np.median([fn(r) for r in x['rows'] if r['mode']==m]):.6f}" for m in 'RTP')+'|')
    out += ['', 'Inclusive rebuild and component intervals overlap: never sum this table to',
        'derive a speedup. R/T measures construction mapping under staged range;',
        'T/P measures PAR organization with both constructions strengthened; R/P is',
        'the direct final combination. CPU user time includes CUDA polling/control,',
        'not proof of CPU distance computation. This campaign does not isolate',
        'coalescing, traffic reduction, launch removal or numerical work as the sole',
        'cause; no new NCU/NSYS evidence was collected.','',
        '## Validation, statistics and remaining scope','',
        '- One unchanged binary serves all three modes. Five T bridge processes pass:',
        '  bounded full workflow, million-row rebuild prefix, memcheck/racecheck/synccheck.',
        '- All 256 query payloads/process and all 336 state transitions are byte/state',
        '  identical to the previously exhaustive ordered-FP64-qualified parent.',
        '- Six permutations balance each method pair 3/3. Bootstrap 20,000, seed 2026101002;',
        '  speedup requires lower 95% bound>1, at least5/6 wins and both strata>1.',
        '  These intervals describe repeat-run variation on fixed observed queries,',
        '  not dataset/query-distribution generalization.',
        '- Same isolated single RTX PRO 6000 Blackwell GPU, CUDA 13.1/SM120; shared',
        '  CPU host/NUMA placement, foreign jobs untouched, no clock/power changes.',
        '- The original 96 B context-symbol full-leak boundary remains unresolved.',
        '- New primaries 18/102; cumulative GPU qualifiers 25/32. External static B',
        '  still has zero new primaries. Earlier native Faiss kNN counterevidence and',
        '  GPU_TREE membership blocker remain; no external superiority is inferred.',
        '- No new kernel optimization, precision, dataset,100k/1B, long campaign or',
        '  manuscript publication. Standard tiling is not claimed as new research.','',
        'See [raw paired evidence](evidence/RTP_RESULTS.json), [contract](RTP_CONTRACT.json),',
        '[attempts](RTP_ATTEMPTS.md), and [remaining external gates](NEXT_GATES.md).']
    return '\n'.join(out)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();a.output.write_text(render(json.loads(a.input.read_text())))
