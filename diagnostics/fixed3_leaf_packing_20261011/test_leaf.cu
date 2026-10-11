// Run the actual original/modified leaf kernel on explicit slot and tail cases.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <thrust/sort.h>
#include <thrust/reduce.h>
#include <thrust/scan.h>
#include <thrust/count.h>
#include "tree.cuh"
#include "search_v2.cuh"
#undef short
static void ck(cudaError_t e) { if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e)); }
template<class T> T* managed(size_t n) {T* p=nullptr;ck(cudaMallocManaged((void**)&p,n*sizeof(T)));return p;}
int main(int argc,char** argv) try {
    if(argc!=2) throw std::runtime_error("usage: test_leaf OUTPUT");
    std::ofstream out(argv[1],std::ios::binary);int cases=0;
    const int n=160,cap=10,level=1,sizes[7]={1,4,5,10,11,13,20};
    for(int d:{96,960}) for(int epoch=0;epoch<2;++epoch) {
        auto data=managed<float>(n*d);auto nodes=managed<TN>(7);
        auto ids=managed<int>(n);auto info=managed<int>(3);auto qids=managed<int>(1);
        auto disk=managed<float>(1);auto sl=managed<int>(2);auto work=managed<double>(cap*63);
        info[0]=d;info[1]=n;info[2]=2;sl[0]=0;sl[1]=cap*63;
        for(int i=0;i<n;++i) {ids[i]=i;for(int j=0;j<d;++j)data[i*d+j]=float(std::sin((i+3.)*(j+5.)*.071+epoch)*.25);}
        for(int j=0;j<d;++j)data[d+j]=data[j]; // Equal vectors, distinct identities.
        for(int tasks=1;tasks<=7;++tasks) for(int shape=0;shape<7;++shape) for(int qid:{0,1}) {
            qids[0]=qid;disk[0]=qid==0?10000.f:1.f;
            std::fill(work,work+cap*63,-987654.);
            for(int b=0;b<tasks;++b) {
                nodes[b]={0,0.f,sizes[(shape+b)%7],b*20,1};
                work[cap+b]=b;work[2*cap+b]=0;
            }
#if FP_MODE == 2
            dataProcessKnn<<<(tasks+2)/3,32>>>(nodes,disk,data,qids,info,nullptr,nullptr,work,0,ids,level,sl,1,tasks);
#elif FP_MODE == 1
            dataProcessKnn<<<tasks,32>>>(nodes,disk,data,qids,info,nullptr,nullptr,work,0,ids,level,sl,1);
#else
            dataProcessKnn<<<tasks,512>>>(nodes,disk,data,qids,info,nullptr,nullptr,work,0,ids,level,sl,1);
#endif
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            for(int b=0;b<tasks;++b) for(int slot=0;slot<20;++slot) {
                double expected=INFI_DIS;
                if(slot<nodes[b].size) {
                    int obj=ids[nodes[b].lid+slot];expected=0;
                    if(obj!=qid) {for(int j=0;j<d;++j)expected+=std::pow(data[obj*d+j]-data[qid*d+j],2);expected=std::pow(expected,.5);}
                    if(expected>disk[0])expected=INFI_DIS;
                }
                int pos=b*20+slot;double got=work[cap*23+pos];
                if(!std::isfinite(got)||std::abs(got-expected)>1e-8*std::max(1.,std::abs(expected))||
                   work[cap*3+pos]!=pos||std::abs(work[cap*43+pos]-expected/INFI_DIS)>1e-10)
                    throw std::runtime_error("leaf slot mismatch");
                double fields[3]={work[cap*3+pos],got,work[cap*43+pos]};out.write((char*)fields,sizeof(fields));
            }
            ++cases;
        }
        for(void* p:{(void*)data,(void*)nodes,(void*)ids,(void*)info,(void*)qids,(void*)disk,(void*)sl,(void*)work})ck(cudaFree(p));
    }
    if(!out)throw std::runtime_error("output write");
    std::cout<<"PASS leaf full/padding slots, tails1/2/3, D96/960, sizes1/4/5/10/11/13/20, equal vectors, self and pointer churn; cases="<<cases<<std::endl;
    return 0;
} catch(const std::exception& e) {std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
