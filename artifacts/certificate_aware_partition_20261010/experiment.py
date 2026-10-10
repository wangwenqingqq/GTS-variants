#!/usr/bin/env python3
"""Run the frozen partition-only diagnostic; raw arrays remain outside Git."""
import argparse
import csv
import json
import platform
from pathlib import Path
import numpy as np
from partition import (HERE, sha, save, outside_repo, raw, make_partition, block_stats,
                       queries, query_summary, decide, bind_inputs, source_hashes)


def main(a):
    out = outside_repo(a.output)
    out.mkdir(exist_ok=False)
    source = source_hashes()
    save(out/'REGISTERED.json', dict(source_hashes=source, contract_sha256=sha(HERE/'CONTRACT.json'),
                                    python=platform.python_version(), numpy=np.__version__, CPU_threads_max=4, GPU_processes=0))
    contract, proof, files = bind_inputs(a.prior, a.verification, a.maintenance, a.references)
    radius = float(np.array([0x3f34a3d8], dtype=np.uint32).view(np.float32)[0])
    partition_rows, query_rows, summaries = [], [], []
    with (out/'BLOCK_STATS.csv').open('x', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['snapshot','strategy','partition','block','size'] +
                        ['width_p'+str(i) for i in range(1,5)] + ['normalized_width_p'+str(i) for i in range(1,5)])
        for name in contract['snapshots']:
            binding = proof['bindings'][name]
            qids = binding['queries']
            occ = np.load(a.maintenance/(name+'.occurrence.npy'))
            tree = np.load(a.prior/(name+'_L3.npy'))
            n = len(occ)
            assert n == contract['shape']['N']
            refs = np.stack([raw(a.references/name/(str(q)+'.f64'), '<f8', (n,)) for q in qids])
            truth = refs <= radius*radius
            for strategy in contract['strategies']:
                scores = np.load(a.prior/(name+'_'+strategy+'_scores.npy'), mmap_mode='r')[:4]
                assert scores.shape == (4,n) and np.isfinite(scores).all() and np.all(scores>=0)
                pivots = binding['pivots'][strategy][:4]
                assert np.array_equal(scores[:,qids].T.view(np.uint64), refs[:,pivots].view(np.uint64))
                for kind in contract['partitions']:
                    key = dict(snapshot=name, strategy=strategy, partition=kind)
                    perm, starts = make_partition(np.sqrt(scores), occ, tree, kind)
                    np.savez(out/(name+'_'+strategy+'_'+kind+'.npz'), permutation=perm, starts=starts)
                    lo, hi, sizes, width, normalized, summary = block_stats(scores,perm,starts)
                    partition_rows.append(dict(**key, **summary))
                    for b, size in enumerate(sizes):
                        writer.writerow([name,strategy,kind,b,int(size),*width[:,b],*normalized[:,b]])
                    for p in (4,2):
                        rows = queries(scores,perm,starts,lo,hi,truth,qids,p,radius)
                        query_rows += [dict(**key,**r) for r in rows]
                        summaries.append(dict(**key,pivot_count=p,queries=len(rows),statistics=query_summary(rows)))
                    print(name,strategy,kind,'blocks',len(starts),'survival',summaries[-2]['statistics']['surviving_block_fraction']['mean'],flush=True)
    assert len(partition_rows)==16 and len(query_rows)==1024
    save(out/'PARTITION_STATS.json',dict(rows=partition_rows,per_block_csv='BLOCK_STATS.csv'))
    save(out/'BLOCK_SELECTIVITY.json',dict(rows=query_rows,summary=summaries))
    save(out/'DECISION.json',decide(summaries))
    assert source_hashes()==source, 'source mutation'
    for path,digest in files.items():
        assert sha(path)==digest, ('input mutation',path.name)
    save(out/'PROOF.json',dict(passed=True,source_hashes=source,
                             input_bindings={str(p.relative_to(a.prior)) if p.is_relative_to(a.prior) else
                                             'references/'+str(p.relative_to(a.references)) if p.is_relative_to(a.references) else
                                             'maintenance/'+p.name if p.is_relative_to(a.maintenance) else 'prior_verification.json':h for p,h in files.items()},
                             raw_files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                             partition_configs=16,main_query_rows=512,trend_query_rows=512,false_prune_blocks=0,GPU_processes=0))
    print(json.dumps(decide(summaries)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('prior','verification','maintenance','references','output'):
        p.add_argument('--'+key,type=Path,required=True)
    main(p.parse_args())
