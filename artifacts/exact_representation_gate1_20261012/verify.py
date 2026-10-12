"""Exact public ship-set/hash, frozen-source and full-histogram recomputation gate."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from analyze import load,analyze,percentile
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
    manifest=load(root/'PUBLIC_MANIFEST.json')
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLIC_MANIFEST.json'}
    assert actual==set(manifest['files'])
    for name,h in manifest['files'].items():assert sha(root/name)==h,name
    c=load(root/'CONTRACT.json');records=load(root/'evidence/QUERY_RECORDS.json');a=analyze(records,c)
    assert a==load(root/'evidence/AGGREGATE.json')
    closure=load(root/'evidence/EXECUTION_CLOSURE.json');quality=load(root/'evidence/QUALITY.json');env=load(root/'evidence/ENVIRONMENT.json')
    assert closure['complete'] and closure['CPU_full_population_processes']==closure['CPU_workers']==1 and closure['GPU_starts']==quality['GPU_starts']==env['GPU_starts']==0
    assert quality['passed'] and quality['pairs']==32000000 and quality['full960_bit_mismatches']==quality['false_rejections']==0
    assert closure['contract_sha256']==sha(root/'CONTRACT.json') and closure['no_failed_primary_replacement']
    for name,h in closure['measurement_source_hashes'].items():assert sha(root/name)==h,name
    parent=load(root.parent/'non_padded_b1_baseline_20261012/evidence/INPUT_IDENTITY.json')
    assert closure['data_sha256']==c['workload']['data_sha256']==parent['data_sha256']
    assert c['workload']['qids']==parent['original_queries'] and closure['reference_hashes']==parent['reference_hashes']
    raw=load(root/'evidence/RAW_IDENTITY.json')['files'];assert len(raw)==64
    for q in c['workload']['qids']:
        assert raw[f'{q}.f64']['sha256']==closure['reference_hashes'][f'{q}.f64'] and raw[f'{q}.f64']['bytes']==8000000
        assert raw[f'{q}.required.u16']['bytes']==2000000
    assert load(root/'required_dims/REQUIRED_DIMS.json')['all_objects']==a['all_objects']
    assert load(root/'checkpoints/CHECKPOINT_REJECTION.json')['rows']==a['checkpoint_rejection']
    b=load(root/'bytes/BYTE_HEADROOM.json');assert all(b[k]==v for k,v in a['bytes'].items()) and b['per_query']==a['per_query']
    assert load(root/'margin/MARGIN_ANALYSIS.json')['groups']==a['margin_groups']
    robust=load(root/'bytes/PER_QUERY_ROBUSTNESS.json')['metrics']
    for key,v in robust.items():
        values=[x[key] for x in a['per_query']];assert v==dict(min=min(values),p10=percentile(values,.1),median=percentile(values,.5),p90=percentile(values,.9),max=max(values))
    with (root/'figures/required_dims_cdf.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==961;s=0
    for k,r in enumerate(rows):
        s+=a['total_histogram'][k];assert int(r['K'])==k
        assert math.isclose(float(r['all_pair_CDF']),s/a['pairs'],rel_tol=1e-14,abs_tol=1e-14)
        q=[sum(v['histogram'][:k+1])/v['N'] for v in records]
        assert math.isclose(float(r['query_min_CDF']),min(q),abs_tol=1e-14) and math.isclose(float(r['query_max_CDF']),max(q),abs_tol=1e-14)
    if a['decision']=='GO_BYTE_REDUCTION':
        stages=load(root/'bytes/STAGE_ACCOUNTING.json');active=a['pairs'];start=0;payload=0;cont=0
        for row,end in zip(stages['rows'],(128,256,512,960)):
            after=a['pairs']-sum(a['nonhit_histogram'][:end+1]);cost=active*(end-start)*4
            assert row['input_pairs']==active and row['unresolved_after']==after and row['coordinate_bytes']==cost
            payload+=cost
            if end<960:cont+=after
            active=after;start=end
        assert stages['coordinate_bytes_per_query']==payload/32 and stages['optional_global_FP64_state_read_write_bytes_per_query']==16*cont/32 and stages['optional_int32_continuation_read_write_bytes_per_query']==8*cont/32
    qa=load(root/'evidence/FIGURE_QA.json');assert qa['passed'] and qa['no_Type3_fonts']
    for name,h in qa['PDF_hashes'].items():assert sha(root/'figures'/name)==h
    assert a['decision'] in (root/'DECISION.md').read_text()
    print('PASS:exact public ship set, frozen numerical sources,all32M-pair histogram accounting,0 GPU starts,margin/stage/figure identities')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=ROOT);verify(p.parse_args().artifact)
