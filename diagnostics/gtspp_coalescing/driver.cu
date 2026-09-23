#include <algorithm>
#include <chrono>
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
    require(argc==6,"usage: bench data query radius D|B check|timing|profile");
    std::string policy=argv[4],mode=argv[5];require(policy=="D"||policy=="B","invalid policy");require(mode=="check"||mode=="timing"||mode=="profile"||mode=="stress"||mode=="sustained","invalid mode");
    int radius=std::stoi(argv[3]);require(radius==300||radius==500,"invalid radius");
    if(policy=="B")CK(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
    CK(cudaFree(nullptr));unsigned flags=0;CK(cudaGetDeviceFlags(&flags));
    std::printf("policy,%s,%u\n",policy.c_str(),flags);
    int *info=nullptr,*sizes=nullptr,*qids=nullptr,*ids=nullptr,*max_nodes=nullptr,*empty=nullptr;
    float* x=nullptr;char* strings=nullptr;TN* nodes=nullptr;int q=0,height=0;
    load(argv[1],info,x,strings,sizes);loadQuery(argv[2],qids,q);CK(cudaDeviceSynchronize());int n=info[1];
    require(info[0]==128&&info[2]==2&&(n==2000||n==65536)&&(q==32||q==128),"input outside contract");
    for(int i=0;i<n*128;++i)require(x[i]>=0&&x[i]<=255&&x[i]==int(x[i]),"noninteger coordinate");
    std::vector<int> expected(q),actual(q);
    for(int i=0;i<q;++i){require(qids[i]==i*n/q,"unexpected query ID");for(int j=0;j<n;++j){int s=0;for(int k=0;k<128;++k){int d=int(x[qids[i]*128+k])-int(x[j*128+k]);s+=d*d;}expected[i]+=s<=radius*radius;}}
    indexConstru(x,strings,sizes,info,ids,nodes,max_nodes,height,empty);CK(cudaDeviceSynchronize());
    auto run=[&](){searchIndexRnnV2(x,nodes,ids,max_nodes,qids,q,radius,height,info,empty,strings,sizes);
        QueryStages phase;phase.set("stage.delivery");CK(cudaMemcpy(actual.data(),res,q*sizeof(int),cudaMemcpyDeviceToHost));CK(cudaFree(res));res=nullptr;};
    auto check=[&](){require(actual==expected,"count mismatch against integer oracle");};
    run();check();std::puts("correct,full_integer_oracle");
    for(int w=0;w<3;++w){run();check();}
    if(mode=="profile")CK(cudaProfilerStart());
    if(mode=="sustained") {
        std::vector<int> history(64*q);
        double cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID),proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID),start=gts_diag_seconds(CLOCK_MONOTONIC);
        for(int i=0;i<64;++i){run();std::copy(actual.begin(),actual.end(),history.begin()+i*q);}
        double wall=gts_diag_seconds(CLOCK_MONOTONIC)-start;proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID)-proc;cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID)-cpu;
        for(int i=0;i<64;++i)require(std::equal(expected.begin(),expected.end(),history.begin()+i*q),"sustained count mismatch");
        std::printf("batch,64,%.9f,%.9f,%.9f\n",wall,cpu,proc);
    }
    for(int i=0;i<(mode=="sustained"?0:mode=="stress"?64:mode=="timing"?8:3);++i) {
        gts_diag_stats().clear();std::string label="measured.query."+std::to_string(i);nvtxRangePushA(label.c_str());
        double cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID),proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID),start=gts_diag_seconds(CLOCK_MONOTONIC);
        run();double wall=gts_diag_seconds(CLOCK_MONOTONIC)-start;proc=gts_diag_seconds(CLOCK_PROCESS_CPUTIME_ID)-proc;cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID)-cpu;
        nvtxRangePop();check();std::printf("sample,%d,%.9f,%.9f,%.9f\n",i,wall,cpu,proc);
        for(const auto& p:gts_diag_stats())if(p.first.rfind("stage.",0)==0)std::printf("stage,%d,%s,%lu,%.9f,%.9f\n",i,p.first.c_str(),p.second.count,p.second.wall,p.second.cpu);
    }
    if(mode=="profile")CK(cudaProfilerStop());
    for(void* p:{(void*)info,(void*)sizes,(void*)qids,(void*)ids,(void*)max_nodes,(void*)empty,(void*)x,(void*)strings,(void*)nodes,(void*)max_dis_d})if(p)CK(cudaFree(p));
    std::puts("pass");return 0;
}catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
