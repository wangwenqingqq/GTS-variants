#!/usr/bin/env python3
"""Render the frozen short dynamic evidence; no timing or GPU work."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,statistics as st
from pathlib import Path

def render(x):
    med=lambda method,key:st.median(r[key] for r in x['rows'] if r['method']==method)
    p=x['comparisons']['trace_ms'];lo,hi=p['CI95'];s=x['comparisons']['setup_plus_trace_ms']
    lines=['# Short dynamic P/E: measured negative result (2026-10-10)','',
        '**Decision: branch 2, one attributable cost question; no 10K expansion.**',
        f"Paired E/P = **{p['paired_geometric_E_over_P']:.6f}**, 95% process-bootstrap CI [{lo:.6f}, {hi:.6f}]; P wins **{p['P_wins']}/6**.",
        f"Equivalently, E is **{1/p['paired_geometric_E_over_P']:.6f}x faster** (reciprocal CI [{1/hi:.6f}, {1/lo:.6f}]).",'',
        '## Same service task, not identical arithmetic implementations','',
        'GIST: **1,000,000 vectors, 960 dimensions, FP32; B=1, K=8**. The immutable',
        '336 events contain 128 complete range queries, 128 kNN queries, 40 inserts',
        'and 40 exact-occurrence deletions. Radius 0.705625057220459. Final live N=1M.',
        'Each process additionally executes the same cloned 19-event / 8-query warmup',
        'and restores initial state. Requests are Host vectors and logical occurrence',
        'IDs, not backend-specific physical row numbers. Duplicates remain distinct.','',
        '* **P:** PAR_STRONG/FULL/TILED, threshold 10 and two measured rebuilds;',
        '  only Host request/ID adaptation. All 113 original GPU functions and 76,152',
        '  normalized instructions are identical to the admitted parent.',
        '* **E_ADAPT:** one live dense GPU vector allocation; Faiss 1.15.1 bfKnn with',
        '  native cached norms and cuVS L2Unexpanded complete range scan. Exact-instance',
        '  swap-last deletion, one-vector/norm insertion; no tree, forced rebuild,',
        '  second vector dataset or fixed-K postfilter. This is **not native Faiss',
        '  dynamic indexing**. E uses native FP32 arithmetic; P keeps ordered FP64.',
        '* Device: one RTX PRO 6000 Blackwell Server Edition, nominal 96 GB (97,887 MiB reported), CUDA 13.1,',
        '  driver 590.48.01, sm_120. Two-sided device/NUMA guards passed. GPU clocks',
        '  and power were not modified; other host users were not stopped.','',
        '## Primary complete workflow','',
        'Continuous Host request input through complete IDs/fields and update ACKs,',
        'including ID mapping, actual copies, maintenance, state publication, final',
        'live-ID manifest and service resource release. Full outputs remain in client',
        'memory. Client subsequent consumption/destruction and disk persistence are',
        'outside. Parse/context/warmup are separately retained in JSON, not added to',
        'the primary denominator. E native-squared validation observations are charged.','',
        '| Six-process median | P | E_ADAPT |','|---|---:|---:|']
    for title,key,scale in [('Trace including final release (s)','trace_ms',1000),('Service setup (s)','setup_ms',1000),
        ('Service setup + trace (s)','setup_plus_trace_ms',1000),('Final release (ms)','release_ms',1),
        ('Trace CPU user (s)','cpu_user_s',1),('Trace CPU system (s)','cpu_system_s',1)]:
        lines.append(f'| {title} | {med("P",key)/scale:.6f} | {med("E",key)/scale:.6f} |')
    lines+=['',f"Service setup+trace E/P = {s['paired_geometric_E_over_P']:.6f}, CI [{s['CI95'][0]:.6f}, {s['CI95'][1]:.6f}].",
        '**This secondary sensitivity is not full program wall time:** E reserves its',
        'client answer/operation ledger between its setup and trace timers; P reserves',
        'client metadata within setup. Both exclude this preparation from primary trace.',
        'Do not present this asymmetry as an exact full-preparation comparison.','',
        '### Raw process order (no replacement or selective rerun)','',
        '| Pair | Order | P trace (ms) | E trace (ms) | E/P |','|---|---|---:|---:|---:|']
    for i in range(1,7):
        a,b=(next(r for r in x['rows'] if r['round']==i and r['method']==m) for m in ('P','E'))
        lines.append(f"| {i} | {a['order']} | {a['trace_ms']:.6f} | {b['trace_ms']:.6f} | {b['trace_ms']/a['trace_ms']:.6f} |")
    lines+=['',f"Order strata: PE {p['order_strata']['PE']:.6f}; EP {p['order_strata']['EP']:.6f}.",
        'Estimator: geometric paired E/P, 20,000 process resamples, seed 2026101010.',
        'Only six pairs; this CI describes this short run, not sustained/general behavior.','',
        '### Operation ACKs (ms)','',
        'Each cell is a median across six processes. Quantiles are per-process event',
        'quantiles, then median; they are not a pooled latency distribution. Independently',
        'taken component medians must not be added to construct a new total.','',
        '| Method / operation | ACK sum | Event p50 | Event p95 | Event p99 |',
        '|---|---:|---:|---:|---:|']
    for method in ('P','E'):
        for op in ('range','knn','insert','delete'):
            records=[r['ack'][op] for r in x['rows'] if r['method']==method]
            values=[st.median(r['sum_ms'] for r in records)]+[st.median(r['p50_p95_p99_ms'][i] for r in records) for i in range(3)]
            lines.append('| '+method+' / '+op+' | '+' | '.join(f'{v:.6f}' for v in values)+' |')
    lines+=['','P performs two actual rebuilds; E performs zero. E performs 40 inserted-row',
        'norm updates plus initial norms, 20 nontrivial swap deletions, 153,600 inserted',
        'H2D bytes and 76,880 swap D2D bytes per measured trace. P Host request vector',
        'uploads total 1,136,640 bytes; other internal copies remain charged.',
        f"P median inclusive rebuild ACK sum: {med('P','rebuild_inclusive_ms'):.6f} ms (overlaps insert ACKs).",'',
        '### Memory and sampling limits','',
        '| Method | Median whole-process sampled peak (MiB) | Min–max across processes (MiB) |',
        '|---|---:|---:|']
    for method in ('P','E'):
        values=[r['whole_process_200ms_samples']['peak_device_MiB'] for r in x['rows'] if r['method']==method]
        lines.append(f'| {method} | {st.median(values):.0f} | {min(values):.0f}–{max(values):.0f} |')
    mem=lambda method,key:[r['memory'][key] for r in x['rows'] if r['method']==method]
    pb=mem('P','sampled_device_peak_bytes');eb=mem('E','device_used_built_bytes')
    lines+=['','These device-used samples are every 200 ms over the **whole process**, including',
        'warmup/setup/context, and can miss true peaks. They are not owned-allocation',
        f'peaks or measured-trace-only peaks. E service-built snapshot median is {st.median(eb):,.0f}',
        f'bytes (range {min(eb):,}–{max(eb):,}); it excludes later lazy query workspace.',
        'Its shared vector/norm storage is 3,840,153,600 / 4,000,160 bytes.',
        f'P in-service sampled peak median is {st.median(pb):,.0f} bytes',
        f'(range {min(pb):,}–{max(pb):,}). E retains 873,824 client result bytes including native',
        'squared fields; P output capacity is 828,672 bytes. Context/library allocations',
        'remaining at service release are not represented as leaked service vectors.','',
        '## Qualification, recovery, and evidence identity','',
        '* 11 actual qualification GPU processes: bounded P/E, each method under',
        '  memcheck/racecheck/synccheck, target P/E, and E empty/<K tail. The reserved',
        '  twelfth qualifier was unused. Sanitizer scope is bounded, not a proof of',
        '  arbitrary size/concurrency; the inherited 96-byte context-symbol leak',
        '  remains separately unresolved.',
        '* First P bounded process was correct; checker expected measured-only builds',
        '  but read cumulative warmup+measured count (4 instead of 2). Preserved failure',
        '  and independent complete-output recheck; explicit recovery continued only',
        '  the remaining ten qualifiers. **No first-sample rerun.**',
        '* All 12 formal processes passed, each with 256 measured queries / 54,614',
        '  output items and complete warmup payloads. P members/required kNN order/field bits are',
        '  exact; E exact range membership, complete tie-aware K8, native squared and',
        '  field tolerance 5e-5 scaled by max(1, reference squared). No score correction.',
        '* Bounded independent exhaustive CPU checks plus target binding to the pinned',
        '  prior exhaustive-qualified reference. Offline verification independently',
        '  rebinds all 23 receipts, sources, binaries, full outputs, states and exact',
        '  336-event identity. Old 72 static / 18 R/T/P observations are not rerun.',
        '* One separately budgeted, output-verified NSYS/counter diagnostic is not',
        '  included in these latency statistics. No long workload was launched.','',
        'Evidence: [all process results and bindings](evidence/PE_RESULTS.json),',
        '[raw private-file hashes](evidence/PE_RAW_MANIFEST.json),',
        '[GPU identity](evidence/PE_GPU_IDENTITY.json),',
        '[diagnostic](evidence/PE_DIAGNOSTIC.json),',
        '[frozen contract](PE_CONTRACT.json), [decision and next gate](PE_DECISION.md).','',
        'Current public checks are hardened after execution. The measured source hashes',
        'are retained separately; use `git apply --unidiff-zero PE_EXECUTED_SOURCES.patch` in a disposable copy',
        'to reconstruct the resumed executor, then apply PE_FIRST_CHECKER.patch with the same option for the original',
        'stopped checker. These patches are provenance, not recommended execution modes.',
        'The portable E build helper was added after measurement; the exact measured',
        'compiler/dependency recipe remains in the private hashed build registration.','']
    return '\n'.join(lines)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();a.output.write_text(render(json.loads(a.input.read_text())))
