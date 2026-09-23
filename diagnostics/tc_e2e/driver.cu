// Benchmark driver for pinned GTS copies. Includes host-delivered range counts.
#include "leaf_kernels.cuh"
#include <cassert>
#include <ctime>
#include "gts_cpu_io_profile.hpp"
#include "tree.cuh"
#include "tc_bridge.cuh"
#include "search_v2.cuh"
using Clock=std::chrono::steady_clock;
static double now_cpu() { timespec t{};require(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t)==0,"clock_gettime");return t.tv_sec+t.tv_nsec*1e-9; }
int main(int argc,char** argv) try {
    require(argc==6,"usage: benchmark data query radius order check|timing");
    std::string order=argv[4],mode=argv[5];auto sorted=order;std::sort(sorted.begin(),sorted.end());require(sorted=="DOST","order must contain OSTD exactly once");require(mode=="check"||mode=="timing","invalid mode");
    int radius=std::stoi(argv[3]);require(radius==300||radius==500,"radius outside contract");
    CK(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));CK(cudaFree(nullptr));
    int *info=nullptr,*str_sizes=nullptr,*qids=nullptr,*ids=nullptr,*max_nodes=nullptr,*empty=nullptr;float* x=nullptr;char* strings=nullptr;TN* nodes=nullptr;int q=0,height=0;
    auto t=Clock::now();load(argv[1],info,x,strings,str_sizes);loadQuery(argv[2],qids,q);CK(cudaDeviceSynchronize());
    std::printf("phase,input_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-t).count());
    int n=info[1];require(info[0]==128&&info[2]==2&&(n==2000||n==65536)&&(q==32||q==128),"input outside contract");
    t=Clock::now();std::vector<float> norms(n);for(int i=0;i<n*128;++i){require(x[i]>=0&&x[i]<=255&&x[i]==int(x[i]),"noninteger input");norms[i/128]+=x[i]*x[i];}
    for(int i=0;i<q;++i)require(qids[i]==i*n/q,"unexpected query IDs");
    std::printf("phase,norms_and_input_check_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-t).count());
    t=Clock::now();std::vector<int> expected(q),actual(q);
    for(int i=0;i<q;++i)for(int j=0;j<n;++j){int s=0;for(int k=0;k<128;++k){int v=int(x[qids[i]*128+k])-int(x[j*128+k]);s+=v*v;}expected[i]+=s<=radius*radius;}
    std::printf("phase,oracle_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-t).count());
    t=Clock::now();indexConstru(x,strings,str_sizes,info,ids,nodes,max_nodes,height,empty);CK(cudaDeviceSynchronize());
    std::printf("phase,index_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-t).count());
    t=Clock::now();tc_prepare(n,q,nodes,max_nodes[0],ids,empty,norms);
    std::printf("phase,bridge_setup_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-t).count());
    auto run=[&](char v){tc_variant=v;if(v=='D')tc_dense(x,qids,radius,actual);else {searchIndexRnnV2(x,nodes,ids,max_nodes,qids,q,radius,height,info,empty,strings,str_sizes);CK(cudaMemcpy(actual.data(),res,q*sizeof(int),cudaMemcpyDeviceToHost));CK(cudaFree(res));res=nullptr;}};
    auto check=[&](){require(actual==expected,"range counts differ from integer oracle");};
    for(char v:order){run(v);check();std::printf("correct,%c,full_integer_oracle\n",v);}
    std::printf("shape,%d,%d,%d,%s\n",n,q,radius,order.c_str());
    if(mode=="timing") {
        cudaEvent_t a,b;CK(cudaEventCreate(&a));CK(cudaEventCreate(&b));
        for(char v:order) {
            for(int w=0;w<5;++w){run(v);check();}
            for(int batch:{1,16})for(int sample=0;sample<(batch==1?20:5);++sample) {
                double wall=0,cpu=0,event=0;
                for(int j=0;j<batch;++j){CK(cudaEventRecord(a));double c=now_cpu();auto s=Clock::now();run(v);auto e=Clock::now();cpu+=now_cpu()-c;wall+=std::chrono::duration<double,std::micro>(e-s).count();CK(cudaEventRecord(b));CK(cudaEventSynchronize(b));float ms;CK(cudaEventElapsedTime(&ms,a,b));event+=ms*1000;check();}
                std::printf("sample,%c,%d,%d,%.6f,%.6f,%.6f\n",v,batch,sample,wall/batch,cpu*1e6/batch,event/batch);
            }
            run(v);check();
        }
        CK(cudaEventDestroy(a));CK(cudaEventDestroy(b));
    } else {for(int repeat=0;repeat<4;++repeat)for(char v:order){run(v);check();}}
    tc_release();for(void* p:{(void*)info,(void*)x,(void*)strings,(void*)str_sizes,(void*)qids,(void*)ids,(void*)max_nodes,(void*)empty,(void*)nodes})if(p)CK(cudaFree(p));
    std::puts("pass");return 0;
} catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
