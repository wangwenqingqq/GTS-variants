#include <cuda_runtime.h>
#include <nvtx3/nvToolsExt.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include "knn_cutoff.cuh"
#include "knn_select.cuh"
#include "knn_verify.cuh"
using Clock=std::chrono::steady_clock;
void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
void check(bool a,const char* text){if(!a)throw std::runtime_error(text);}
double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
template<class T>T* alloc(size_t n){T* p;ck(cudaMalloc((void**)&p,n*sizeof(T)));return p;}
template<class T>void read(std::ifstream& f,std::vector<T>& v){f.read((char*)v.data(),v.size()*sizeof(T));check(bool(f),"short input");}
std::vector<int> qids(const std::string& path){std::ifstream f(path);int n;f>>n;check(bool(f)&&n>0,"qids header");std::vector<int> a(n);for(int& x:a)f>>x;check(bool(f),"qids payload");return a;}

int main(int argc,char** argv)try {
    check(argc==11,"usage: opt data qids tree.index seeds.i32 MODE K B out warm.qid force_all");
    std::string mode=argv[5],out=argv[8];int k=std::stoi(argv[6]),b=std::stoi(argv[7]);
    bool bound=mode!="O_FULL",masked=mode=="O_MASK",force_all=std::stoi(argv[10])!=0;
    check((mode=="O_FULL"||mode=="O_BOUND"||masked)&&(k==8||k==32)&&(b==1||b==32),"mode/K/B");
    ck(cudaFree(nullptr));auto setup=Clock::now();
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);
    int d=h[0],n=h[1];check(bool(f)&&h[2]==2&&(d==96||d==960)&&n>=k,"data header");
    std::vector<float> host_data(size_t(n)*d);read(f,host_data);
    for(float x:host_data)check(std::isfinite(x),"nonfinite input");
    auto queries=qids(argv[2]),warm=qids(argv[9]);
    for(int x:queries)check(x>=0&&x<n,"query range");for(int x:warm)check(x>=0&&x<n,"warm range");
    std::ifstream index_file(argv[3],std::ios::binary);int ih[4];index_file.read((char*)ih,16);
    check(bool(index_file)&&ih[0]==n&&ih[1]==d&&ih[3]>0,"tree header");
    int count=ih[3],depth=std::min(d==960?4:1,ih[2]-1);
    std::vector<int> order(n),empty(count);std::vector<TN> nodes(count);
    read(index_file,order);read(index_file,nodes);read(index_file,empty);
    auto sorted=order;std::sort(sorted.begin(),sorted.end());
    for(int i=0;i<n;++i)check(sorted[i]==i,"order permutation");
    int m=std::min(4096,n);std::vector<int> seeds(m);
    std::ifstream sf(argv[4],std::ios::binary);read(sf,seeds);sorted=seeds;std::sort(sorted.begin(),sorted.end());
    check(sorted.front()>=0&&sorted.back()<n&&std::adjacent_find(sorted.begin(),sorted.end())==sorted.end(),"seed IDs");
    float* data=alloc<float>(host_data.size());int* ids_order=alloc<int>(n);
    size_t packed_items=size_t((n+31)/32)*32*d;float* packed=alloc<float>(packed_items);
    ck(cudaMemcpy(data,host_data.data(),host_data.size()*4,cudaMemcpyHostToDevice));
    ck(cudaMemcpy(ids_order,order.data(),n*4,cudaMemcpyHostToDevice));
    pack32<<<(n+511)/512,512>>>(data,ids_order,packed,n,d);ck(cudaGetLastError());ck(cudaDeviceSynchronize());
    double layout_ms=ms(setup);host_data.clear();host_data.shrink_to_fit();
    int* query=alloc<int>(b);int* seed_ids=alloc<int>(m);
    ck(cudaMemcpy(seed_ids,seeds.data(),m*4,cudaMemcpyHostToDevice));
    double* scores=alloc<double>(size_t(n)*b);double* seed_scores=alloc<double>(size_t(m)*b);
    double* cutoff=alloc<double>(b);int* out_ids=alloc<int>(b*k);float* out_dist=alloc<float>(b*k);
    size_t temp_count=size_t((n+255)/256)*k*b;
    Neighbor* tmp_a=alloc<Neighbor>(temp_count);Neighbor* tmp_b=alloc<Neighbor>(temp_count);
    TN* tree=nullptr;int* empty_dev=nullptr;int* flags=nullptr;int* frontier=nullptr;
    uint8_t* mask=nullptr;unsigned long long* lower=nullptr;unsigned long long* upper=nullptr;
    int stride=1,width=10;for(int l=0;l<depth;++l){stride+=width;width*=10;}
    double refit_ms=0.;int fallback_nodes=0,refitted_nodes=0;
    if(masked) {
        auto start=Clock::now();check(stride<=count,"tree depth capacity");
        tree=alloc<TN>(count);empty_dev=alloc<int>(count);lower=alloc<unsigned long long>(count);upper=alloc<unsigned long long>(count);
        ck(cudaMemcpy(tree,nodes.data(),count*sizeof(TN),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(empty_dev,empty.data(),count*4,cudaMemcpyHostToDevice));
        std::vector<unsigned long long> lo(count,0x7ff0000000000000ull),hi(count,0);
        ck(cudaMemcpy(lower,lo.data(),count*8,cudaMemcpyHostToDevice));ck(cudaMemcpy(upper,hi.data(),count*8,cudaMemcpyHostToDevice));
        int* mapping_dev=alloc<int>(n);std::vector<int> mapping(n),last(n,0);int base=1; width=10;
        for(int level=1;level<=depth;++level) {
            std::fill(mapping.begin(),mapping.end(),-1);
            for(int nid=base;nid<base+width;++nid)if(!empty[nid]) {
                TN t=nodes[nid];check(t.pid>=0&&t.pid<n&&t.lid>=0&&t.size>0&&t.lid+t.size<=n,"node bounds");
                TN parent=nodes[(nid-1)/10];
                check(t.lid>=parent.lid&&t.lid+t.size<=parent.lid+parent.size,"node ancestry");
                for(int pos=t.lid;pos<t.lid+t.size;++pos) {
                    check(mapping[pos]<0,"same-level overlap");mapping[pos]=nid;last[pos]=nid;
                }
            }
            ck(cudaMemcpy(mapping_dev,mapping.data(),n*4,cudaMemcpyHostToDevice));
            refit_node_bounds<<<(n+255)/256,256>>>(data,ids_order,mapping_dev,tree,n,d,lower,upper);
            ck(cudaGetLastError());base+=width;width*=10;
        }
        check(std::find(last.begin(),last.end(),0)==last.end(),"frontier partition");
        frontier=alloc<int>(n);ck(cudaMemcpy(frontier,last.data(),n*4,cudaMemcpyHostToDevice));
        ck(cudaFree(mapping_dev));flags=alloc<int>(size_t(stride)*b);mask=alloc<uint8_t>(size_t(n)*b);
        ck(cudaDeviceSynchronize());
        std::vector<double> checked_lo(count),checked_hi(count);
        ck(cudaMemcpy(checked_lo.data(),lower,count*8,cudaMemcpyDeviceToHost));
        ck(cudaMemcpy(checked_hi.data(),upper,count*8,cudaMemcpyDeviceToHost));
        for(int nid=1;nid<stride;++nid)if(!empty[nid]) {
            ++refitted_nodes;
            if(!std::isfinite(checked_lo[nid])||!std::isfinite(checked_hi[nid])||checked_lo[nid]>checked_hi[nid])++fallback_nodes;
        }
        refit_ms=ms(start);
    }
    cudaStream_t stream;ck(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
    auto select=[&](double* source,int* source_order,int nitems,int batch)->Neighbor* {
        int blocks=(nitems+255)/256;
        block_topk<<<dim3(blocks,batch),256,0,stream>>>(source,source_order,nullptr,tmp_a,nitems,k,batch,true);
        Neighbor* a=tmp_a;Neighbor* z=tmp_b;int len=blocks*k;
        while(blocks>1) {
            blocks=(len+255)/256;
            block_topk<<<dim3(blocks,batch),256,0,stream>>>(nullptr,nullptr,a,z,len,k,batch,false);
            std::swap(a,z);len=blocks*k;
        }
        return a;
    };
    cudaGraph_t graph;cudaGraphExec_t graph_exec;
    auto dispatch=[&](int batch) {
        if(bound) {
            nvtxRangePushA("seed");
            seed_distances<<<dim3((m+255)/256,batch),256,0,stream>>>(data,seed_ids,query,seed_scores,m,d,batch);
            Neighbor* result=select(seed_scores,seed_ids,m,batch);
            select_cutoff<<<1,32,0,stream>>>(result,cutoff,k,batch);nvtxRangePop();
        }
        if(masked) {
            nvtxRangePushA("tree_mask");
            if(force_all)ck(cudaMemsetAsync(mask,1,size_t(n)*batch,stream));
            else {
                ck(cudaMemsetAsync(flags,0,size_t(stride)*batch*4,stream));init_root<<<1,32,0,stream>>>(flags,stride,batch);
                int base=1,ww=10;
                for(int level=1;level<=depth;++level) {
                    knn_parent_walk<<<dim3((ww/10+255)/256,batch),256,0,stream>>>(flags,stride,base,ww/10,tree,empty_dev,lower,upper,data,query,cutoff,batch,d);
                    base+=ww;ww*=10;
                }
                knn_mask<<<(size_t(n)*batch+255)/256,256,0,stream>>>(flags,stride,frontier,mask,n,batch);
            }
            nvtxRangePop();
        }
        nvtxRangePushA("distance");
        int qt=b==1?1:2;dim3 grid((n+511)/512,(batch+qt-1)/qt);int shared=qt*d*4;
#define RUN_DISTANCE(QT) \
        if(!bound)verify_distances<QT,false,false><<<grid,512,shared,stream>>>(data,packed,query,cutoff,mask,scores,n,d,batch); \
        else if(masked)verify_distances<QT,true,true><<<grid,512,shared,stream>>>(data,packed,query,cutoff,mask,scores,n,d,batch); \
        else verify_distances<QT,true,false><<<grid,512,shared,stream>>>(data,packed,query,cutoff,mask,scores,n,d,batch);
        if(qt==1){RUN_DISTANCE(1)}else{RUN_DISTANCE(2)}
#undef RUN_DISTANCE
        nvtxRangePop();nvtxRangePushA("topk_merge");Neighbor* result=select(scores,ids_order,n,batch);
        final_output<<<(batch*k+255)/256,256,0,stream>>>(result,out_ids,out_dist,batch,k);nvtxRangePop();ck(cudaGetLastError());
    };
    // Capture each actual batch shape, including a ragged tail, before warmup.
    std::vector<int> shapes={b};int tail=int(queries.size())%b;if(tail&&tail!=b)shapes.push_back(tail);
    std::vector<cudaGraph_t> graphs;std::vector<cudaGraphExec_t> executions;
    auto capture_begin=Clock::now();
    for(int shape:shapes) {
        ck(cudaStreamBeginCapture(stream,cudaStreamCaptureModeGlobal));dispatch(shape);
        ck(cudaStreamEndCapture(stream,&graph));ck(cudaGraphInstantiate(&graph_exec,graph));graphs.push_back(graph);executions.push_back(graph_exec);
    }
    double capture_ms=ms(capture_begin);
    std::vector<int> result_ids(queries.size()*k);std::vector<float> result_dist(queries.size()*k);
    auto batch_run=[&](const int* qs,int count,int offset) {
        ck(cudaMemcpy(query,qs,count*4,cudaMemcpyHostToDevice));
        ck(cudaGraphLaunch(executions[count==b?0:1],stream));
        nvtxRangePushA("delivery");
        ck(cudaMemcpyAsync(result_ids.data()+size_t(offset)*k,out_ids,count*k*4,cudaMemcpyDeviceToHost,stream));
        ck(cudaMemcpyAsync(result_dist.data()+size_t(offset)*k,out_dist,count*k*4,cudaMemcpyDeviceToHost,stream));
        ck(cudaStreamSynchronize(stream));nvtxRangePop();
    };
    for(int w=0;w<2;++w)batch_run(warm.data()+(size_t((w+1)*b)<=warm.size()?w*b:0),std::min(b,int(queries.size())),0);
    std::vector<double> times;times.reserve((queries.size()+b-1)/b);
    nvtxRangePushA("formal.query_pass");auto start=Clock::now();
    for(int first=0;first<int(queries.size());first+=b) {
        auto begin=Clock::now();batch_run(queries.data()+first,std::min(b,int(queries.size())-first),first);times.push_back(ms(begin));
    }
    ck(cudaStreamSynchronize(stream));double total_ms=ms(start);nvtxRangePop();
    for(size_t i=0;i<result_ids.size();++i)check(result_ids[i]>=0&&result_ids[i]<n&&std::isfinite(result_dist[i]),"invalid result");
    std::ofstream output(out+".bin",std::ios::binary);int oh[4]={n,d,int(queries.size()),k};output.write((char*)oh,16);
    output.write((char*)result_ids.data(),result_ids.size()*4);output.write((char*)result_dist.data(),result_dist.size()*4);
    std::ofstream csv(out+".csv");csv<<"batch_index,host_ms\n"<<std::setprecision(12);
    for(size_t i=0;i<times.size();++i)csv<<i<<','<<times[i]<<'\n';
    std::sort(times.begin(),times.end());
    std::ofstream meta(out+".json");meta<<std::setprecision(12)<<"{\"mode\":\""<<mode<<"\",\"N\":"<<n<<",\"D\":"<<d<<",\"K\":"<<k<<",\"B\":"<<b
      <<",\"Q\":"<<queries.size()<<",\"pass_ms\":"<<total_ms<<",\"batch_p50_ms\":"<<times[times.size()/2]<<",\"batch_p95_ms\":"<<times[std::min(times.size()-1,size_t(times.size()*.95))]
      <<",\"data_layout_ms\":"<<layout_ms<<",\"refit_ms\":"<<refit_ms<<",\"capture_ms\":"<<capture_ms<<",\"effective_depth\":"<<depth<<",\"seed_M\":"<<m
      <<",\"score_bytes\":"<<size_t(n)*b*8<<",\"select_workspace_bytes\":"<<temp_count*sizeof(Neighbor)*2<<",\"refitted_nodes\":"<<refitted_nodes<<",\"bound_fallback_nodes\":"<<fallback_nodes<<",\"force_all\":"<<(force_all?"true":"false")<<"}\n";
    // A separate replay exposes every admissible pair for small-table audit.
    // No audit copy or file write occurs in the measured continuous pass.
    if(std::getenv("P7_SMALL_AUDIT")) {
        check(n<=8192,"audit is small-table only");
        std::vector<double> all_scores(size_t(queries.size())*n),all_cutoff(queries.size(),INFINITY);
        std::vector<uint8_t> all_mask(size_t(queries.size())*n,1);
        for(int first=0;first<int(queries.size());first+=b) {
            int batch=std::min(b,int(queries.size())-first);batch_run(queries.data()+first,batch,first);
            ck(cudaMemcpy(all_scores.data()+size_t(first)*n,scores,size_t(batch)*n*8,cudaMemcpyDeviceToHost));
            if(bound)ck(cudaMemcpy(all_cutoff.data()+first,cutoff,batch*8,cudaMemcpyDeviceToHost));
            if(masked)ck(cudaMemcpy(all_mask.data()+size_t(first)*n,mask,size_t(batch)*n,cudaMemcpyDeviceToHost));
        }
        std::ofstream audit(out+".coverage.bin",std::ios::binary);audit.write((char*)oh,16);
        audit.write((char*)all_cutoff.data(),all_cutoff.size()*8);
        audit.write((char*)all_mask.data(),all_mask.size());audit.write((char*)all_scores.data(),all_scores.size()*8);
    }
    for(auto x:executions)ck(cudaGraphExecDestroy(x));for(auto x:graphs)ck(cudaGraphDestroy(x));
    for(void* p:{(void*)data,(void*)packed,(void*)ids_order,(void*)query,(void*)seed_ids,(void*)scores,(void*)seed_scores,(void*)cutoff,(void*)out_ids,(void*)out_dist,(void*)tmp_a,(void*)tmp_b,(void*)tree,(void*)empty_dev,(void*)flags,(void*)frontier,(void*)mask,(void*)lower,(void*)upper})if(p)ck(cudaFree(p));
    ck(cudaStreamDestroy(stream));return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
