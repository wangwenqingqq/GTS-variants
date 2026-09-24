// Capacity, stable payload, poisoned-tail, rollover and pointer-churn regression.
#include <cuda_runtime.h>
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>
#include "fused_result.cuh"
void ck(cudaError_t e){if(e!=cudaSuccess){fprintf(stderr,"CUDA error: %s\n",cudaGetErrorString(e));exit(2);}}
template<class T> void alloc(T*& p,int n){ck(cudaMalloc(&p,n*sizeof(T)));}
int main(){
    std::mt19937 rng(20260924);int cases=0;
    for(int capacity:{111,1111,11111,111111})for(int fresh=0;fresh<2;++fresh){
        int slots=capacity*20,bytes=slots*4;
        int *nc,*flags,*ri,*prefix,*count,*oi;float *rd,*od;
        alloc(nc,1);alloc(flags,slots);alloc(ri,slots);alloc(rd,slots);alloc(prefix,slots);alloc(count,1);alloc(oi,slots+2);alloc(od,slots+2);
        std::vector<int> hf(slots),hi(slots),hp(slots),actual(slots+2);
        std::vector<float> hd(slots),dist(slots+2);
        for(int i=0;i<slots;++i){hi[i]=slots-1-i;hp[i]=i/7;hd[i]=float((i*31)%101)/4;}
        ck(cudaMemcpy(ri,hi.data(),bytes,cudaMemcpyHostToDevice));ck(cudaMemcpy(rd,hd.data(),bytes,cudaMemcpyHostToDevice));
        ck(cudaMemcpy(prefix,hp.data(),bytes,cudaMemcpyHostToDevice));
        for(int nodes:{capacity,1,0,capacity-1,26,25,52,51,2,capacity,0})for(int pattern=0;pattern<4;++pattern){
            std::fill(hf.begin(),hf.end(),1);std::vector<int> want;std::vector<float> wd;
            for(int i=0;i<nodes*20;++i){
                hf[i]=pattern==0?1:pattern==1?0:pattern==2?int(rng()%7==0):int(i%512==0||i%512==511);
                if(hf[i]){want.push_back(hi[i]-hp[hi[i]]);wd.push_back(hd[i]);}
            }
            ck(cudaMemcpy(nc,&nodes,4,cudaMemcpyHostToDevice));ck(cudaMemcpy(flags,hf.data(),bytes,cudaMemcpyHostToDevice));
            ck(cudaMemset(oi,0xff,(slots+2)*4));ck(cudaMemset(od,0,(slots+2)*4));
            fusedResultSelect<<<1,512>>>(nc,capacity,flags,ri,rd,prefix,count,oi,od);ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            int n;ck(cudaMemcpy(&n,count,4,cudaMemcpyDeviceToHost));assert(n==int(want.size()));
            ck(cudaMemcpy(actual.data(),oi,(slots+2)*4,cudaMemcpyDeviceToHost));ck(cudaMemcpy(dist.data(),od,(slots+2)*4,cudaMemcpyDeviceToHost));
            assert(std::equal(want.begin(),want.end(),actual.begin()));assert(std::equal(wd.begin(),wd.end(),dist.begin()));
            assert(std::all_of(actual.begin()+n,actual.end(),[](int x){return x==-1;}));++cases;
        }
        for(void* p:{(void*)nc,(void*)flags,(void*)ri,(void*)rd,(void*)prefix,(void*)count,(void*)oi,(void*)od})ck(cudaFree(p));
    }
    assert(cases==352);printf("PASS selector %d cases\n",cases);
}
