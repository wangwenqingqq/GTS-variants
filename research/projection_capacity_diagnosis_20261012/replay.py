#!/usr/bin/env python3
"""Portable public count/proof replay; optional full private distance/fixture replay."""
import argparse
import csv
import json
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np
from common import HERE,KS,SIZES,ETA,sha,save,inputs,freeze_check,arithmetic_proof,matrix_proof,envelope,level_decision,ordered_project

def main():
    p=argparse.ArgumentParser();p.add_argument('--matrix',action='store_true');p.add_argument('--raw',type=Path);p.add_argument('--bridge',type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args();freeze_check();arithmetic_proof();E=HERE/'evidence'
    s=json.loads((E/'aggregate_summary.json').read_text());assert s['decision']==s['per_level_decisions']['4']['decision'] and len(s['rows'])==24
    with (E/'per_query_capacity.csv').open() as f:qrows=list(csv.DictReader(f))
    assert len(qrows)==192
    for r in s['rows']:
        qs=[q for q in qrows if int(q['k'])==r['k'] and int(q['level'])==r['level']];assert [int(q['query_id']) for q in qs]==inputs()['queries']
        for scope,subset in [('all',qs),('hard',qs[2:])]:
            tr=sum(int(q['truth_objects']) for q in subset);safe=sum(int(q['safe_objects']) for q in subset);possible=sum(int(q['possible_objects']) for q in subset)
            assert float(Fraction(safe,tr))==r['all_alignment' if scope=='all' else 'hard_alignment']
            assert float(Fraction(possible,tr))==r['all_possible_alignment' if scope=='all' else 'hard_possible_alignment'] and 0<=safe<=possible<=tr
        assert [int(q['safe_objects']) for q in qs[2:]]==r['hard_safe_counts']
        assert [int(q['possible_objects']) for q in qs[2:]]==r['hard_possible_counts']
    for l in SIZES:assert level_decision([r for r in s['rows'] if r['level']==l])==s['per_level_decisions'][str(l)]
    basisfile=E/'basis.f64';proof=json.loads((E/'MATRIX_PROOF.json').read_text());assert sha(basisfile)==proof['basis_sha256'] and proof['certified_contractive']
    basis=np.fromfile(basisfile,dtype='<f8').reshape(960,960);assert np.isfinite(basis).all() and np.abs(basis[basis!=0]).min()>=2**-100
    receipt=dict(status='PASS',python=sys.version.split()[0],numpy=np.__version__,replay_source_sha256=sha(Path(__file__)),public_count_arithmetic_and_source_replay=True,query_level_dimension_cells=192,full_matrix_recertified=False,private_full_distance_checks=0,original_vector_fixture_rows=0)
    if a.matrix:
        measured,_,_=matrix_proof(basis);assert measured['certified_contractive'] and measured['gram_infinity_upper']==proof['gram_infinity_upper']
        assert measured['gram_identity_defect_infinity_upper']==proof['gram_identity_defect_infinity_upper'];receipt['full_matrix_recertified']=True
    if a.raw:
        assert sha(a.raw)==json.loads((E/'ORACLE_RECEIPT.json').read_text())['raw_sha256']
        raw=np.load(a.raw);u=raw['U_star_squared'];assert np.array_equal(u,np.array([float.fromhex(v) for v in inputs()['U_star_squared_hex']]))
        for l,size in SIZES.items():
            d=raw[f'D_{l}'];t=raw[f'truth_sq_{l}'];low,high=envelope(d);truth=t>u[:,None];safe=low>np.sqrt(u)[None,:,None];possible=(high>np.sqrt(u)[None,:,None])&truth[None]
            assert np.all(np.diff(d,axis=0)>=0) and np.all(low<=np.sqrt(t)[None]) and not np.any(safe&~truth[None])
            assert np.all(~safe[:-1]|safe[1:]) and np.all(~possible[:-1]|possible[1:])
            for ki,k in enumerate(KS):
                qs=[q for q in qrows if int(q['k'])==k and int(q['level'])==l]
                assert (safe[ki].sum(1)*size).tolist()==[int(q['safe_objects']) for q in qs]
                assert (possible[ki].sum(1)*size).tolist()==[int(q['possible_objects']) for q in qs]
                assert (truth.sum(1)*size).tolist()==[int(q['truth_objects']) for q in qs]
            receipt['private_full_distance_checks']+=d.size
        receipt['private_raw_sha256']=sha(a.raw)
    if a.bridge:
        assert sha(a.bridge)==json.loads((E/'OUTPUT_MANIFEST.json').read_text())['independent2']['bridge_vectors.npz']['sha256']
        bridge=np.load(a.bridge);reference=ordered_project(bridge['vectors'],basis);difference=float(np.abs(reference-bridge['projection']).max());assert difference<2*ETA
        receipt.update(original_vector_fixture_rows=len(reference),max_coordinate_difference=difference)
    if a.receipt:save(a.receipt,receipt)
    print(json.dumps(receipt))

if __name__=='__main__':main()
