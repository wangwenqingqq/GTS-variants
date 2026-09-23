#!/usr/bin/env python3
"""Prepare a pinned GTS leaf exporter and bounded SIFT fixtures (stdlib only)."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_prepare', HERE.parent/'original_tree_profile/prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# Called after the existing device synchronization; only diagnostic exports added.
EXPORT = r'''
            if (const char* path = std::getenv("GTS_TC_EXPORT")) {
                std::vector<int> ns(lnum), qs(lnum);
                CHECK(cudaMemcpy(ns.data(),p_list+offset_p+size_list[cur_level]/(MAX_SIZE+3),lnum*sizeof(int),cudaMemcpyDeviceToHost));
                CHECK(cudaMemcpy(qs.data(),p_list+offset_p+size_list[cur_level]/(MAX_SIZE+3)*2,lnum*sizeof(int),cudaMemcpyDeviceToHost));
                FILE* f = std::fopen(path, "a"); if (!f) std::exit(81);
                for (int i=0;i<lnum;++i) std::fprintf(f,"%d %d\n",qs[i],ns[i]);
                if (std::fclose(f)) std::exit(83);
            }
'''
INDEX_EXPORT = r'''
    if (const char* path=std::getenv("GTS_TC_INDEX")) {
        int nn=max_node_num[0];
        std::vector<TN> nodes(nn); std::vector<int> ids(data_info[1]), empty(nn);
        CHECK(cudaMemcpy(nodes.data(),node_list,nn*sizeof(TN),cudaMemcpyDeviceToHost));
        CHECK(cudaMemcpy(ids.data(),id_list,data_info[1]*sizeof(int),cudaMemcpyDeviceToHost));
        CHECK(cudaMemcpy(empty.data(),empty_list,nn*sizeof(int),cudaMemcpyDeviceToHost));
        FILE* f=std::fopen(path,"w"); if(!f) std::exit(84);
        for(int i=0;i<nn;++i) if(!empty[i] && nodes[i].is_leaf) {
            TN n=nodes[i]; if(n.size<1 || n.size>MAX_SIZE || n.lid<0 || n.lid+n.size>data_info[1]) std::exit(85);
            std::fprintf(f,"%d %d",i,n.size);
            for(int j=0;j<n.size;++j) std::fprintf(f," %d",ids[n.lid+j]);
            std::fprintf(f,"\n");
        }
        if(std::fclose(f)) std::exit(86);
    }
'''

def prepare(source, out, height):
    base.prepare(source, out)
    p=out/'GTS/include/search_v2.cuh'
    text=p.read_text()
    anchor='\t\t\t// Processing data in leaf node.\n\t\t\tblock_num = lnum;'
    front, marker, tail=text.partition('void searchIndexKnnV2(')
    assert marker
    p.write_text(base.once(front,anchor,EXPORT+'\n'+anchor)+marker+tail)
    p=out/'GTS/src/main.cu'
    anchor='\tindexConstru(data_d, data_s, size_s, data_info, id_list, node_list, max_node_num, tree_h, empty_list);'
    p.write_text(base.once(p.read_text(),anchor,anchor+'\n'+INDEX_EXPORT))
    p=out/'GTS/include/tree.cuh'
    p.write_text(base.once(p.read_text(),'__managed__ int MAX_H = 3;',f'__managed__ int MAX_H = {height};'))
    manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(out.rglob('*')) if p.is_file() and p.name!='INSTRUMENTED_SHA256.json'}
    (out/'INSTRUMENTED_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')


def fixture(source, out, n):
    out.mkdir(parents=True, exist_ok=False)
    h=hashlib.sha256()
    with source.open() as f, (out/'data.txt').open('w') as dst:
        d,total,metric=map(int,f.readline().split()); assert d==128 and total>=n and metric==2
        dst.write(f'128 {n} 2\n')
        for _ in range(n):
            line=f.readline(); vals=list(map(float,line.split()))
            assert len(vals)==128 and all(v==int(v) and 0<=v<=255 for v in vals)
            clean=' '.join(str(int(v)) for v in vals)+'\n';dst.write(clean);h.update(clean.encode())
    for q in [32,128]:
        (out/f'q{q}.txt').write_text(str(q)+'\n'+'\n'.join(str(i*n//q) for i in range(q))+'\n')
    (out/'manifest.json').write_text(json.dumps({'n':n,'d':128,'metric':2,'selection':'first N; floor(i*N/Q)',
        'canonical_rows_sha256':h.hexdigest(),'file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.txt')}},indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='mode',required=True)
    p=sp.add_parser('source');p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('--height',type=int,choices=[3,5],required=True)
    p=sp.add_parser('fixture');p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('--n',type=int,choices=[2000,65536],required=True)
    a=ap.parse_args()
    if a.mode=='source':prepare(a.source,a.out,a.height)
    else:fixture(a.source,a.out,a.n)
