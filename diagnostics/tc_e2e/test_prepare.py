#!/usr/bin/env python3
"""CPU-only regression of isolated patches, frozen kernel reuse and orders."""
import hashlib
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import sys
import tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare',HERE/'prepare.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
local=HERE/'local';local.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=local) as tmp:
    for h in [3,5]:
        out=Path(tmp)/str(h);prep.prepare(Path(sys.argv[1]),out,h)
        src=(out/'GTS/include/search_v2.cuh').read_text();old=(Path(sys.argv[1])/'GTS/include/search_v2.cuh').read_text()
        assert src.count('tc_refine(')==1 and src.count("if (tc_variant == 'O')")==1
        assert src.count('dataProcessRnn<<<')==old.count('dataProcessRnn<<<')
        # kNN changed only by the previously documented common profile/workspace wrapper.
        assert 'tc_variant' not in src.split('void searchIndexKnnV2(')[1]
        parent=(HERE.parent/'tc_leaf_probe/probe.cu').read_text().split('int main(int argc,char** argv) try {')[0]
        assert (out/'GTS/include/leaf_kernels.cuh').read_text()=='#pragma once\n'+parent
        m=json.loads((out/'INSTRUMENTED_SHA256.json').read_text());assert all(hashlib.sha256((out/f).read_bytes()).hexdigest()==v for f,v in m.items())
        try:prep.prepare(Path(sys.argv[1]),out,h)
        except FileExistsError:pass
        else:raise AssertionError('must refuse overwrite')
orders=['OSTD','TDOS','SODT','DTSO','DSOT','TOSD']
assert all(sum(o.index(a)<o.index(b) for o in orders)==3 for a,b in combinations('OSTD',2))
assert all(1<=sum(o.index(v)==pos for o in orders)<=2 for v in 'OSTD' for pos in range(4))
spec=importlib.util.spec_from_file_location('analyze',HERE/'analyze.py');analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
assert analysis.portable_profile([{'Minimum Virtual Address':'0xAB','Maximum Virtual Address':'0xCD','CPU Instruction Address':'0xEF','count':'9','name':'simt'}])==[{'CPU Instruction Address':'unresolved instruction','count':'9','name':'simt'}]
print('PASS: source pins, isolated patch, frozen kernels, manifests, no overwrite, balanced orders, profile redaction')
