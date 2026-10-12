#!/usr/bin/env python3
"""Public integer/proof replay, optionally all private serialized bounds and vector fixture."""
import argparse
import csv
import json
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np
from shape_math import HERE,NAMES,BYTES,LEVELS,sha,save,check_freeze,decision,all_bounds,pack,unpack
from projection_math import exact_gram_bound,projection_error_bound,error_bound,ETA,RHO
from independent import project,box_lb,ball_lb,ellipsoid_lb


def read(path):
    with Path(path).open() as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=HERE/'evidence');p.add_argument('--build',type=Path);p.add_argument('--eval',type=Path);p.add_argument('--bridge',type=Path);p.add_argument('--receipt',type=Path)
    a=p.parse_args();check_freeze();E=a.evidence;summary=json.loads((E/'aggregate_summary.json').read_text());rows=summary['rows']
    assert len(rows)==12 and summary['decision']==decision(rows)['decision']
    c=json.loads((HERE/'CONTRACT.json').read_text());im=json.loads((E/'INPUT_IDENTITY.json').read_text());assert sha(HERE/'CONTRACT.json')==im['contract_sha256']
    queries=read(E/'per_query_summary.csv');assert len(queries)==96
    for r in rows:
        q=[v for v in queries if v['shape']==r['shape'] and int(v['level'])==r['level']];assert len(q)==8
        assert [int(v['query_id']) for v in q]==c['queries']
        assert sum(int(v['pruned_objects']) for v in q)==r['pruned_objects']
        assert sum(int(v['truth_prunable_objects']) for v in q)==r['truth_prunable_objects']
        assert [int(v['pruned_objects']) for v in q[2:]]==r['hard_query_pruned']
        assert [int(v['truth_prunable_objects']) for v in q[2:]]==r['hard_query_truth_prunable']
        assert float(min(Fraction(int(v['pruned_objects']),int(v['truth_prunable_objects'])) for v in q[2:]))==r['worst_hard_alignment']
        assert float(q[2]['alignment'])==r['canary_alignment']
    safety=json.loads((E/'SAFETY_VALIDATION.json').read_text());assert safety['status']=='PASS_G1_G2_G3_G4_G5'
    g5=json.loads((E/'G5_VALIDATION.json').read_text());assert g5['pairs_total']==384 and g5['pairs_per_level']=={'3':128,'4':128,'5':128}
    assert len(g5['checks'])==384 and g5['original_region_objects_recomputed']==142080
    basisfile=HERE.parent/'projection_certificate_20261011/evidence/BASIS.json';assert sha(basisfile)==im['basis_sha256']
    basis=np.array([[float.fromhex(v) for v in r] for r in json.loads(basisfile.read_text())['families']['PCA']])
    upper,_=exact_gram_bound(basis);assert upper<=1 and projection_error_bound()<ETA and error_bound()<RHO
    receipt=dict(status='PASS',public_integer_and_proof_replay=True,python=sys.version.split()[0],numpy=np.__version__,
        private_full_bounds_replayed=False,serialized_cells_replayed=0,original_vector_fixture_rows=0)
    if a.build or a.eval:
        assert a.build and a.eval;metadata=np.load(a.build/'metadata_and_truth.npz');raw=np.load(a.eval/'full_query_region_bounds.npz')
        sm=json.loads((E/'SHAPE_MANIFEST.json').read_text());counts=0
        for l,size in LEVELS.items():
            meta={k:metadata[f'{k}_{l}'] for k in ['low','high','center','radius','minimax','minimax_radius','scale','factor']}
            reconstructed={}
            for shape in NAMES:
                blob=pack(meta,shape);record=next(v for v in sm['cells'] if v['shape']==shape and v['level']==l)
                assert len(blob)==record['metadata_bytes'] and __import__('hashlib').sha256(blob).hexdigest()==record['metadata_sha256']
                reconstructed.update(unpack(blob,shape));receipt['serialized_cells_replayed']+=1
            bounds=np.array([all_bounds(reconstructed,q) for q in metadata['query_projection']]).transpose(1,0,2)
            assert np.array_equal(bounds,raw[f'LB_{l}'])
            truth=metadata[f'truth_sq_{l}'];assert np.array_equal(np.sqrt(truth),raw[f'LB_truth_{l}'])
            assert np.all(bounds<=np.sqrt(truth)[None]);u=metadata['U_star_squared'];masks=bounds>np.sqrt(u)[None,:,None]
            assert not np.any(masks & (truth<=u[:,None])[None])
            for si,shape in enumerate(NAMES):
                qq=[v for v in queries if v['shape']==shape and int(v['level'])==l]
                assert (masks[si].sum(1)*size).tolist()==[int(v['pruned_objects']) for v in qq]
            counts+=bounds.size
        receipt.update(private_full_bounds_replayed=True,full_truth_checks=counts,
            private_metadata_sha256=sha(a.build/'metadata_and_truth.npz'),private_raw_bounds_sha256=sha(a.eval/'full_query_region_bounds.npz'))
    if a.bridge:
        bridge=np.load(a.bridge);actual=project(bridge['vectors'],basis);assert np.array_equal(actual,bridge['projection'])
        receipt['original_vector_fixture_rows']=len(bridge['row_ids']);receipt['original_vector_fixture_values']=actual.size
    if a.receipt:save(a.receipt,receipt)
    print(json.dumps(receipt))


if __name__=='__main__':main()
