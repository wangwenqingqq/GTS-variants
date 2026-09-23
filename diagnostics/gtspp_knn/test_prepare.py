#!/usr/bin/env python3
"""The candidate changes only two shared leaf paths, never sorting or output."""
from pathlib import Path
import tempfile
import prepare
with tempfile.TemporaryDirectory() as tmp:
 a=Path(tmp)/'A';b=Path(tmp)/'B';prepare.prepare(a,'A');prepare.prepare(b,'B')
 diff=[str(p.relative_to(a)) for p in a.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and p.read_bytes()!=(b/p.relative_to(a)).read_bytes()]
 assert diff==['include/search_v2.cuh']
 sa=(a/diff[0]).read_text();sb=(b/diff[0]).read_text()
 assert sa[sa.index('void searchIndexRnnV2('):]==sb[sb.index('void searchIndexRnnV2('):]
 sb=sb.replace((prepare.HERE/'leaf_warp.cuh').read_text()+'\n','',1)
 import re
 sb,n=re.subn(r'\n\tif\(data_info\[2\]==2\)\{knnLeafL2Warp<[^\n]+return;\}\n','',sb);assert n==2 and sb==sa
 assert sa.count('stage.result_sort')==4 and sa.count('stage.aggregate')==4
 assert '#define THREAD_NUM 512' in (a/'include/tree.cuh').read_text()
 try:prepare.prepare(a);raise RuntimeError('overwrite allowed')
 except FileExistsError:pass
print('PASS: pinned source, two leaf fast paths only, all four host overloads/other kernels unchanged')

with tempfile.TemporaryDirectory() as tmp:
 b=Path(tmp)/'B';c=Path(tmp)/'C';prepare.prepare(b,'B');prepare.prepare(c,'C')
 sb=(b/'include/search_v2.cuh').read_text();sc=(c/'include/search_v2.cuh').read_text()
 expected,n=re.subn(r'(dataProcessKnn(?:Vec)?<<<block_num, )THREAD_NUM(>>>)',r'\g<1>64\2',sb);assert n==4
 assert sc==expected.replace('did+=16','did+=blockDim.x/32')
 assert '__managed__ int MAX_SIZE = 20;' in (c/'include/tree.cuh').read_text()
 print('PASS: C changes only leaf CTA width in all four overloads and warp point stride')

with tempfile.TemporaryDirectory() as tmp:
 a=Path(tmp)/'A';d=Path(tmp)/'D';prepare.prepare(a,'A');prepare.prepare(d,'D')
 sa=(a/'include/search_v2.cuh').read_text();sd=(d/'include/search_v2.cuh').read_text()
 sd=sd.replace((prepare.HERE/'leaf_warp_store.cuh').read_text()+'\n','',1)
 sd,n=re.subn(r'\n\tif\(data_info\[2\]==2\)\{knnLeafL2Warp<[^\n]+return;\}\n','',sd);assert n==2
 sd,n=re.subn(r'(dataProcessKnn(?:Vec)?<<<block_num, )64(>>>)',r'\g<1>THREAD_NUM\2',sd);assert n==4 and sd==sa
 print('PASS: D adds only two shared-handoff leaf fast paths and four leaf launch widths')
