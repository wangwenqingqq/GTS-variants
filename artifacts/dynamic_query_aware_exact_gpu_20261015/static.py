"""Bind full containers and selected normalized device functions before execution."""
import importlib.util
import re
import subprocess
import sys
import hashlib
from common import REPO, MODES, load, save, sha


def run(w):
    legacy = REPO/'artifacts/progressive_gpu_gate2_20261013'; sys.path.insert(0, str(legacy))
    spec = importlib.util.spec_from_file_location('frozen_static_helpers', legacy/'static_evidence.py')
    helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
    parent = load(REPO/'artifacts/pdx_bond_gpu_realizability_gate4_20261015_recovery_01/evidence/STATIC.json')
    ready = load(w/'READY.json'); rows = {}
    for mode in MODES:
        folder = w/'build'/mode; binary = folder/'service'; assert sha(binary) == ready['binaries'][mode]
        for option, suffix in (('--dump-sass', 'sass.txt'), ('--dump-resource-usage', 'resources.txt')):
            with (folder/suffix).open('x') as f: subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump', option, str(binary)], stdout=f, check=True)
        selected = {n: body for n, body in helpers.functions((folder/'sass.txt').read_text()).items()
                    if any(s in n for s in ('progressive_stage', 'progressive_fields', 'gather_deleted', 'maintain_mean'))}
        assert selected
        functions = {n: dict(normalized_sass_sha256=hashlib.sha256(body.encode()).hexdigest(), opcode_counts=dict(helpers.opcodes(body))) for n, body in selected.items()}
        resources = {}
        for match in re.finditer(r' Function (\S+):\n\s*([^\n]+)', (folder/'resources.txt').read_text()):
            if match[1] in functions: resources[match[1]] = {k: int(v) for k, v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)', match[2])}
        assert resources.keys() == functions.keys()
        for resource in resources.values(): assert resource['STACK'] == resource['LOCAL'] == resource['SHARED'] == 0
        for f in functions.values(): assert not any(op in f['opcode_counts'] for op in ('LDL', 'STL', 'HMMA', 'IMMA', 'QMMA', 'DMMA'))
        query = {n: f['normalized_sass_sha256'] for n, f in functions.items() if 'progressive_' in n}
        if mode != 'S0':
            old = parent['selected_functions']['keeper' if mode == 'S1' else 'candidate']
            assert query == {n: r['normalized_sass_sha256'] for n, r in old.items()}, ('changed frozen search kernel', mode)
        else: assert any('ILi0ELi960E' in n for n in query)
        rows[mode] = dict(binary_sha256=sha(binary), sass_sha256=sha(folder/'sass.txt'), resources_sha256=sha(folder/'resources.txt'),
                          functions=functions, resources=resources, inherited_query_functions_equal=mode != 'S0')
    save(w/'STATIC.json', dict(passed=True, GPU_starts=0, scope='Compile/static only,not runtime or performance', records=rows))
    print('STATIC PASS: S1/PDX query functions match immutable parent;all selected kernels no spill/TC', flush=True)
