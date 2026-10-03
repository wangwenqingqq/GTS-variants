#!/usr/bin/env python3
"""CPU-only regression of tie-aware recall, missing-slot and distance gates."""
import ast
import hashlib
from pathlib import Path
import struct
import tempfile

import numpy as np

# Extract the actual function without importing the CUDA-only CuPy dependency.
tree = ast.parse((Path(__file__).with_name('native_ivf.py')).read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'quality')
namespace = {'np': np}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<quality>', 'exec'), namespace)
quality = namespace['quality']
data = np.arange(12, dtype=np.float32)[:,None]
data[:9] = 0
ref = {'Q': 1, 'records': [{'qid': 0, 'ids': list(range(8)),
        'ties': {'8': {'strictly_closer_ids': [], 'boundary_ids': list(range(9))}}}]}
ids = np.array([[1,2,3,4,5,6,7,8]], dtype=np.int32)
dist = np.zeros((1,8), dtype=np.float32)
q = quality(ids, dist, ref, data, 8)
assert q['recall_tie_aware'] == 1 and q['recall_deterministic'] == 7/8
ids[0,-1] = -1
q = quality(ids, dist, ref, data, 8, allow_missing=True)
assert q['recall_tie_aware'] == 7/8 and q['missing_neighbor_slots'] == 1
try:
    quality(ids, dist, ref, data, 8)
except AssertionError:
    pass
else:
    raise AssertionError('GTS must not accept missing neighbor slots')
ids[0,-1] = 8; dist[0,-1] = 1
assert not quality(ids, dist, ref, data, 8)['distance_tolerance_pass']
ids[0,-1] = 7
try:
    quality(ids, dist, ref, data, 8)
except AssertionError:
    pass
else:
    raise AssertionError('Duplicate IDs must be rejected')
print('PASS ties, missing-slot scoring, GTS completeness, field tolerance, duplicate-ID rejection')

tree = ast.parse((Path(__file__).with_name('verify_outputs.py')).read_text())
namespace.update({'original_quality': quality, 'hashlib': hashlib, 'struct': struct})
for name in ('output_fields', 'quality', 'verify_cache'):
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<post-validation>', 'exec'), namespace)
verified = namespace['quality']
ids = np.array([[0,9,1,2,3,4,5,6]], dtype=np.int32)
dist = data[ids,0].copy()
assert quality(ids, dist, ref, data, 8)['distance_tolerance_pass']
assert not verified(ids, dist, ref, data, 8)['nondecreasing_distance_pass']
dist[0,1] = -9
assert quality(ids, dist, ref, data, 8)['distance_tolerance_pass']
assert not verified(ids, dist, ref, data, 8)['nonnegative_pass']
dtype = np.dtype([('pid','<i4'), ('min_dis','<f4'), ('size','<i4'), ('lid','<i4'), ('is_leaf','<i4')])
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp)/'cache'
    def write_cache(spans):
        nodes = np.zeros(len(spans), dtype=dtype)
        nodes['is_leaf'] = 1
        for node,(lid,size) in zip(nodes,spans):node['lid']=lid;node['size']=size
        path.write_bytes(struct.pack('<iiii',10,96,3,len(spans))+np.arange(10,dtype='<i4').tobytes()+nodes.tobytes()+np.zeros(len(spans),dtype='<i4').tobytes())
    write_cache([(0,4),(4,3),(7,3)])
    assert namespace['verify_cache'](path)['exact_disjoint_partition_pass']
    write_cache([(0,4),(3,3),(7,3)])
    try:namespace['verify_cache'](path)
    except AssertionError:pass
    else:raise AssertionError('Summed leaf capacity must not substitute for an exact partition')
print('PASS supplemental negative/order fields and overlap/gap cache regression')
