#!/usr/bin/env python3
"""Bind one perturbed attribution capture to exact keeper output and its measured NVTX span."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,sqlite3
from pathlib import Path
from common import outside_repo
from qualify import cpu
HERE=Path(__file__).resolve().parent

def analyze(a):
    f=a.raw;receipt=json.loads((f/'guard/receipt.json').read_text());assert receipt['runtime_valid'] and receipt['stop_reason'] is None and receipt['exit_code']==0
    registration=json.loads(a.registration.read_text());build=json.loads((a.build/'REGISTERED.json').read_text())
    assert registration['budget']==1 and registration['parent_sha256']==cpu.sha(a.build/'REGISTERED.json')
    assert registration['binary_sha256']==json.loads((a.build/'BUILD.json').read_text())['binary_sha256']==cpu.sha(a.build/'bin/target')
    assert all(cpu.sha(a.build/'source'/name)==value for name,value in build['sources'].items())
    assert build['parent_prepared_sha256']==json.loads((HERE.parent/'build_distance_tiles/evidence/QUALIFICATION.json').read_text())['source']['prepared_sha256']
    command=json.loads((f/'guard/command.json').read_text());assert receipt['command']==command
    at=command.index(str(a.build/'bin/target'));assert command[at+1:]==[str(a.data),str(a.events),'2','0.705625057220459',str(f/'out'),'8']
    from pe_binding import validate_target
    validate_target(a.events);assert cpu.sha(a.data)==cpu.validate.TARGET_DATA_SHA256
    assert receipt['binary_sha256']==cpu.sha(command[3])  # Guard records the nsys launcher.

    assert not json.loads((f/'guard/before.json').read_text())['apps'] and not json.loads((f/'guard/after.json').read_text())['apps']
    assert all(not x['foreign'] for x in json.loads((f/'guard/checks.json').read_text()))
    gold=json.loads((HERE/'evidence/RTP_RESULTS.json').read_text());pins=next(r['output_hashes'] for r in gold['rows'] if r['label']=='round_1_P')
    for warm in ('','.warmup'):
        for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
            p=Path(str(a.reference)+warm+suffix);assert cpu.sha(p)==pins[p.name]
            assert (f/('out'+warm+suffix)).read_bytes()==p.read_bytes()
    c=sqlite3.connect(f/'cost.sqlite');spans=c.execute("select start,end from NVTX_EVENTS where text='native.trace' order by start").fetchall();assert len(spans)==2;lo,hi=spans[1]
    kernels=[dict(name=n,calls=count,total_ms=ns/1e6,mean_ms=ns/count/1e6) for n,count,ns in c.execute('select s.value,count(*),sum(k.end-k.start) from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on k.demangledName=s.id where k.start>=? and k.end<=? group by k.demangledName order by sum(k.end-k.start) desc',(lo,hi))]
    runtime=[dict(name=n,calls=count,inclusive_ms=ns/1e6) for n,count,ns in c.execute('select s.value,count(*),sum(k.end-k.start) from CUPTI_ACTIVITY_KIND_RUNTIME k join StringIds s on k.nameId=s.id where k.start>=? and k.end<=? group by k.nameId order by sum(k.end-k.start) desc',(lo,hi))]
    counter=json.loads((f/'out.cost.json').read_text());assert counter['d']==960 and counter['distinct_parameter_pairs']==1
    return dict(status='DIAGNOSTIC_ONLY',exact_keeper_warmup_and336_payloads=True,measured_trace_span_ns=[lo,hi],diagnostic_trace_ms=(hi-lo)/1e6,counter=counter,
        inferred_directed_multiplications=counter['radius_upper_calls']*963,kernels=kernels,runtime=runtime,
        radius_isolated_time='unknown; containing kernel includes distances, synchronization, traversal and diagnostic atomic',
        scope='one extra atomic per active parent CTA; NSYS perturbed timing, not primary denominator or hoist speedup',
        hashes={p.name:cpu.sha(p) for p in (f/'cost.sqlite',f/'cost.nsys-rep',f/'out.cost.json',f/'guard/receipt.json')},checker_sha256=cpu.sha(__file__),binary_sha256=registration['binary_sha256'],registration_sha256=cpu.sha(a.registration),build_registration_sha256=cpu.sha(a.build/'REGISTERED.json'),sources=build['sources'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('raw','reference','output','build','registration','data','events'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output=outside_repo(a.output);assert not a.output.exists();cpu.save(a.output,analyze(a))
