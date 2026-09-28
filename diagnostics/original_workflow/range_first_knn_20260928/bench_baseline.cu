#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "gts_cpu_io_profile.hpp"
#include "query_stages.hpp"
#include "tree.cuh"
#include "search_v2.cuh"
static void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
#define CK(x) do {cudaError_t e=(x);if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}while(0)
static void load_sift(const char* path,int*& info,short*& x){
    std::ifstream in(path,std::ios::binary|std::ios::ate);require(bool(in),"open fvecs");
    std::streamoff bytes=in.tellg();require(bytes>0 && bytes%516==0,"bad fvecs size");
    int n=int(bytes/516);require(n==65536||n==1000000,"N outside pilot");
    in.seekg(0);CK(cudaMallocManaged((void**)&info,3*sizeof(int)));
    info[0]=128;info[1]=n;info[2]=2;
    CK(cudaMallocManaged((void**)&x,size_t(n)*128*sizeof(short)));
    float row[128];
    for(int i=0;i<n;++i){int d=0;in.read((char*)&d,4);require(bool(in)&&d==128,"fvec dimension");
        in.read((char*)row,sizeof(row));require(bool(in),"fvec row");
        for(int j=0;j<128;++j)x[size_t(i)*128+j]=short(row[j]);}
}
int main(int argc,char** argv)try{
    require(argc==5,"usage: bench sift.fvecs qids.txt k radius");
    int k=std::stoi(argv[3]),radius=std::stoi(argv[4]);require(k>0&&k<=100&&radius>0,"bad k/radius");
    CK(cudaFree(nullptr));
    int *info=nullptr,*sizes=nullptr,*qids=nullptr,*ids=nullptr,*max_nodes=nullptr,*empty=nullptr;
    short *x=nullptr;char *strings=nullptr;TN *nodes=nullptr;int q=0,height=0;
    load_sift(argv[1],info,x);loadQuery(argv[2],qids,q);CK(cudaDeviceSynchronize());
    require(q==32,"Q outside pilot");
    std::vector<int> expected(q),actual(q),all(info[1]),inrange(q,0);std::vector<float> delivered(q);
    for(int i=0;i<q;++i){int qi=qids[i];require(qi>=0&&qi<info[1],"bad query id");
        for(int j=0;j<info[1];++j){int sum=0;for(int d=0;d<128;++d){
            int a=int(x[size_t(qi)*128+d]),b=int(x[size_t(j)*128+d]);
            require(a>=0&&a<=255&&b>=0&&b<=255,"non-byte data");int delta=a-b;sum+=delta*delta;}
            all[j]=sum;inrange[i]+=(sum<=radius*radius);}
        std::nth_element(all.begin(),all.begin()+k-1,all.end());expected[i]=all[k-1];}
    int covered=0;long long total_hits=0;int min_hits=info[1],max_hits=0;for(int i=0;i<q;++i){covered+=expected[i]<=radius*radius;total_hits+=inrange[i];min_hits=std::min(min_hits,inrange[i]);max_hits=std::max(max_hits,inrange[i]);}
    std::printf("contract,N,%d,Q,%d,k,%d,r,%d,covered,%d,min_hits,%d,max_hits,%d,total_hits,%lld\n",info[1],q,k,radius,covered,min_hits,max_hits,total_hits);
    indexConstru(x,strings,sizes,info,ids,nodes,max_nodes,height,empty);CK(cudaDeviceSynchronize());
    auto run=[&](){
#ifdef HYBRID
        searchIndexRnnV2(x,nodes,ids,max_nodes,qids,q,float(radius),height,info,empty,strings,sizes,k);
        CK(cudaMemcpy(actual.data(),res,q*sizeof(int),cudaMemcpyDeviceToHost));CK(cudaFree(res));res=nullptr;
        for(int i=0;i<q;++i)delivered[i]=actual[i]>=0?std::sqrt(float(actual[i])):-1.0f;
#else
        update_disk=false;
        searchIndexKnnV2(x,nodes,ids,max_nodes,qids,q,k,height,info,empty,strings,sizes);
        CK(cudaMemcpy(delivered.data(),res_dis,q*sizeof(float),cudaMemcpyDeviceToHost));
        CK(cudaFree(res_dis));res_dis=nullptr;
        for(int i=0;i<q;++i)actual[i]=int(std::lround(double(delivered[i])*double(delivered[i])));
#endif
    };
    auto check=[&](){for(int i=0;i<q;++i)if(std::abs(actual[i]-expected[i])>2 || std::abs(delivered[i]-std::sqrt(float(expected[i])))>0.002f){
        std::fprintf(stderr,"mismatch query=%d expected_sq=%d actual_sq=%d\n",i,expected[i],actual[i]);throw std::runtime_error("oracle mismatch");}};
    run();check();std::puts("correct,integer_kth_oracle");
    for(int i=0;i<3;++i){run();check();}
    for(int i=0;i<8;++i){auto t=std::chrono::steady_clock::now();run();double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t).count();check();
        std::printf("sample,%d,%.6f\n",i,ms);}
    for(void* p:{(void*)info,(void*)sizes,(void*)qids,(void*)ids,(void*)max_nodes,(void*)empty,(void*)x,(void*)strings,(void*)nodes})if(p)CK(cudaFree(p));
    std::puts("pass");return 0;
}catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
