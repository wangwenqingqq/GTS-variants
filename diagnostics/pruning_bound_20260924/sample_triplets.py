#!/usr/bin/env python3
"""Measure a point-level one-pivot triangle bound on fixed random triplets."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924/data')
SEED=240924
PAIRS_PER_QUERY=4096

def main():
    output={'seed':SEED,'pairs_per_query':PAIRS_PER_QUERY,'datasets':{}}
    for ds in ('GIST','Deep'):
        f=ROOT/ds/'1000000'/'fixtures'
        meta=json.loads((f/'oracle.json').read_text())
        d,n,r=meta['dimension'],meta['n'],meta['radii']['normal']
        data=np.memmap(f/'data.f32bin',mode='r',dtype='<f4',offset=12,shape=(n,d))
        qids=list(map(int,(f/'queries.qid').read_text().split()[1:]))
        rng=np.random.default_rng(SEED)
        per=[]
        for q in qids:
            x=rng.integers(n,size=PAIRS_PER_QUERY)
            p=rng.integers(n,size=PAIRS_PER_QUERY)
            qv=np.asarray(data[q],dtype=np.float64)
            xv=np.asarray(data[x],dtype=np.float64)
            pv=np.asarray(data[p],dtype=np.float64)
            dqx=np.sqrt(np.sum((xv-qv)**2,axis=1))
            dqp=np.sqrt(np.sum((pv-qv)**2,axis=1))
            dxp=np.sqrt(np.sum((xv-pv)**2,axis=1))
            lb=np.abs(dqp-dxp)
            miss=dqx>r
            per.append({'qid':q,'misses':int(np.sum(miss)),
                        'median_true_distance':float(np.median(dqx)),
                        'median_point_radial_bound':float(np.median(lb)),
                        'median_bound_over_true_for_misses':float(np.median(lb[miss]/dqx[miss])),
                        'point_bound_rejects_misses':int(np.sum(lb[miss]>r))})
        output['datasets'][ds]={'radius':r,'queries':per,
            'total_misses':sum(x['misses'] for x in per),
            'total_point_bound_rejects_misses':sum(x['point_bound_rejects_misses'] for x in per),
            'input_sha256':hashlib.sha256((f/'oracle.json').read_bytes()).hexdigest()}
    path=Path(__file__).resolve().parent/'SAMPLE.json'
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({ds:{'misses':x['total_misses'],
                         'bound_prunes':x['total_point_bound_rejects_misses']}
                      for ds,x in output['datasets'].items()},indent=2))

if __name__=='__main__':main()
