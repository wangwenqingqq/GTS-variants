#!/usr/bin/env python3
"""Public integer-count/gate replay; optional private all-bound cross-runtime replay."""
import argparse
import csv
from pathlib import Path
import numpy as np
from aabb_math import *

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-build',type=Path);p.add_argument('--pointset',type=Path);p.add_argument('--raw-bounds',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();freeze_check()
    e=HERE/'evidence';rows=list(csv.DictReader((e/'per_query_summary.csv').open()));levels=json.loads((e/'aggregate_summary.json').read_text())['level_results'];assert len(rows)==72 and len(levels)==9
    by={(int(r['k']),int(r['level']),int(r['query_id'])):r for r in rows};assert len(by)==72
    for r in levels:
        group=[by[r['k'],r['level'],q] for q in identity()['queries'][2:]]
        for key in ('truth','point','aabb'):assert sum(int(v[key+'_objects']) for v in group)==r['hard_'+key+'_objects']
        assert r['hard_alignment']==ratio(r['hard_aabb_objects'],r['hard_truth_objects'])
        assert r['hard_retention']==ratio(r['hard_aabb_objects'],r['hard_point_objects'])
        assert r['projection_loss_objects']+r['summary_loss_objects']+r['hard_aabb_objects']==r['hard_truth_objects']
        can=by[r['k'],r['level'],359924];assert int(can['aabb_objects'])==r['canary_aabb_objects']
        assert r['canary_retention']==ratio(r['canary_aabb_objects'],r['canary_point_objects'])
    summary=json.loads((e/'aggregate_summary.json').read_text());decision=stage_a(levels)
    for key,v in decision.items():assert summary[key]==v
    tested=json.loads((e/'QUANTIZATION_VALIDATION.json').read_text());assert summary['stage_B_formats']==tested['tested_formats']
    if not decision['stage_B_admitted']:assert tested['status']=='NOT_ADMITTED' and tested['tested_formats']==[]
    result=dict(status='PASS',public_query_cells=72,public_level_cells=9,exact_integer_gates=decision,source_sha256=sha(Path(__file__)))
    if a.raw_build:
        assert a.pointset and a.raw_bounds;pin(a.pointset,'capacity_raw_npz')
        for path,phase in [(a.raw_build,'BUILD2'),(a.raw_bounds,'EVAL2')]:
            expected=json.loads((e/(phase+'_RAW_MANIFEST.json')).read_text())[path.name]
            assert path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256']
        from evaluate_fp32 import compute
        with np.load(a.raw_build) as ab,np.load(a.pointset) as pt:q,l,b,checks=compute(ab,pt)
        with np.load(a.raw_bounds) as stored:
            assert set(stored.files)==set(b)
            for key,values in b.items():assert np.array_equal(values,stored[key]),key
        assert l==levels
        for r in q:
            stored=by[r['k'],r['level'],r['query_id']]
            for key,v in r.items():assert stored[key]==('' if v is None else str(v)),(key,stored[key],v)
        result.update(all_bound_checks=checks,private_raw_exact_counts_and_floats=True,all_bound_arrays_bit_identical=True)
    if a.out:save(a.out,result)
    print(json.dumps(result))

if __name__=='__main__':main()
