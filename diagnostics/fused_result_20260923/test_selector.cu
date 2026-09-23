// Small device regression check, including stale capacity and nonidentity maps.
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
    std::mt19937 rng(20260923);int cases=0;
    for(int fresh=0;fresh<3;++fresh){
        int *nc,*flags,*ri,*prefix,*count,*oi;float *rd,*od;
        alloc(nc,1);alloc(flags,2220);alloc(ri,2220);alloc(rd,2220);alloc(prefix,2220);alloc(count,1);alloc(oi,2222);alloc(od,2222);
        std::vector<int> hflags(2220),hri(2220),hp(2220),actual(2222);
        std::vector<float> hrd(2220),dist(2222);
        for(int i=0;i<2220;++i){hri[i]=(i*137+73)%2220;hp[i]=i/7;hrd[i]=float((i*31)%101)/4;}
        ck(cudaMemcpy(ri,hri.data(),8880,cudaMemcpyHostToDevice));ck(cudaMemcpy(rd,hrd.data(),8880,cudaMemcpyHostToDevice));
        ck(cudaMemcpy(prefix,hp.data(),8880,cudaMemcpyHostToDevice));
        for(int nodes:{111,1,0,110,26,25,52,51,2,111,0})for(int pattern=0;pattern<4;++pattern){
            // Inactive flags are deliberately hits: the kernel must not inspect them.
            std::fill(hflags.begin(),hflags.end(),1);
            std::vector<int> want;std::vector<float> wd;
            for(int i=0;i<nodes*20;++i){
                hflags[i]=pattern==0?1:pattern==1?0:pattern==2?int(rng()%7==0):int(i%512==0||i%512==511);
                if(hflags[i]){want.push_back(hri[i]-hp[hri[i]]);wd.push_back(hrd[i]);}
            }
            ck(cudaMemcpy(nc,&nodes,4,cudaMemcpyHostToDevice));ck(cudaMemcpy(flags,hflags.data(),8880,cudaMemcpyHostToDevice));
            ck(cudaMemset(oi,0xff,2222*4));ck(cudaMemset(od,0,2222*4));
            fusedResultSelect<<<1,512>>>(nc,flags,ri,rd,prefix,count,oi,od);ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            int n;ck(cudaMemcpy(&n,count,4,cudaMemcpyDeviceToHost));assert(n==int(want.size()));
            ck(cudaMemcpy(actual.data(),oi,2222*4,cudaMemcpyDeviceToHost));ck(cudaMemcpy(dist.data(),od,2222*4,cudaMemcpyDeviceToHost));
            assert(std::equal(want.begin(),want.end(),actual.begin()));assert(std::equal(wd.begin(),wd.end(),dist.begin()));
            assert(std::all_of(actual.begin()+n,actual.end(),[](int x){return x==-1;}));++cases;
        }
        for(void* p:{(void*)nc,(void*)flags,(void*)ri,(void*)rd,(void*)prefix,(void*)count,(void*)oi,(void*)od})ck(cudaFree(p));
    }
    printf("PASS selector %d cases; ordered payload, nonidentity prefix, poisoned tail and pointer churn\n",cases);
}
