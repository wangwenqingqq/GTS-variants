#!/usr/bin/env python3
import argparse,hashlib,json,random,subprocess,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
SIZES=[2000,4000,8000,16000,32000,64000,128000,256000]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(source,anchor,out,oracle_bin):
    raw=source.read_bytes();lines=raw.splitlines();width,n,metric=map(int,lines[0].split());rows=lines[1:]
    assert sha(source)=='72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c'
    assert len(rows)==n and metric==6 and all(b'\0' not in x and len(x)<109 for x in rows)
    base=[i*(n-1)//1999 for i in range(2000)];qids=list(map(int,(anchor/'queries.qid').read_text().split()));assert qids.pop(0)==len(qids)==64
    query_source=[base[q] for q in qids];chosen=set(base)
    additions=random.Random(20260924).sample([i for i in range(n) if i not in chosen],SIZES[-1]-2000)
    out.mkdir();manifest={}
    for size in SIZES:
        ids=sorted(base+additions[:size-2000]);lookup={x:i for i,x in enumerate(ids)};qs=[lookup[x] for x in query_source]
        dest=out/str(size)/'fixtures';dest.mkdir(parents=True);(dest.parent/'runs').mkdir();(dest.parent/'bin').symlink_to('../../bin')
        (dest/'data.txt').write_bytes(f'{width} {size} 6\n'.encode()+b'\n'.join(rows[i] for i in ids)+b'\n')
        if size==2000:assert sha(dest/'data.txt')==sha(anchor/'words_2000.txt')
        for name,q in [('queries.qid',qs),('check_queries.qid',qs[::8])]:
            (dest/name).write_text(str(len(q))+'\n'+'\n'.join(map(str,q))+'\n')
        (dest/'indices.json').write_text(json.dumps(ids)+'\n')
        manifest[str(size)]={'n':size,'queries':qs,'query_source_ids':query_source,'source_sha256':sha(source)}
    large=out/str(SIZES[-1])/'fixtures';subprocess.run([str(oracle_bin),str(large/'data.txt'),str(large/'queries.qid'),str(large/'oracle.bin')],check=True)
    matrix=np.fromfile(large/'oracle.bin',dtype=np.uint8).reshape(64,SIZES[-1]);large_ids=json.loads((large/'indices.json').read_text());pos={s:i for i,s in enumerate(large_ids)}
    sys.path.insert(0,str(HERE.parent/'original_tree_profile'));from make_fixture import distance
    rng=random.Random(19)
    for qi,k in [(0,0),(63,len(large_ids)-1)]+[(rng.randrange(64),rng.randrange(len(large_ids))) for _ in range(128)]:
        assert int(matrix[qi,k])==distance(rows[query_source[qi]],rows[large_ids[k]])
    for size in SIZES:
        dest=out/str(size)/'fixtures';ids=json.loads((dest/'indices.json').read_text())
        if size!=SIZES[-1]:matrix[:,[pos[x] for x in ids]].tofile(dest/'oracle.bin')
        meta=manifest[str(size)];meta['sha256']={p.name:sha(p) for p in dest.iterdir()};(dest/'oracle.json').write_text(json.dumps(meta,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PASS nested pinned fixtures, same 64 query words, CPU matrix + 130 Python cross-checks')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source','anchor','output','oracle_binary']:p.add_argument(name,type=Path)
    a=p.parse_args();main(a.source,a.anchor,a.output,a.oracle_binary.resolve())
