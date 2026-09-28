#!/usr/bin/env python3
"""Prepare one fixed-2000 C/E binary and the four preserved fixtures."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fusion=load('cross_fusion_prepare',HERE.parent/'fused_result_20260923/prepare.py')
scale=load('cross_scale_prepare',HERE.parent/'fusion_scale_20260924/prepare.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
def driver():
    s=fusion.transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    s=once(s,'assert(data_info[1]==2000 && data_info[2]==6);',
           'assert(data_info[1]==2000 && ((data_info[2]==6) || (data_info[2]==2 && (data_info[0]==960 || data_info[0]==96 || data_info[0]==2))));')
    s=once(s,'std::ofstream full; if(dump)full.open(out+".results");',
           'std::ofstream full; if(dump){full.open(out+".results");full<<std::setprecision(9);}')
    return s
def main(source,words,l2,old,out):
    assert not out.exists();out.mkdir(parents=True)
    for p in ['bin','logs','static','data']:(out/p).mkdir()
    pins={k:v for k,v in json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256'].items() if k.startswith('GTS/')}
    for name,h in pins.items():
        assert sha(source/name)==h,name
        p=out/'source'/name.removeprefix('GTS/');p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,p)
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    (out/'graph_bench.cu').write_text(driver())
    shutil.copy2(fusion.HERE/'fused_result.cuh',out/'fused_result.cuh')
    (out/'run.py').write_text(scale.runner())
    for name in ['CONTRACT.md','suite.py','verify.py']:shutil.copy2(HERE/name,out/name)
    inputs={}
    for dataset in ['Words','GIST','Deep','Tloc']:
        src=(words if dataset=='Words' else l2/dataset)/'fixtures'
        target=out/'data'/dataset/'fixtures';target.mkdir(parents=True)
        (target.parent/'runs').mkdir();(target.parent/'bin').symlink_to('../../bin')
        o=json.loads((src/'oracle.json').read_text())
        names=['data.txt','queries.qid','oracle.json']+(['oracle.bin','indices.json'] if dataset=='Words' else ['source_indices.json'])
        for name in names:shutil.copy2(src/name,target/name)
        if dataset=='Words':
            assert o['n']==2000 and sha(target/'data.txt')==o['sha256']['data.txt']
            assert sha(target/'queries.qid')==o['sha256']['queries.qid']
        else:
            assert o['dataset']==dataset and o['dimension']=={'GIST':960,'Deep':96,'Tloc':2}[dataset]
            assert sha(target/'data.txt')==o['data_sha256'] and sha(target/'queries.qid')==o['qids_sha256']
            assert sha(target/'source_indices.json')==o['source_indices_sha256']
        qs=list(map(int,(target/'queries.qid').read_text().split()));assert qs.pop(0)==len(qs)==64 and len(set(qs))==64
        (target/'check_queries.qid').write_text('8\n'+'\n'.join(map(str,qs[::8]))+'\n')
        inputs[dataset]={name:sha(target/name) for name in names+['check_queries.qid']}
    assert sha(old)==json.loads((HERE.parent/'fused_result_20260923/EVIDENCE.json').read_text())['binary_sha256']
    shutil.copy2(old,out/'bin/graph_bench_anchor')
    (out/'input_sha256.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print('PASS fixed C/E source, four pinned 2000 fixtures, previous Words binary')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source','words','l2','old','out']:p.add_argument(name,type=Path)
    a=p.parse_args();main(a.source,a.words,a.l2,a.old,a.out)
