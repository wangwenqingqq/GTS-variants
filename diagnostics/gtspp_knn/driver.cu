#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <vector>
#include <cuda_profiler_api.h>
#include "gts_cpu_io_profile.hpp"
#include "query_stages.hpp"
#define MLP_MAIN_FILE
#define RP_DEFINE_CONSTANTS
#include "tree.cuh"
#include "search_v2.cuh"
static void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
#define CK(x) do {cudaError_t e=(x);if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}while(0)
int main(int argc,char** argv) try {
    require(argc==7,"usage: bench data query k ids|vec|kth|vth check|timing|profile|stress|sustained D");
    int k=std::stoi(argv[3]);std::string api=argv[4],mode=argv[5];
    require(std::string(argv[6])=="D","only unchanged default wait admitted");
    require(k==10||k==100,"k outside contract");require(api=="ids"||api=="vec"||api=="kth"||api=="vth","invalid API");
    require(mode=="check"||mode=="timing"||mode=="profile"||mode=="stress"||mode=="sustained","invalid mode");
    bool full=api=="ids"||api=="vec",vec=api=="vec"||api=="vth";
    CK(cudaFree(nullptr));unsigned flags=0;CK(cudaGetDeviceFlags(&flags));require((flags&7)==0,"wait policy changed");
    int rp_mode=0;CK(cudaMemcpyToSymbol(c_rp_mode,&rp_mode,sizeof(int)));
    std::printf("policy,D,%u\npruning,0\napi,%s\n",flags,api.c_str());
    int *info=nullptr,*sizes=nullptr,*qids=nullptr,*ids=nullptr,*max_nodes=nullptr,*empty=nullptr;
    float* x=nullptr;float* query=nullptr;char* strings=nullptr;TN* nodes=nullptr;int q=0,height=0;
    load(argv[1],info,x,strings,sizes);loadQuery(argv[2],qids,q);CK(cudaDeviceSynchronize());int n=info[1];
    require(info[0]==128&&info[2]==2&&(n==2000||n==65536)&&(q==32||q==128),"input outside contract");
    for(int i=0;i<n*128;++i)require(x[i]>=0&&x[i]<=255&&x[i]==int(x[i]),"noninteger coordinate");
    std::vector<int> sq(q*n),expected(q*k),actual_ids(q*k);
    std::vector<float> actual_dis(q*(full?k:1));
    CK(cudaMallocManaged(&query,q*128*sizeof(float)));
    for(int i=0;i<q;++i){require(qids[i]==i*n/q,"unexpected query ID");std::copy(x+qids[i]*128,x+(qids[i]+1)*128,query+i*128);
        for(int j=0;j<n;++j){int s=0;for(int c=0;c<128;++c){int d=int(x[qids[i]*128+c])-int(x[j*128+c]);s+=d*d;}sq[i*n+j]=s;}
        std::vector<int> row(sq.begin()+i*n,sq.begin()+(i+1)*n);std::nth_element(row.begin(),row.begin()+k,row.end());std::sort(row.begin(),row.begin()+k);std::copy(row.begin(),row.begin()+k,expected.begin()+i*k);
    }
    indexConstru(x,strings,sizes,info,ids,nodes,max_nodes,height,empty);CK(cudaDeviceSynchronize());
    auto run=[&](){require(st.empty(),"nonempty native stack");update_disk=false;int* output_ids=nullptr;
        if(full){QueryStages phase;phase.set("stage.output_alloc");CK(cudaMallocManaged(&output_ids,q*k*sizeof(int)));}
        if(full&&vec)searchIndexKnnV2(x,nodes,ids,max_nodes,query,output_ids,q,k,height,info,empty,strings,sizes);
        else if(full)searchIndexKnnV2(x,nodes,ids,max_nodes,qids,output_ids,q,k,height,info,empty,strings,sizes);
        else if(vec)searchIndexKnnV2(x,nodes,ids,max_nodes,query,q,k,height,info,empty,strings,sizes);
        else searchIndexKnnV2(x,nodes,ids,max_nodes,qids,q,k,height,info,empty,strings,sizes);
        QueryStages phase;phase.set("stage.delivery");
        if(full){CK(cudaMemcpy(actual_ids.data(),output_ids,q*k*sizeof(int),cudaMemcpyDeviceToHost));CK(cudaFree(output_ids));}
        CK(cudaMemcpy(actual_dis.data(),res_dis,actual_dis.size()*sizeof(float),cudaMemcpyDeviceToHost));CK(cudaFree(res_dis));res_dis=nullptr;};
    auto check=[&](const int* result_ids,const float* result_dis){
        for(int i=0;i<q;++i){
            if(!full){require(std::abs(result_dis[i]-std::sqrt(float(expected[i*k+k-1])))<=1e-3f,"kth distance mismatch");continue;}
            std::vector<int> unique(result_ids+i*k,result_ids+(i+1)*k);std::sort(unique.begin(),unique.end());require(std::adjacent_find(unique.begin(),unique.end())==unique.end(),"duplicate ID");
            for(int j=0;j<k;++j){if(j)require(result_dis[i*k+j-1]<=result_dis[i*k+j],"returned distances not sorted");int id=result_ids[i*k+j];if(!std::isfinite(result_dis[i*k+j])||id<0||id>=n||sq[i*n+id]!=expected[i*k+j]||std::abs(result_dis[i*k+j]-std::sqrt(float(sq[i*n+id])))>1e-3f){std::fprintf(stderr,"mismatch q=%d rank=%d id=%d want_sq=%d got_sq=%d got_dist=%f\n",i,j,id,expected[i*k+j],id>=0&&id<n?sq[i*n+id]:-1,result_dis[i*k+j]);throw std::runtime_error("full top-k mismatch");}}
        }
    };
    run();check(actual_ids.data(),actual_dis.data());std::puts("correct,full_integer_topk_oracle");
    for(int w=0;w<3;++w){run();check(actual_ids.data(),actual_dis.data());}
    if(mode=="profile")CK(cudaProfilerStart());
    if(mode=="sustained"){
        std::vector<int> ih(64*actual_ids.size());std::vector<float> dh(64*actual_dis.size());
        double cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID),proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID),start=gts_diag_seconds(CLOCK_MONOTONIC);
        for(int i=0;i<64;++i){run();if(full)std::copy(actual_ids.begin(),actual_ids.end(),ih.begin()+i*actual_ids.size());std::copy(actual_dis.begin(),actual_dis.end(),dh.begin()+i*actual_dis.size());}
        double wall=gts_diag_seconds(CLOCK_MONOTONIC)-start;proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID)-proc;cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID)-cpu;
        for(int i=0;i<64;++i)check(ih.data()+i*actual_ids.size(),dh.data()+i*actual_dis.size());
        std::printf("batch,64,%.9f,%.9f,%.9f\n",wall,cpu,proc);
    }
    for(int i=0;i<(mode=="sustained"?0:mode=="stress"?64:mode=="timing"?8:3);++i){
        gts_diag_stats().clear();std::string label="measured.query."+std::to_string(i);nvtxRangePushA(label.c_str());
        double cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID),proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID),start=gts_diag_seconds(CLOCK_MONOTONIC);
        run();double wall=gts_diag_seconds(CLOCK_MONOTONIC)-start;proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID)-proc;cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID)-cpu;
        nvtxRangePop();check(actual_ids.data(),actual_dis.data());std::printf("sample,%d,%.9f,%.9f,%.9f\n",i,wall,cpu,proc);
        for(const auto& p:gts_diag_stats())if(p.first.rfind("stage.",0)==0)std::printf("stage,%d,%s,%lu,%.9f,%.9f\n",i,p.first.c_str(),p.second.count,p.second.wall,p.second.cpu);
    }
    if(mode=="profile")CK(cudaProfilerStop());
    for(void* p:{(void*)info,(void*)sizes,(void*)qids,(void*)ids,(void*)max_nodes,(void*)empty,(void*)x,(void*)strings,(void*)nodes,(void*)max_dis_d,(void*)query})if(p)CK(cudaFree(p));
    std::puts("pass");return 0;
}catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
