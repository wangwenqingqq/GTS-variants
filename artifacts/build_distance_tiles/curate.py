#!/usr/bin/env python3
"""Whitelist aggregate proofs and render the same frozen result without raw vectors."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def med(cost,mode,fn):return float(np.median([fn(x) for x in cost if x['mode']==mode]))

def render(result,qualification,sass):
    paired=result['paired'];raw=result['rows'];cost=result['cost_rows'];by={r['label']:r for r in raw}
    verdict='passed the frozen internal short-workflow gate' if result['internal_win_gate_passed'] else 'did not pass the frozen internal short-workflow gate'
    lines=['# Build-distance tiling: fixed-workflow evidence','',
        f"**B1 {verdict}: paired B0/B1 {paired['ratio']:.6f}×,95% CI [{paired['CI95'][0]:.6f},{paired['CI95'][1]:.6f}].**",
        'This is an engineering improvement over freshly remeasured PAR+FULL with the original build mapping, not over untouched GTS, CPU trees, IVF or CAGRA.',
        '','## Task and denominator','',
        'Original FP32 GIST **N1M,D960,B1,K8**,radius bits0x3f34a3d8.336 events:128 range+128 kNN+40 insert+40 delete,2 actual occupancy10 rebuilds.',
        'Twelve fresh primary processes,six alternating direction-balanced pairs. Continuous Host-ready/ACK time includes full outputs,buffer work,all maintenance and final owned-service release. Setup and cloned warmup are separate; no profiler denominator.',
        '', '| Round/order | B0 seconds | B1 seconds | B0/B1 |','|---|---:|---:|---:|']
    for i,order in enumerate(('B0B1','B1B0')*3,1):
        a=by[f'round_{i}_B0'];b=by[f'round_{i}_B1'];lines.append(f"| {i}/{order} | {a['trace_ms']/1000:.6f} | {b['trace_ms']/1000:.6f} | {a['trace_ms']/b['trace_ms']:.6f}× |")
    lines += ['',f"Candidate wins **{result['candidate_wins']}/6**. Order strata: B0-before {result['order_strata']['B0B1']:.6f}×; B0-after {result['order_strata']['B1B0']:.6f}×. Marginal median ratio {result['marginal_median_ratio']:.6f}×.",
        f"Paired elapsed-time reduction is {100*(1-1/paired['ratio']):.3f}%. The paired bootstrap estimates repeat-run variation on this one fixed trace, not variation across datasets or100k events.",
        '', '## Cost boundaries','',
        'Every cell is independently the median of its six process values. Rebuild is nested within insertion ACK; build/refit/refresh/repack are nested inside maintenance. **Do not sum these rows or subtract medians to create a denominator.**',
        '', '| Boundary | B0 | B1 |','|---|---:|---:|']
    fields=[('Continuous workflow,s',lambda x:by[x['label']]['trace_ms']/1000),('Initial setup,s',lambda x:x['initial_setup_ms']/1000),
        ('Setup+trace,s',lambda x:x['setup_plus_trace_ms']/1000),('Cloned warmup,s',lambda x:x['warmup_ms']/1000),
        ('128 range ACKs,s',lambda x:x['operations']['range']['sum_ms']/1000),('128 kNN ACKs,s',lambda x:x['operations']['knn']['sum_ms']/1000),
        ('40 insertion ACKs,s',lambda x:x['operations']['insert']['sum_ms']/1000),('40 deletion ACKs,s',lambda x:x['operations']['delete']['sum_ms']/1000),
        ('Two rebuilds,inclusive,s',lambda x:sum(x['rebuilds_ms'])/1000),
        ('Build inside two rebuilds,s',lambda x:next(s['inclusive_host_ms'] for s in x['stages'] if s['name']=='rebuild.construct')/1000),
        ('Active numeric refit,s',lambda x:sum(x['numeric']['refresh_ms'][1:])/1000),
        ('Active PAR plan refresh,s',lambda x:sum(r['ms'] for r in x['region']['refresh_rows'][1:])/1000),
        ('Active kNN mirror repack,s',lambda x:sum(x['live']['refresh_ms'][1:])/1000),
        ('Trace CPU user,s',lambda x:x['cpu_user_s']),('Trace CPU system,s',lambda x:x['cpu_system_s']),
        ('Sampled device peak,GiB',lambda x:x['sampled_device_peak_bytes']/2**30),('Host answer capacity,MiB',lambda x:x['host_output_capacity_bytes']/2**20),
        ('Per-process insertion p99,ms',lambda x:x['operations']['insert']['p50_p99_ms'][1]),
        ('Per-process deletion p99,ms',lambda x:x['operations']['delete']['p50_p99_ms'][1])]
    for name,fn in fields:lines.append(f'| {name} | {med(cost,"B0",fn):.6f} | {med(cost,"B1",fn):.6f} |')
    lines += ['', 'Insertion/deletion p99 is a descriptive percentile of only40 operations per process, not a production-tail guarantee. Device peaks are sampled total used memory, not allocator-exact peaks. Setup+trace excludes parse/context/warmup/disk serialization; the raw receipts retain those boundaries.',
        '','## Mechanism and exactness','',
        f"Nine paired qualification cases cover {sum(x['builds'] for x in qualification['layers'])} build states and {sum(x['layers'] for x in qualification['layers'])} layers per mode. All {sum(x['defined_files'] for x in qualification['layers'])} complete defined-state files per mode match bitwise, including keys,pids,sort order,occupied topology and refit bounds.",
        'The original midpoint pivot and node_slot composite keys remain; each object has one writer and tile0/thread0 alone writes each splitting-node pivot metadata. The root grid changes1→1954 CTAs for N1M; no task array,allocation,copy or new primary fence is introduced.',
        f"All {sass['preserved_functions']} original GPU functions/{sass['preserved_instructions']:,} normalized instructions are identical. The only added function has {sass['added_instructions']:,} static instructions. This is static identity,not dynamic work or a coalescing/traffic counter.",
        'Static resources: original42 versus tiled52 registers; both retain47528-byte stack frame and20-byte reported shared allocation; zero compiler spill stores/loads. The stack is not evidence of zero local traffic. No occupancy or sector/byte-saving claim is made.',
        'Four ordinary access/sync sanitizer processes report zero errors/hazards. Every primary process has256 complete query outputs/54614 ID-field pairs with actual parent exhaustive-quality bindings; warmup and operation states also match. Hardened replay requires complete file families and rejects changed keys,geometry,tail bytes and missing qualification evidence.',
        '','## Mainline and strongest caveats','',
        'Avoidable shallow serialization → explicit object-tile ownership → build_distance_tiles → identical work/state with larger independent grid → measured internal complete-workflow result. This is not repeated-distance elimination and ordinary CTA partitioning alone is not novel.',
        'Trace-scoped CPU user time is measured separately. Its change is consistent with the earlier diagnostic waiting attribution,but this campaign has no new CPU polling or arithmetic profiler evidence; CPU/GPU overlap is not additive.',
        'The old1.684797× A→PAR result is preserved separately,not multiplied into this campaign. Native GPU Flat and CPU Flat counterevidence and unresolved MVPT/GPU_TREE qualification remain in the baseline tables. No new external dynamic or formal CPU/GPU ranking is established.',
        'Inherited96B/seven managed context-symbol full-leak issue remains unresolved. No leak-clean,production/default,1B/100k or long-matrix admission. Next: keep this as the strengthened internal comparator and separately close qualified external static/dynamic and sustained-workflow gates.']
    return '\n'.join(lines)+'\n'


def curate(a):
    out=a.output;out.mkdir(parents=True,exist_ok=False);e=out/'evidence';e.mkdir()
    q=read(a.qualification/'QUALIFICATION.json');recheck=read(a.recheck);result=read(a.primary/'RESULTS.json');sass=read(a.sass_delta)
    assert q['passed'] and recheck['passed'] and q['evidence_binding']==recheck['evidence_binding']
    assert result['qualification_sha256']==sha(a.qualification/'QUALIFICATION.json') and result['binary_sha256']==q['binary_sha256']
    assert sass['passed'] and sass['candidate_normalized_sha256']==q['source']['normalized_SASS_sha256']
    for name,value in [('QUALIFICATION.json',q),('QUALIFICATION_RECHECK.json',recheck),('SOURCE_IDENTITY.json',q['source']),('SASS_DELTA.json',sass),('RESULTS.json',result)]:save(e/name,value)
    record=read(a.primary/'REGISTERED.json')
    safe={k:record[k] for k in ('stage','jobs','binary_sha256','contract_sha256','executed_driver_sha256','build_sha256','prepared_sha256','case_hashes','data_sha256','guard_sha256','admission_sha256')}
    safe['raw_registration_sha256']=sha(a.primary/'REGISTERED.json');save(e/'PRIMARY_REGISTRATION.json',safe)
    save(e/'BUILD.json',dict(binary_sha256=q['binary_sha256'],flags=['-std=c++17','-O3','-arch=sm_120','-lineinfo','-rdc=true','-Xnvlink=--ignore-host-info','--ptxas-options=-v'],
        hardware=dict(GPU='RTX PRO6000 Blackwell Server96GB',architecture='SM120',CPU='Xeon Gold6530',sockets=2,physical_cores=64,logical_CPUs=128),
        software=dict(CUDA='13.1',driver='590.48.01'),settings='unchanged; serialized idle single GPU and device-local NUMA; identifiers private',
        original_qualification_driver_sha256=read(a.qualification/'REGISTERED.json')['executed_driver_sha256'],original_qualification_analysis_sha256=q['source_analysis_sha256'],
        primary_analysis_sha256=result['analysis_sha256'],source_recipe_sha256=sha(Path(__file__).parent/'run.py'),
        primary_qualification_proof_sha256=sha(a.qualification/'QUALIFICATION.json'),hardened_recheck_sha256=sha(a.recheck)))
    (out/'REBUILD_E2E_RESULTS.md').write_text(render(result,recheck,sass))
    save(out/'MANIFEST.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('primary','qualification','recheck','sass-delta','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert __debug__;curate(a)
