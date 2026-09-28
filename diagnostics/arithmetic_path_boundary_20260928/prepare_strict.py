#!/usr/bin/env python3
"""Extend the pinned compact driver with common strict L2 backends."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPACT = HERE.parent / "fixed_cutoff_20260927" / "prepare_compact.py"


def once(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


def render(out):
    spec = importlib.util.spec_from_file_location("prepare_compact", COMPACT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.make(out)
    s = (out / "graph_bench.cu").read_text()
    s = once(s, "#include <cub/cub.cuh>",
             "#include <cub/cub.cuh>\n#include <cstdlib>\n#include <thrust/iterator/counting_iterator.h>")
    s = s.replace("cub::CountingInputIterator<int>", "thrust::counting_iterator<int>")
    s = once(s, '#include "compact_cutoff.cuh"',
             '#include "compact_cutoff.cuh"\n#include "strict_l2.cuh"')
    s = once(s, "    bool fused;\n", "    bool fused;\n    bool strict, fast;\n    unsigned long long *lower, *upper;\n")
    s = once(s, "const std::vector<int>* host_empty=nullptr):fused(f),traversal(t)",
             "const std::vector<int>* host_empty=nullptr,bool sm=false,bool fm=false,unsigned long long* lb=nullptr,unsigned long long* ub=nullptr):fused(f),strict(sm),fast(fm),lower(lb),upper(ub),traversal(t)")
    s = s.replace("if(leaf_mode==4)", "if(leaf_mode==4||leaf_mode==6)")
    s = once(s, "    void enqueue(float radius) {\n        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));",
             '''    void enqueue(float radius) {
        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));
        if(strict) {
            const int d=data_info[0];
            if(leaf_mode==5) {
                if(fast)strict_flat<true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);
                else strict_flat<false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);
                ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
                flatResultSelect<<<1,512,0,stream>>>(n,hits,rawids,rawdis,is_delete_prefix,count,outids,outdis);
            } else {
                initQnode<<<(nodes+511)/512,THREAD_NUM,0,stream>>>(flags,1,max_node_num);
                int start=1,width=TREE_ORDER;
                const int last=leaf_mode==6?stop_depth:height-1;
                for(int level=1;level<=last;++level) {
                    if(fast) strict_walk<true><<<(width+511)/512,512,0,stream>>>(flags,start,node_list,radius,data_d,qid,width,d,empty_list,lower,upper);
                    else strict_walk<false><<<(width+511)/512,512,0,stream>>>(flags,start,node_list,radius,data_d,qid,width,d,empty_list,lower,upper);
                    clear_parents<<<(width/TREE_ORDER+511)/512,512,0,stream>>>(flags,start,width);
                    start+=width;width*=TREE_ORDER;
                }
                if(leaf_mode==6) {
                    frontierFlags<<<(n+511)/512,512,0,stream>>>(n,node_for_pos,flags,active);
                    thrust::counting_iterator<int> positions(0);
                    ck(cub::DeviceSelect::Flagged(temp,tempbytes,positions,active,candidate_positions,candidate_count,n,stream));
                    if(fast)strict_compact<true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,candidate_positions,candidate_count,hits,rawids,rawdis);
                    else strict_compact<false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,candidate_positions,candidate_count,hits,rawids,rawdis);
                    ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
                    compactResultSelect<<<1,512,0,stream>>>(candidate_count,n,hits,rawids,rawdis,is_delete_prefix,count,outids,outdis);
                } else {
                    ck(cub::DeviceReduce::Sum(temp,tempbytes,flags,candidate_count,nodes,stream));
                    initRes<<<(slots+511)/512,512,0,stream>>>(hits,slots);
                    ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,flags,nodeidx,nodes,stream));
                    mergeLeafNode<<<(nodes+511)/512,512,0,stream>>>(flags,nodeidx,candidates,max_node_num,1,queryids,0);
                    if(fast)strict_leaf<true><<<nodes,512,0,stream>>>(candidates,node_list,id_list,data_d,qid,d,radius,hits,rawids,rawdis,candidate_count);
                    else strict_leaf<false><<<nodes,512,0,stream>>>(candidates,node_list,id_list,data_d,qid,d,radius,hits,rawids,rawdis,candidate_count);
                    ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
                    fusedResultSelect<<<1,512,0,stream>>>(candidate_count,hits,rawids,rawdis,is_delete_prefix,count,outids,outdis,nodes);
                }
            }
            ck(cudaMemcpyAsync(hc,count,sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hi,outids,slots*sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hd,outdis,slots*sizeof(float),cudaMemcpyDeviceToHost,stream));
            ck(cudaGetLastError());return;
        }''')
    refit = '''
double buildStrictBounds(const std::vector<TN>& tree,const std::vector<int>& empty,
                         int n,int d,int height,unsigned long long*& low,
                         unsigned long long*& high,uint64_t& digest_out) {
    auto begin=Clock::now();const int nodes=int(tree.size());
    std::vector<unsigned long long> lo(nodes,~0ull),hi(nodes,0);
    alloc(low,nodes);alloc(high,nodes);
    ck(cudaMemcpy(low,lo.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
    ck(cudaMemcpy(high,hi.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
    int* dev_map;alloc(dev_map,n);std::vector<int> mapping(n);
    int start=1,width=TREE_ORDER;
    for(int level=1;level<height;++level) {
        std::fill(mapping.begin(),mapping.end(),-1);
        assert(start+width<=nodes);
        for(int nid=start;nid<start+width;++nid)if(empty[nid]==0) {
            const TN node=tree[nid];
            assert(node.pid>=0&&node.pid<n&&node.lid>=0&&node.size>0&&node.lid+node.size<=n);
            for(int pos=node.lid;pos<node.lid+node.size;++pos){assert(mapping[pos]==-1);mapping[pos]=nid;}
        }
        assert(std::all_of(mapping.begin(),mapping.end(),[](int x){return x>=0;}));
        ck(cudaMemcpy(dev_map,mapping.data(),n*sizeof(int),cudaMemcpyHostToDevice));
        refit_bounds<<<(n+255)/256,256>>>(dev_map,id_list,node_list,data_d,n,d,low,high);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());
        start+=width;width*=TREE_ORDER;
    }
    ck(cudaMemcpy(lo.data(),low,nodes*sizeof(unsigned long long),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(hi.data(),high,nodes*sizeof(unsigned long long),cudaMemcpyDeviceToHost));
    uint64_t hash=1469598103934665603ull;
    for(int nid=1;nid<nodes;++nid)if(empty[nid]==0) {
        assert(lo[nid]!=~0ull&&hi[nid]!=0&&lo[nid]<=hi[nid]);
        hash=(hash^lo[nid])*1099511628211ull;
        hash=(hash^hi[nid])*1099511628211ull;
    }
    digest_out=hash;ck(cudaFree(dev_map));return seconds(begin);
}

'''
    s = once(s, "int main(int argc,char** argv) {", refit + "int main(int argc,char** argv) {")
    s = once(s, "bool dump=std::stoi(argv[8]);", '''bool dump=std::stoi(argv[8]);
    const bool strict=mode=="FR"||mode=="FF"||mode=="TR"||mode=="TF"||
        mode=="CR1"||mode=="CR2"||mode=="CR3"||mode=="CR4"||mode=="CR5"||
        mode=="CF1"||mode=="CF2"||mode=="CF3"||mode=="CF4"||mode=="CF5";
    const bool fast=strict&&mode[1]=='F';''')
    s = once(s, 'mode=="C5") && repeats>0', 'mode=="C5"||strict) && repeats>0')
    s = once(s, "    qnum_leaf=1;", '''    unsigned long long *strict_low=nullptr,*strict_high=nullptr;
    uint64_t bound_hash=0;double refit_s=0;
    if(strict)refit_s=buildStrictBounds(tree,empty,data_info[1],data_info[0],tree_h,
                                       strict_low,strict_high,bound_hash);
    qnum_leaf=1;''')
    s = once(s, "    for(int id:ids){assert(id>=0&&id<data_info[1]);assert(++seen[id]==1);}",
             '''    uint64_t idlist_hash=1469598103934665603ull;
    for(int id:ids){assert(id>=0&&id<data_info[1]);assert(++seen[id]==1);
        idlist_hash=(idlist_hash^uint32_t(id))*1099511628211ull;}
    if(strict)if(const char* path=getenv("GTS_DUMP_IDLIST")) {
        std::ofstream order(path,std::ios::binary);
        order.write(reinterpret_cast<const char*>(ids.data()),ids.size()*sizeof(int));
        assert(bool(order));
    }''')
    old = '''Fixed* fixed=mode=="A"?nullptr:new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:(mode[0]=='C'?4:3))),(mode[0]=='D'||mode[0]=='C')?mode[1]-'0':0,&tree,&empty);'''
    new = '''int leaf_mode=strict?(mode[0]=='F'?5:(mode[0]=='C'?6:7)):
        (mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:(mode[0]=='C'?4:3))));
    int depth=strict?(mode[0]=='C'?mode[2]-'0':0):
        ((mode[0]=='D'||mode[0]=='C')?mode[1]-'0':0);
    Fixed* fixed=new Fixed(tree_size,tree_h,true,2,true,leaf_mode,depth,&tree,&empty,
                           strict,fast,strict_low,strict_high);'''
    s = once(s, old, new)
    s = once(s, '''if(mode=="Q"||mode=="H"||mode=="J"||mode=="F"||mode=="D1"||mode=="D2"||mode=="D3"||mode=="D4"||mode=="D5"||mode=="C1"||mode=="C2"||mode=="C3"||mode=="C4"||mode=="C5"){*fixed->hq=queries[0];capture_s=fixed->capture(radius);}''',
             '''*fixed->hq=queries[0];capture_s=fixed->capture(radius);''')
    s = once(s, '''fixed->query(q,radius,mode=="Q"||mode=="H"||mode=="J"||mode=="F"||mode=="D1"||mode=="D2"||mode=="D3"||mode=="D4"||mode=="D5"||mode=="C1"||mode=="C2"||mode=="C3"||mode=="C4"||mode=="C5")''',
             '''fixed->query(q,radius,true)''')
    s = once(s, '''std::ofstream full,work; if(dump){full.open(out+".results");full<<std::setprecision(9);work.open(out+".work.csv");work<<"qid,candidates\\n";}''',
             '''std::ofstream full,work,binary;
    if(dump){
        if(strict)binary.open(out+".bin",std::ios::binary);
        else {full.open(out+".results");full<<std::setprecision(9);}
        work.open(out+".work.csv");work<<"qid,candidates\\n";
    }''')
    s = once(s, '''if(dump){full<<q<<' '<<count;for(int i=0;i<count;++i)full<<' '<<ids[i]<<':'<<ds[i];full<<'\\n';}''',
             '''if(dump){
            if(strict){
                binary.write(reinterpret_cast<const char*>(&q),sizeof(q));
                binary.write(reinterpret_cast<const char*>(&count),sizeof(count));
                binary.write(reinterpret_cast<const char*>(ids),size_t(count)*sizeof(int));
                binary.write(reinterpret_cast<const char*>(ds),size_t(count)*sizeof(float));
                assert(bool(binary));
            } else {full<<q<<' '<<count;for(int i=0;i<count;++i)full<<' '<<ids[i]<<':'<<ds[i];full<<'\\n';}
        }''')
    s = once(s, '''<<",\\\"setup_s\\\":"<<setup_s''', '''<<",\\\"refit_s\\\":"<<refit_s<<",\\\"bounds_hash\\\":"<<bound_hash<<",\\\"setup_s\\\":"<<setup_s''')
    s = once(s, '''<<",\\\"used_nodes\\\":"<<used_nodes''', '''<<",\\\"idlist_hash\\\":"<<idlist_hash<<",\\\"used_nodes\\\":"<<used_nodes''')
    s = once(s, "    delete fixed;", "    delete fixed;\n    if(strict_low)ck(cudaFree(strict_low));if(strict_high)ck(cudaFree(strict_high));")
    (out / "graph_bench.cu").write_text(s)
    (out / "strict_l2.cuh").write_bytes((HERE / "strict_l2.cuh").read_bytes())
    runner = (out / "run.py").read_text()
    runner = once(runner, "'C3','C4','C5']", "'C3','C4','C5','FR','FF','TR','TF','CR1','CR2','CR3','CR4','CR5','CF1','CF2','CF3','CF4','CF5']")
    runner = once(runner, "gold=root/'fixtures'/f'expected_{radius:g}.json'", "gold=root/'fixtures'/f'expected_{radius:g}.json' if mode not in ('FR','FF','TR','TF','CR1','CR2','CR3','CR4','CR5','CF1','CF2','CF3','CF4','CF5') else root/'fixtures'/'strict_external_audit_required.json'")
    runner = once(runner, "p.add_argument('--dump',action='store_true')",
                  "p.add_argument('--dump',action='store_true');p.add_argument('--qfile',default='queries.qid');p.add_argument('--binary',default='graph_bench')")
    runner = once(runner, "a.repeats,a.warmup,a.tool,a.dump)",
                  "a.repeats,a.warmup,a.tool,a.dump,a.qfile,a.binary)")
    (out / "run.py").write_text(runner)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    a = p.parse_args()
    render(a.out)
