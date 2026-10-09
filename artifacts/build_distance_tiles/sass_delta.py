#!/usr/bin/env python3
"""Static all-function comparison, not a dynamic-work or timing claim."""
import argparse
import importlib.util
import hashlib
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('normalization',HERE.parent/'rebuild_tree_baselines/verify_profile.py')
normalization=importlib.util.module_from_spec(spec);spec.loader.exec_module(normalization)
sha=normalization.sha


def functions(text):
    result={}
    for line in text.splitlines():
        if line.startswith('Function:'):key=line[10:];result[key]=[]
        elif line.endswith(';'):result[key].append(line)
    return result


def compare(parent,candidate):
    assert sha(parent)=='7d0ff1767e79a2dbc1f8ea18e52d29015d3d5a99ce4491dab8836d75b5f40948'
    a=functions(parent.read_text());normalized=normalization.normalize_dump(candidate.read_text());b=functions(normalized)
    assert len(a)==112 and len(b)==113
    assert all(a[k]==b.get(k) for k in a),'original GPU function changed'
    added=list(set(b)-set(a));assert len(added)==1 and 'getPivotDisTiled' in added[0]
    return dict(passed=True,parent_normalized_sha256=sha(parent),candidate_raw_sha256=sha(candidate),
        candidate_normalized_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
        preserved_functions=112,preserved_instructions=sum(map(len,a.values())),added_function=added[0],added_instructions=len(b[added[0]]),
        analysis_sha256=sha(Path(__file__)),scope='all original compiled GPU functions identical; static identity, not dynamic instruction counts or speed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','candidate','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert __debug__ and not a.output.exists();a.output.write_text(json.dumps(compare(a.parent,a.candidate),indent=2)+'\n')
