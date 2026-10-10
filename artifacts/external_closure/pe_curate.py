#!/usr/bin/env python3
"""Publish a whitelist of bound results; retain raw receipts and data privately."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,csv,difflib,json,math
from pathlib import Path
from common import outside_repo
from qualify import cpu
from pe_results import paired
HERE=Path(__file__).resolve().parent

def curate(raw,out,proof_name="PE_RESULTS.json"):
    assert Path(proof_name).name==proof_name
    out=outside_repo(out);assert not out.exists()
    x=json.loads((raw/proof_name).read_text())
    assert x['binding']['passed'] and x['binding']['all23_runtime_receipts_bound']
    assert x['formal_GPU_processes']==12 and len(x['rows'])==12
    for metric,result in x['comparisons'].items():
        values=lambda method:[next(r[metric] for r in x['rows'] if r['round']==i and r['method']==method) for i in range(1,7)]
        recomputed=paired(values('E'),values('P'))
        for order,value in result['order_strata'].items():
            assert math.isclose(recomputed['order_strata'][order],value,rel_tol=1e-14,abs_tol=0)
        assert {k:v for k,v in recomputed.items() if k!='order_strata'}=={k:v for k,v in result.items() if k!='order_strata'}
    out.mkdir(parents=True)
    names=('status','shape','events','rows','comparisons','branch','registration_sha256','recovery_sha256',
           'formal_results_sha256','binaries','source_hashes','binding','actual_qualification_GPU_processes',
           'failed_checker_records_retained','formal_GPU_processes','limits')
    public={k:x[k] for k in names}
    public['complete_private_proof_sha256']=cpu.sha(raw/proof_name)
    public['limits']=x['limits']+[
        'setup+trace is service-setup sensitivity, not complete program wall time: E client ledger reserve falls between timers; primary trace is unchanged',
        'telemetry covers whole processes, including parse/context/warmup/setup/release; sampled peak is not exact allocator peak',
        'GPU clocks and power were not locked or altered; only the selected device was isolated, not the entire host']
    public['hardware']=dict(gpu='RTX PRO 6000 Blackwell Server Edition',nominal_memory_GB=96,reported_memory_MiB=97887,driver='590.48.01',cuda='13.1',architecture='sm_120',single_GPU=True)
    for r in public['rows']:
        p=raw/'campaign/primary/guards'/r['label']/'gpu.csv'
        records=list(csv.reader(p.open()))
        assert records and all(len(row)==8 for row in records)
        values=lambda i:[float(row[i]) for row in records if row[i].strip() not in ('N/A','[N/A]')]
        r['whole_process_200ms_samples']=dict(count=len(records),gpu_csv_sha256=cpu.sha(p),peak_device_MiB=max(values(1)),
            sm_MHz_minmax=[min(values(4)),max(values(4))],memory_MHz_minmax=[min(values(5)),max(values(5))],
            temperature_C_minmax=[min(values(6)),max(values(6))],power_W_minmax=[min(values(3)),max(values(3))])
        meta=json.loads((raw/'campaign/primary/outputs'/(r['label']+'.pe.json')).read_text())
        r['maintenance']={k:meta[k] for k in ('rebuilds','native_norm_updates_including_build','swap_deletes','inserted_H2D_bytes','swap_D2D_bytes') if k in meta}
        ops=list(csv.DictReader((raw/'campaign/primary/outputs'/(r['label']+'.ops.csv')).open()))
        r['maintenance']['actual_rebuild_events']=sum(float(op['rebuild_ms'])>0 for op in ops)
    cpu.save(out/'PE_RESULTS.json',public)
    for name,source in (('PE_DIAGNOSTIC.json','PE_DIAGNOSTIC_BOUND.json'),('PE_GPU_IDENTITY.json','P_GPU_IDENTITY.json')):
        value=json.loads((raw/source).read_text());value['private_source_sha256']=cpu.sha(raw/source)
        cpu.save(out/name,value)
    manifest={str(p.relative_to(raw)):cpu.sha(p) for folder in ('campaign','diagnostic','P_build','E_build','diagnostic_build')
              for p in (raw/folder).rglob('*') if p.is_file()}
    cpu.save(out/'PE_RAW_MANIFEST.json',dict(scope='Private original receipts, complete outputs, logical cases and bounded fixtures; no input data or runtime configuration published',files=manifest))
    # Preserve executed code without claiming later hardening ran during measurement.
    for filename,before,after in (('PE_EXECUTED_SOURCES.patch',HERE.parent.parent,raw/'repo'),
                                  ('PE_FIRST_CHECKER.patch',raw/'repo',raw/'first_executor')):
        patch=[]
        for name in sorted(x['source_hashes']):
            a=(before/name).read_text().splitlines(True);b=(after/name).read_text().splitlines(True)
            patch.extend(difflib.unified_diff(a,b,fromfile='a/'+name,tofile='b/'+name,n=0))
        (out/filename).write_text(''.join(patch))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--proof-name',default='PE_RESULTS.json');a=p.parse_args();curate(a.raw,a.output,a.proof_name)
