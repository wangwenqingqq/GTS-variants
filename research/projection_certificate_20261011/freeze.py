#!/usr/bin/env python3
"""Freeze inherited inputs and balanced bridge pairs before computing projections."""
import argparse,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'certified_navigation_20261010'))
from audit import sha,save,load_index

def main():
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True)
    p.add_argument('--scores',type=Path,required=True);p.add_argument('--ancestors',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    old=HERE.parent/'certificate_compression_20261011';prior=HERE.parent/'region_truth_diagnosis_20261011'
    identity=json.loads((old/'evidence/INPUT_IDENTITY.json').read_text())
    pm=json.loads((old/'evidence/PIVOT_MANIFEST.json').read_text())
    contract=json.loads((HERE/'CONTRACT.json').read_text())
    assert identity['queries']==contract['queries']
    assert sha(a.index)==identity['tree_sha256']
    assert sha(a.scores)==identity['prior_scores_sha256']
    assert sha(a.ancestors)==pm['ancestors_sha256']
    n,d,h,ids,nodes,flags=load_index(a.index);assert (n,d,h)==(1000000,960,6) and not any(flags)
    rng=np.random.default_rng(contract['bridge_seed']);pairs=[]
    for level,count in zip(contract['levels'],contract['bridge_pairs_per_level']):
        regions=10**level;size=n//regions;start=(regions-1)//9
        for pair in sorted(map(int,rng.choice(8*regions,count,replace=False))):
            qi,ri=divmod(pair,regions);node=start+ri
            assert nodes[node][2:4]==(size,ri*size)
            pairs.append(dict(query_index=qi,query_id=identity['queries'][qi],level=level,
                region_index=ri,region_id=node,object_ids=list(ids[ri*size:(ri+1)*size])))
    save(a.out/'BRIDGE_PAIRS.json',dict(seed=contract['bridge_seed'],pair_count=128,
        every_pair_covers=['RANDOM_ORTHO','PCA'],prefixes=contract['prefixes'],pairs=pairs))
    save(a.out/'INPUT_MANIFEST.json',dict(**identity,projection_base_commit=contract['base_commit'],
        ancestors_sha256=sha(a.ancestors),contract_sha256=sha(HERE/'CONTRACT.json'),
        pairs_sha256=sha(a.out/'BRIDGE_PAIRS.json'),
        prior_published_manifest_sha256=sha(old/'PUBLISH_MANIFEST.json'),
        pivot_summary_sha256=sha(old/'evidence/per_level_summary.csv'),
        oracle_sha256=sha(prior/'evidence/oracle8.bin'),
        trace_sha256=sha(prior/'evidence/G0_trace8.json.gz')))
    print('Frozen: 128 pairs, 2 families x 4 prefixes each; no projection measurements')
if __name__=='__main__':main()
