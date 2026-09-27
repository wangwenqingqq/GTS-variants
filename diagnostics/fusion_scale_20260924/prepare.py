#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
fusion=load('scale_fusion',HERE.parent/'fused_result_20260923/prepare.py')
once=fusion.replace_once
def driver():
    s=fusion.transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
    s=once(s,'struct Fixed {','int query_slots=0,used_nodes=0,leaf_nodes=0;\n\nstruct Fixed {')
    s=once(s,'const int nodes=111, slots=2220;','const int nodes, slots;')
    s=once(s,':fused(f),n(count_n),height(h)',':fused(f),nodes(max_node_num[0]),slots(nodes*20),n(count_n),height(h)')
    s=once(s,'initQnode<<<1,THREAD_NUM,0,stream>>>','initQnode<<<(nodes+511)/512,THREAD_NUM,0,stream>>>')
    s=once(s,'mergeLeafNode<<<1,512,0,stream>>>','mergeLeafNode<<<(nodes+511)/512,512,0,stream>>>')
    s=once(s,'is_delete_prefix,count,outids,outdis);','is_delete_prefix,count,outids,outdis,nodes);')
    s=once(s,'count<=2220','count<=query_slots')
    s=once(s,'assert(data_info[1]==2000 && data_info[2]==6);','''assert(data_info[1]>=2000 && data_info[1]<=256000 && data_info[2]==6);
    MAX_H=1;for(int worst=data_info[1];worst>20;worst-=9*(worst/10))++MAX_H;
    assert(MAX_H>=3 && MAX_H<=6);''')
    start=s.index('    assert(tree_h==3');end=s.index('    tree_size=data_info[1];',start)
    s=s[:start]+'''    assert(tree_h==MAX_H && MAX_SIZE==20 && TREE_ORDER==10);
    query_slots=max_node_num[0]*20;
    std::vector<TN> tree(max_node_num[0]);std::vector<int> empty(max_node_num[0]),ids(data_info[1]),seen(data_info[1],0),cover(data_info[1],0);
    ck(cudaMemcpy(tree.data(),node_list,tree.size()*sizeof(TN),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(empty.data(),empty_list,empty.size()*sizeof(int),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(ids.data(),id_list,ids.size()*sizeof(int),cudaMemcpyDeviceToHost));
    for(int id:ids){assert(id>=0&&id<data_info[1]);assert(++seen[id]==1);}
    for(size_t i=0;i<tree.size();++i)if(empty[i]==0){
        ++used_nodes;auto node=tree[i];assert(node.size>0&&node.lid>=0&&node.lid+node.size<=data_info[1]);
        if(node.is_leaf==1){++leaf_nodes;assert(node.size<=20);for(int j=node.lid;j<node.lid+node.size;++j)assert(++cover[j]==1);}
    }
    assert(std::all_of(cover.begin(),cover.end(),[](int x){return x==1;}));
    qnum_leaf=1;
'''+s[end:]
    s=once(s,'std::vector<int> host_ids(2220);std::vector<float> host_ds(2220);','std::vector<int> host_ids(query_slots);std::vector<float> host_ds(query_slots);')
    s=once(s,'std::ofstream full; if(dump)full.open(out+".results");','std::ofstream full,work; if(dump){full.open(out+".results");work.open(out+".work.csv");work<<"qid,candidates\\n";}')
    s=once(s,'        if(dump){full<<q', '        if(dump && fixed){int nc;ck(cudaMemcpy(&nc,fixed->candidate_count,4,cudaMemcpyDeviceToHost));work<<q<<\',\'<<nc<<\'\\n\';}\n        if(dump){full<<q')
    s=once(s,'<<",\\"setup_s\\":"<<setup_s','<<",\\"n\\":"<<tree_size<<",\\"tree_height\\":"<<tree_h<<",\\"nodes\\":"<<max_node_num[0]<<",\\"slots\\":"<<query_slots<<",\\"used_nodes\\":"<<used_nodes<<",\\"leaves\\":"<<leaf_nodes\n      <<",\\"setup_s\\":"<<setup_s')
    return s
def selector():
    s=(fusion.HERE/'fused_result.cuh').read_text()
    s=once(s,'int* outids, float* outdis)','int* outids, float* outdis, int capacity)')
    return once(s,'*candidates<=111','*candidates<=capacity')
def test_selector():
    s=(fusion.HERE/'test_selector.cu').read_text()
    s=once(s,'for(int fresh=0;fresh<3;++fresh){','for(int cap:{111,1111,11111,111111}){int slots=cap*20;')
    s=s.replace('2222','(slots+2)').replace('2220','slots').replace('8880','(slots*4)')
    s=once(s,'{111,1,0,110,26,25,52,51,2,111,0}','{cap,1,0,cap-1,26,25,52,51,2,cap,0}')
    s=once(s,'prefix,count,oi,od);','prefix,count,oi,od,cap);')
    return s
def runner():
    s=(HERE.parent/'graph_query_20260923/run.py').read_text()
    s=once(s,'tool,dump):','tool,dump,qfile="queries.qid",binary="graph_bench"):')
    s=s.replace("root/'bin/graph_bench'","root/'bin'/binary").replace("root/'fixtures/words_2000.txt'","root/'fixtures/data.txt'").replace("root/'fixtures/queries.qid'","root/'fixtures'/qfile")
    s=once(s,"    if tool.startswith('nsys'):","    nq=int((root/'fixtures'/qfile).read_text().split()[0])\n    if mode=='T':cmd=[str(root/'bin/test_selector')]\n    if tool.startswith('nsys'):")
    s=once(s,"limit=120 if tool=='clean' or tool.startswith('nsys') else 600","limit=600 if tool=='clean' or tool.startswith('nsys') else 1800")
    s=s.replace('repeats*64','repeats*nq').replace("nextcheck=start+1","nextcheck=start+.2").replace("nextcheck=time.monotonic()+1","nextcheck=time.monotonic()+.2").replace('time.sleep(.1)','time.sleep(.02)')
    s=once(s,"if 'error:' in x.lower()", "if '==ERROR==' in x or 'error:' in x.lower()")
    s=once(s,"    record={'label':label", "    if mode=='T':validation={'pass':'PASS selector 176 cases' in logs,'scope':'dynamic capacity selector regression'}\n    record={'qfile':qfile,'binary':binary,'input_sha256':{n:hashlib.sha256((root/'fixtures'/n).read_bytes()).hexdigest() for n in ['data.txt',qfile]},'label':label")
    s=s.replace("choices=['A','B','C']","choices=['A','B','C','D','E','T']").replace("'synccheck','initcheck']","'synccheck','initcheck','racecheck']")
    s=s.replace("with open('/tmp/gtspp_gpu'+index+'.lock','a')", "with open('/tmp/gtspp_gpu'+index+'.lock','r+')")
    return s
def prepare(source,out):
    assert not out.exists();out.mkdir(parents=True)
    for d in ['bin','logs','static']:(out/d).mkdir()
    pins={n:h for n,h in json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256'].items() if n.startswith('GTS/')}
    for n,h in pins.items():
        assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
        dest=out/'source'/n.removeprefix('GTS/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/n,dest)
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    for name,value in [('graph_bench.cu',driver()),('fused_result.cuh',selector()),('test_selector.cu',test_selector()),('run.py',runner())]:(out/name).write_text(value)
    for name in ['CONTRACT.md','suite.py','verify.py']:shutil.copy2(HERE/name,out/name)
    print('PASS generated dynamic capacity control/fusion, original source unchanged')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.source,a.output)
