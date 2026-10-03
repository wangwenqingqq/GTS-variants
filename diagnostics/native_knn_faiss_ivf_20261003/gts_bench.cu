// Original GTS V2 with full sorted-neighbor output for diagnostic comparison.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <thrust/sort.h>
#include <thrust/reduce.h>
#include <thrust/scan.h>
#include <thrust/count.h>
#include <nvtx3/nvToolsExt.h>
#include "tree.cuh"
#include "search_v2.cuh"
#undef short
using Clock = std::chrono::steady_clock;
static void require(bool ok, const char* message) { if(!ok) throw std::runtime_error(message); }
static void ck(cudaError_t e) { if(e != cudaSuccess) throw std::runtime_error(cudaGetErrorString(e)); }
static double elapsed(Clock::time_point t) { return std::chrono::duration<double,std::milli>(Clock::now()-t).count(); }
template<class T> void write_vec(std::ofstream& f, const std::vector<T>& v) {
    f.write(reinterpret_cast<const char*>(v.data()), v.size()*sizeof(T)); require(bool(f), "write vector");
}
template<class T> void read_device(std::ifstream& f, T*& p, size_t n) {
    std::vector<T> v(n); f.read(reinterpret_cast<char*>(v.data()), n*sizeof(T)); require(bool(f), "cache read");
    ck(cudaMalloc(reinterpret_cast<void**>(&p), n*sizeof(T)));
    ck(cudaMemcpy(p, v.data(), n*sizeof(T), cudaMemcpyHostToDevice));
}
template<class T> void write_device(std::ofstream& f, T* p, size_t n) {
    std::vector<T> v(n); ck(cudaMemcpy(v.data(), p, n*sizeof(T), cudaMemcpyDeviceToHost)); write_vec(f,v);
}
int main(int argc, char** argv) try {
    require(argc == 9, "usage: gts_bench data.f32bin qids K B repeats cache output warmup_batches");
    const int k=std::stoi(argv[3]), batch=std::stoi(argv[4]), repeats=std::stoi(argv[5]), warm=std::stoi(argv[8]);
    require(k>0 && k<=32 && (batch==1||batch==32) && repeats>=1 && warm>=0,"arguments outside contract");
    ck(cudaFree(nullptr)); auto setup=Clock::now();
    int *info=nullptr,*qids=nullptr,*ids=nullptr,*max_nodes=nullptr,*empty=nullptr,*sizes=nullptr;
    float* data=nullptr; char* strings=nullptr; TN* nodes=nullptr; int height=0;
    ck(cudaMallocManaged(reinterpret_cast<void**>(&info),3*sizeof(int)));
    std::ifstream input(argv[1],std::ios::binary); require(bool(input),"open data");
    input.read(reinterpret_cast<char*>(info),12); require(bool(input),"data header");
    const int d=info[0], n=info[1];
    require((d==96||d==960) && n>=4097 && n<=1000000 && info[2]==2,"data outside contract");
    ck(cudaMalloc(reinterpret_cast<void**>(&data),size_t(n)*d*sizeof(float)));
    const size_t chunk=16*1024*1024; std::vector<float> block(std::min(chunk,size_t(n)*d));
    for(size_t offset=0;offset<size_t(n)*d;offset+=block.size()) {
        size_t count=std::min(block.size(),size_t(n)*d-offset);
        input.read(reinterpret_cast<char*>(block.data()),count*sizeof(float)); require(bool(input),"data payload");
        ck(cudaMemcpy(data+offset,block.data(),count*sizeof(float),cudaMemcpyHostToDevice));
    }
    input.close(); block.clear(); block.shrink_to_fit();
    std::ifstream queries(argv[2]); int q=0; queries>>q; require(q>=1,"query count");
    std::vector<int> query_ids(q); for(int& id:query_ids) {queries>>id; require(bool(queries)&&id>=0&&id<n,"query ID");}
    int extra=0; require(!(queries>>extra),"extra query IDs");
    ck(cudaMallocManaged(reinterpret_cast<void**>(&qids),batch*sizeof(int)));
    double data_setup_ms=elapsed(setup); auto index_begin=Clock::now();
    std::ifstream cache(argv[6],std::ios::binary); bool cache_loaded=bool(cache);
    if(cache_loaded) {
        int h[4]; cache.read(reinterpret_cast<char*>(h),sizeof(h));
        require(bool(cache)&&h[0]==n&&h[1]==d&&h[2]>=3&&h[2]<=6&&h[3]>0,"bad index cache"); height=h[2];
        ck(cudaMallocManaged(reinterpret_cast<void**>(&max_nodes),sizeof(int))); max_nodes[0]=h[3];
        read_device(cache,ids,n); read_device(cache,nodes,h[3]); read_device(cache,empty,h[3]);
    } else {
        nvtxRangePushA("static.index_build");
        indexConstru(data,strings,sizes,info,ids,nodes,max_nodes,height,empty);
        ck(cudaDeviceSynchronize()); nvtxRangePop();
        std::vector<int> permutation(n), flags(max_nodes[0]); std::vector<TN> host_nodes(max_nodes[0]);
        ck(cudaMemcpy(permutation.data(),ids,n*sizeof(int),cudaMemcpyDeviceToHost));
        ck(cudaMemcpy(flags.data(),empty,flags.size()*sizeof(int),cudaMemcpyDeviceToHost));
        ck(cudaMemcpy(host_nodes.data(),nodes,host_nodes.size()*sizeof(TN),cudaMemcpyDeviceToHost));
        auto sorted=permutation; std::sort(sorted.begin(),sorted.end());
        for(int i=0;i<n;++i) require(sorted[i]==i,"index ID permutation");
        long long coverage=0;
        for(size_t i=0;i<flags.size();++i) if(flags[i]==0&&host_nodes[i].is_leaf) {
            const TN node=host_nodes[i]; require(node.size>0&&node.size<=MAX_SIZE&&node.lid>=0&&node.lid+node.size<=n,"leaf capacity");
            coverage+=node.size;
        }
        require(coverage==n,"incomplete leaf coverage");
        std::ofstream out(argv[6],std::ios::binary); int h[4]={n,d,height,max_nodes[0]}; out.write(reinterpret_cast<char*>(h),sizeof(h));
        write_device(out,ids,n); write_device(out,nodes,max_nodes[0]); write_device(out,empty,max_nodes[0]);
    }
    start_idx=0; for(int level=0,width=1;level<height-1;++level,width*=TREE_ORDER) start_idx+=width;
    double index_setup_ms=elapsed(index_begin);
    std::vector<int> result_ids(size_t(q)*k); std::vector<float> result_dist(size_t(q)*k);
    auto run_batch=[&](int start,int count,bool collect) {
        nvtxRangePushA("query.gts.host_ready");
        ck(cudaMemcpy(qids,query_ids.data()+start,count*sizeof(int),cudaMemcpyHostToDevice));
        update_disk=false;
        searchIndexKnnV2(data,nodes,ids,max_nodes,qids,count,k,height,info,empty,strings,sizes);
        if(collect) {
            ck(cudaMemcpy(result_ids.data()+size_t(start)*k,diag_ids,size_t(count)*k*sizeof(int),cudaMemcpyDeviceToHost));
            ck(cudaMemcpy(result_dist.data()+size_t(start)*k,diag_dist,size_t(count)*k*sizeof(float),cudaMemcpyDeviceToHost));
        } else {
            std::vector<int> wi(size_t(count)*k); std::vector<float> wd(size_t(count)*k);
            ck(cudaMemcpy(wi.data(),diag_ids,wi.size()*sizeof(int),cudaMemcpyDeviceToHost));
            ck(cudaMemcpy(wd.data(),diag_dist,wd.size()*sizeof(float),cudaMemcpyDeviceToHost));
        }
        ck(cudaFree(diag_ids)); ck(cudaFree(diag_dist)); ck(cudaFree(res_dis));
        diag_ids=nullptr;diag_dist=nullptr;res_dis=nullptr;
        ck(cudaDeviceSynchronize());nvtxRangePop();
    };
    for(int i=0;i<warm;++i) run_batch(0,std::min(batch,q),false);
    std::ofstream csv(std::string(argv[7])+".csv"); csv<<"sample,total_ms,batch_p50_ms,batch_p95_ms\n"<<std::setprecision(12);
    for(int repeat=0;repeat<repeats;++repeat) {
        std::vector<double> batch_ms; auto begin=Clock::now(); nvtxRangePushA("formal.query_pass");
        for(int start=0;start<q;start+=batch) {auto t=Clock::now();run_batch(start,std::min(batch,q-start),true);batch_ms.push_back(elapsed(t));}
        nvtxRangePop(); double total_ms=elapsed(begin);
        std::sort(batch_ms.begin(),batch_ms.end());
        csv<<repeat<<','<<total_ms<<','<<batch_ms[batch_ms.size()/2]<<','<<batch_ms[std::min(batch_ms.size()-1,size_t(batch_ms.size()*.95))]<<'\n';csv.flush();
        for(int row=0;row<q;++row) {
            std::vector<int> seen;
            for(int rank=0;rank<k;++rank) {
                size_t pos=size_t(row)*k+rank;
                require(result_ids[pos]>=0&&result_ids[pos]<n&&std::isfinite(result_dist[pos])&&result_dist[pos]<INFI_DIS,"invalid neighbor");
                seen.push_back(result_ids[pos]);
            }
            std::sort(seen.begin(),seen.end());require(std::adjacent_find(seen.begin(),seen.end())==seen.end(),"duplicate neighbor");
        }
    }
    std::ofstream output(std::string(argv[7])+".bin",std::ios::binary); int h[4]={n,d,q,k};output.write(reinterpret_cast<char*>(h),sizeof(h));
    write_vec(output,result_ids);write_vec(output,result_dist);
    std::cout<<"RESULT {\"N\":"<<n<<",\"D\":"<<d<<",\"Q\":"<<q<<",\"K\":"<<k<<",\"B\":"<<batch
             <<",\"height\":"<<height<<",\"cache_loaded\":"<<(cache_loaded?"true":"false")
             <<",\"data_setup_ms\":"<<data_setup_ms<<",\"index_setup_ms\":"<<index_setup_ms<<"}"<<std::endl;
    for(void* p:{(void*)info,(void*)qids,(void*)ids,(void*)max_nodes,(void*)empty,(void*)data,(void*)nodes})if(p)ck(cudaFree(p));
    return 0;
} catch(const std::exception& e) {std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
