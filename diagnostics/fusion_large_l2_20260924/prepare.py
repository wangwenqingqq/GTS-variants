#!/usr/bin/env python3
"""Extend the pinned dynamic-capacity C/E driver only for binary L2 input."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
scale=load('large_scale_prepare',HERE.parent/'fusion_scale_20260924/prepare.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
def driver():
    s=scale.driver()
    s=once(s,'assert(data_info[1]>=2000 && data_info[1]<=256000 && data_info[2]==6);',
           'assert(data_info[1]>=2000 && data_info[1]<=1000000 && data_info[2]==2 && '
           '(data_info[0]==960 || data_info[0]==96 || data_info[0]==2));')
    insert='''// Experiment-only bulk float32 input. Runs before index construction and timers.
void loadBinaryL2(const char* filename) {
    std::ifstream in(filename,std::ios::binary);assert(in.good());
    int header[3];in.read(reinterpret_cast<char*>(header),sizeof(header));assert(in.gcount()==sizeof(header));
    const int dim=header[0], n=header[1], metric=header[2];
    assert(metric==2 && n>=2000 && n<=1000000 && (dim==960 || dim==96 || dim==2));
    ck(cudaMallocManaged((void**)&data_info,3*sizeof(int)));
    for(int i=0;i<3;++i)data_info[i]=header[i];
    const size_t bytes=size_t(n)*size_t(dim)*sizeof(float);
    ck(cudaMallocManaged((void**)&data_d,bytes));
    in.read(reinterpret_cast<char*>(data_d),std::streamsize(bytes));assert(in.gcount()==std::streamsize(bytes));
    char extra;assert(!in.read(&extra,1));data_s=nullptr;size_s=nullptr;
}

'''
    s=once(s,'int main(int argc,char** argv) {',insert+'int main(int argc,char** argv) {')
    s=once(s,'load(argv[1],data_info,data_d,data_s,size_s);','loadBinaryL2(argv[1]);')
    s=once(s,'for(void* p:{(void*)data_info,(void*)data_s,(void*)size_s,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)empty_list})ck(cudaFree(p));',
           'for(void* p:{(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)empty_list})if(p)ck(cudaFree(p));')
    s=once(s,'full.open(out+".results");work.open(out+".work.csv");',
           'full.open(out+".results");full<<std::setprecision(9);work.open(out+".work.csv");')
    return s
def runner():
    s=scale.runner();assert s.count('data.txt')==2
    return s.replace('data.txt','data.f32bin')
def main(source,out):
    assert not out.exists();out.mkdir(parents=True)
    for n in ['bin','logs','static','data','base']:(out/n).mkdir()
    pins={k:v for k,v in json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256'].items() if k.startswith('GTS/')}
    for name,h in pins.items():
        assert sha(source/name)==h,name
        p=out/'source'/name.removeprefix('GTS/');p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,p)
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    (out/'graph_bench.cu').write_text(driver())
    (out/'fused_result.cuh').write_text(scale.selector())
    (out/'run.py').write_text(runner())
    for name in ['CONTRACT.md','fixtures.py','verify.py','suite.py']:shutil.copy2(HERE/name,out/name)
    base=HERE.parent/'fusion_datasets_20260924/local/raw/data'
    for d in ['GIST','Deep','Tloc']:
        dest=out/'base'/d;dest.mkdir()
        for name in ['data.txt','queries.qid','source_indices.json','oracle.json']:
            shutil.copy2(base/d/'fixtures'/name,dest/name)
    print('PASS pinned dynamic C/E source and prior L2 anchors; CPU fixture generation pending')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.source,a.out)
