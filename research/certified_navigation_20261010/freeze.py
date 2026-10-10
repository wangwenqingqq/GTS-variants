#!/usr/bin/env python3
"""Freeze queries before four-mode measurements, excluding an explicit prior inventory."""
import argparse
import json
from pathlib import Path
import random
from audit import sha, save, load_index


def read_qids(path):
    values=[int(x) for x in path.read_text().split()]
    if not values or values[0]!=len(values)-1:raise ValueError('invalid query list: '+path.name)
    return values[1:]


def freeze(data,index,inventory,out):
    if out.exists():raise ValueError('never overwrite a frozen query set')
    n,d,h,ids,nodes,flags=load_index(index)
    if (n,d,h)!=(1000000,960,6):raise ValueError('target tree')
    prior=set();inputs=[]
    for label,root in inventory.items():
        paths=sorted(Path(root).glob('**/GIST*.qid'))
        if not paths:raise ValueError('missing prior query inventory: '+label)
        for path in paths:
            values=read_qids(path)
            if any(not 0<=x<n for x in values):raise ValueError('prior query out of range')
            prior.update(values)
            inputs.append(dict(label=label,relative_path=str(path.relative_to(root)),sha256=sha(path),count=len(values)))
    rng=random.Random(202610101401);chosen=[]
    while len(chosen)<288:
        x=rng.randrange(n)
        if x not in prior and x not in chosen:chosen.append(x)
    out.mkdir(parents=True)
    for name,values in (('dev32.qid',chosen[:32]),('formal256.qid',chosen[32:])):
        (out/name).write_text(str(len(values))+'\n'+''.join(str(x)+'\n' for x in values))
    reg=dict(seed=202610101401,data_sha256=sha(data),tree_sha256=sha(index),
        development_sha256=sha(out/'dev32.qid'),formal_sha256=sha(out/'formal256.qid'),
        development_ids=chosen[:32],formal_ids=chosen[32:],prior_distinct_ids=len(prior),
        inventoried_files=inputs,formal_development_overlap=0,formal_inventoried_overlap=0,
        inventory_scope='explicit listed GIST query fixtures; undisclosed/non-fixture historical queries are not certified absent',
        frozen_before_four_mode_measurement=True,source_sha256=sha(__file__))
    save(out/'QUERY_MANIFEST.json',reg);return reg


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('data','index','inventory','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(freeze(a.data,a.index,json.loads(a.inventory.read_text()),a.out)))
