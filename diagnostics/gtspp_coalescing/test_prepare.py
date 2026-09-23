#!/usr/bin/env python3
"""Assert candidate changes only the aggregation body and its launch grid."""
from pathlib import Path
import tempfile
import prepare
with tempfile.TemporaryDirectory() as tmp:
    a=Path(tmp)/'A';b=Path(tmp)/'B';prepare.prepare(a,'A');prepare.prepare(b,'B')
    different=[str(p.relative_to(a)) for p in a.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and p.read_bytes()!=(b/p.relative_to(a)).read_bytes()]
    assert different==['include/search_v2.cuh'],different
    sa=(a/different[0]).read_text();sb=(b/different[0]).read_text()
    def hide(s):
        begin=s.index('__global__ void mergeResRnn(');op=s.index('{',begin);i=op+1;level=1
        while level:level+=(s[i]=='{')-(s[i]=='}');i+=1
        return s[:op]+s[i:]
    assert hide(sa).replace('block_num = (le - ls + THREAD_NUM - 1) / THREAD_NUM;','block_num = le - ls;',1)==hide(sb)
    assert sa.count('cudaDeviceSynchronize()')==sb.count('cudaDeviceSynchronize()')
    assert 'partial[16]' in sb and '#define THREAD_NUM 512' in (b/'include/tree.cuh').read_text()
    try:prepare.prepare(a,'A');raise AssertionError('overwrite allowed')
    except FileExistsError:pass
print('PASS: exact source pins, only aggregation/grid differ, synchronization unchanged, no overwrite')
