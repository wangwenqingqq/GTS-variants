#!/usr/bin/env python3
"""Public count/proof replay; optional private full cached-mask and packing replay."""
import argparse, csv, json, sys
from fractions import Fraction
from pathlib import Path
import numpy as np
from views import HERE, configurations, exact_gram_bound, bounds, decision, sha
sys.path.insert(0,str(HERE.parent/'projection_certificate_20261011'))
from build_projection import ordered
from evaluate_multi_view import csv_write

def read(p):
    with p.open() as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=HERE/'evidence');p.add_argument('--private-run',type=Path);p.add_argument('--bridge',type=Path);p.add_argument('--receipt',type=Path)
    a=p.parse_args();E=a.evidence;summary=json.loads((E/'aggregate_summary.json').read_text());manifest=json.loads((E/'VIEW_MANIFEST.json').read_text());im=json.loads((E/'INPUT_IDENTITY.json').read_text())
    assert sha(HERE/'CONTRACT.json')==im['contract_sha256'];cfg,aliases=configurations();assert cfg==manifest['physical_configs'] and aliases==manifest['aliases']
    assert len(summary['rows'])==36 and summary['decision']==decision(summary['rows'])['decision']
    old=json.loads((HERE.parent/'projection_certificate_20261011/evidence/BASIS.json').read_text())
    matrices=np.concatenate([np.array([[float.fromhex(t) for t in r] for r in old['families']['PCA']]),np.array([[float.fromhex(t) for t in r] for r in manifest['projected_direction_hex']])])
    for c in cfg:
        for vi,g in enumerate(c['groups']):
            ub,sums=exact_gram_bound(matrices[g]);assert ub<=1
            recorded=next(r for r in manifest['proofs'] if r['config']==c['config'] and r['view']==vi)
            assert str(ub)==recorded['exact_gram_infinity_bound'] and list(map(str,sums))==recorded['exact_gram_row_sums']
    pq=read(E/'per_query_summary.csv');qv=read(E/'query_view_gain.csv');cost=read(E/'cost_accounting.csv');assert len(pq)==288 and len(qv)==1176 and len(cost)==36
    for r in summary['rows']:
        rr=[s for s in pq if s['config']==r['config'] and int(s['level'])==r['level']]
        assert len(rr)==8 and sum(int(s['pruned_objects']) for s in rr)==r['pruned_objects'] and sum(int(s['truth_prunable_objects']) for s in rr)==r['truth_prunable_objects']
        assert [int(s['pruned_objects']) for s in rr[2:]]==r['hard_query_pruned'] and [int(s['truth_prunable_objects']) for s in rr[2:]]==r['hard_query_truth_prunable']
        assert float(min(Fraction(int(s['pruned_objects']),int(s['truth_prunable_objects'])) for s in rr[2:]))==r['worst_hard_alignment']
        vv=[s for s in qv if s['config']==r['config'] and int(s['level'])==r['level']]
        assert sum(int(s['unique_pruned_objects']) for s in vv)==r['unique_pruned_objects']
        for s in vv:assert int(s['unique_pruned_objects'])+int(s['shared_pruned_objects'])==int(s['pruned_objects'])
    la=json.loads((E/'LOOKAHEAD_SUMMARY.json').read_text());lr=read(E/'lookahead_parents.csv');assert len(lr)==16
    assert sum(int(r['gain_pruned_objects']) for r in lr)==la['pooled']['gain_objects'] and sum(int(r['denominator']) for r in lr)==la['pooled']['denominator']
    for r in lr:assert int(r['lookahead_horizon_pruned'])>=int(r['greedy_horizon_pruned']) and int(r['denominator'])==6*int(r['parent_objects'])
    receipt=dict(status='PASS',public_proof_count_replay=True,python=sys.version.split()[0],numpy=np.__version__,private_cached_bounds_replayed=False,serialized_roundtrip_cells=0,restricted_vectors_published=False)
    if a.private_run:
        meta=np.load(a.private_run/'metadata_and_truth.npz');masks=np.load(a.private_run/'constituent_prune_masks.npz');u_sq=np.array([float.fromhex(t) for t in im['U_star_squared_hex']]);u=np.sqrt(u_sq);checks=0
        for r in summary['rows']:
            c=next(c for c in cfg if c['config']==r['config']);l=r['level'];size=10**(6-l);lo=meta[f'low_{l}'];hi=meta[f'high_{l}'];q=meta['query_projection'];truth=meta[f'truth_sq_{l}'];flat=np.concatenate(c['groups'])
            packed=np.stack([lo[:,flat],hi[:,flat]],axis=-1).astype('<f4').reshape(10**l,16)
            blob=packed.tobytes();name=f'{r["config"]}_L{l}.metadata.f32';m=json.loads((E/'OUTPUT_MANIFEST.json').read_text())[name]
            assert len(blob)==64*10**l and __import__('hashlib').sha256(blob).hexdigest()==m['sha256']
            loaded=np.frombuffer(blob,dtype='<f4').reshape(10**l,8,2);assert np.array_equal(loaded[:,:,0],lo[:,flat]) and np.array_equal(loaded[:,:,1],hi[:,flat])
            lb=[];offset=0
            for g in c['groups']:
                k=len(g);lb.append([bounds(loaded[:,offset:offset+k,0],loaded[:,offset:offset+k,1],qq[g]) for qq in q]);offset+=k
            lb=np.array(lb);assert np.all(lb<=np.sqrt(truth)[None,:,:]);mask=lb>u[None,:,None]
            assert np.array_equal(mask,masks[f'{r["config"]}_L{l}']) and not np.any(mask & (truth<=u_sq[:,None])[None,:,:])
            assert mask.any(0).sum(1).tolist()==[int(s['pruned_objects'])//size for s in pq if s['config']==r['config'] and int(s['level'])==l]
            checks+=lb.size;receipt['serialized_roundtrip_cells']+=1
        receipt.update(private_cached_bounds_replayed=True,constituent_truth_checks=checks,private_metadata_sha256=sha(a.private_run/'metadata_and_truth.npz'),private_masks_sha256=sha(a.private_run/'constituent_prune_masks.npz'))
    if a.bridge:
        f=np.load(a.bridge);actual=ordered(f['vectors'],matrices[8:]);assert np.array_equal(actual,f['projection'])
        receipt.update(independent_original_vector_bridge_rows=len(f['row_ids']),independent_original_vector_bridge_values=actual.size)
    if a.receipt:
        with a.receipt.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
