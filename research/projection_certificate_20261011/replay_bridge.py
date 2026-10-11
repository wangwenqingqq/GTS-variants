#!/usr/bin/env python3
"""Independent Python-scalar replay of a small cross-runtime projection fixture."""
import argparse,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'certified_navigation_20261010'))
from audit import sha,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();stage=json.loads((a.run/'STAGE_A.json').read_text())
    assert stage['status']=='PASS' and sha(a.run/'bridge_vectors.npz')==stage['bridge_vectors_sha256']
    b=json.loads((a.run/'BASIS.json').read_text());assert sha(a.run/'BASIS.json')==stage['basis_sha256']
    matrix=np.array([[float.fromhex(v) for v in row] for family in ['RANDOM_ORTHO','PCA'] for row in b['families'][family]])
    f=np.load(a.run/'bridge_vectors.npz');out=np.zeros((len(f['row_ids']),16),dtype=np.float64)
    assert f['vectors'].shape==(len(out),960) and np.isfinite(f['vectors']).all()
    for ri,row in enumerate(f['vectors']):
        for j,p in enumerate(matrix):
            total=0.
            for x,y in zip(row,p):
                term=float(x)*float(y);total=total+term
            out[ri,j]=total
    assert np.array_equal(out.view(np.uint64),f['projection'].view(np.uint64)),'scalar cross-runtime bit mismatch'
    save(a.out,dict(status='PASS',rows=len(out),coordinate_values=len(out)*16,
        scalar_multiply_adds=len(out)*16*960,bitwise_equal=True,python=sys.version.split()[0],
        source_sha256=sha(Path(__file__)),fixture_sha256=sha(a.run/'bridge_vectors.npz'),
        scope='tiny scalar replay fixture, supplementary to remote all-object 128-pair Stage A'))
    print('Independent Python scalar bitwise replay PASS',len(out),'rows')
if __name__=='__main__':main()
