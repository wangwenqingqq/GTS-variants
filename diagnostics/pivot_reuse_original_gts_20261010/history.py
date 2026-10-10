#!/usr/bin/env python3
"""Inventory known in-dataset GIST IDs without claiming complete private history."""
import argparse
import hashlib
import json
from pathlib import Path

def collect(roots):
    files={};ids=set()
    for number,root in enumerate(roots):
        for path in sorted(root.rglob('*.qid')):
            relative=path.relative_to(root)
            name=str(relative).lower()
            if 'local/' in name:continue
            if 'gist' not in name and 'arithmetic_path_boundary_20260928/frozen' not in name:continue
            raw=path.read_bytes();values=list(map(int,raw.split()))
            assert values and values[0]==len(values)-1,path
            valid={x for x in values[1:] if 0<=x<1000000}
            ids.update(valid)
            files[f'collection{number}/{relative}']={'sha256':hashlib.sha256(raw).hexdigest(),
                'query_count':values[0],'in_first_million_id_count':len(valid)}
    assert files and len(ids)>=256
    return {'excluded_ids':sorted(ids),'excluded_count':len(ids),'files':files,
            'scope':'No intersection with inventoried GIST-named and cumulative original-distance query files. Generic unnamed/private prior queries may be missing; confirmation is not claimed universally unseen.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,action='append',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();x=collect(a.root)
    with a.out.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print('Inventoried',len(x['files']),'files;',x['excluded_count'],'known IDs excluded')
