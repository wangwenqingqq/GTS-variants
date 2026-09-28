#!/usr/bin/env python3
"""Hash retained cuobjdump output and identify the six traversal functions."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PATTERNS = {'E': r'^_Z11findNextRnn', 'R': r'^_Z14findNextLayoutILi2',
            'T': r'^_Z14findNextLayoutILi3', 'F': r'^_Z14fusedTraversalILb0',
            'X': r'^_Z20fusedTraversalLayoutILi2', 'Y': r'^_Z20fusedTraversalLayoutILi3'}


def audit(root):
    sha = lambda data: hashlib.sha256(data).hexdigest()
    res = (root/'static/resources.txt').read_text()
    sass = (root/'static/sass.txt').read_text()
    output = {}
    for mode, pattern in PATTERNS.items():
        matches = [(name, resource) for name, resource in
                   re.findall(r' Function (\S+):\n  ([^\n]+)', res)
                   if re.match(pattern, name)]
        assert len(matches) == 1, (mode, matches)
        name, resource = matches[0]
        start = sass.index('Function : '+name+'\n')
        end = sass.find('Function : ', start+1)
        body = sass[start:end if end != -1 else len(sass)]
        instructions = [line.strip() for line in body.splitlines()
                        if re.match(r'\s*/\*[0-9a-f]+\*/\s+(?:@\S+\s+)?[A-Z]', line)]
        output[mode] = dict(symbol=name, resources=resource,
                            exact_function_dump_sha256=sha(body.encode()),
                            static_instruction_lines=len(instructions),
                            static_instruction_sites={op: sum(bool(re.search(r'\b'+op+r'(?:\.|\b)', line))
                                                             for line in instructions)
                                                      for op in ['BAR', 'LDL', 'STL', 'CALL', 'EXIT']})
    output.update(binary_sha256=sha((root/'bin/graph_bench').read_bytes()),
                  sass_dump_sha256=sha((root/'static/sass.txt').read_bytes()),
                  resource_dump_sha256=sha((root/'static/resources.txt').read_bytes()),
                  scope='Exact cuobjdump sections from retained sm_120 CUDA 13.1.115 executable; static sites do not establish runtime spills or bottlenecks. Runtime symbols/resources checked independently via NSYS.')
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(audit(a.root), indent=2)+'\n')
