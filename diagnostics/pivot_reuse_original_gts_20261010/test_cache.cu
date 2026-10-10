// Isolated cache/rounding/lifetime gate; not a full-search exactness certificate.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <cuda_runtime.h>
#include "tree.cuh"
#define PR_ENABLED 1
#define PR_COUNTS 1
#include "reuse.cuh"
__global__ void pivot_value(const float* x,int d,int id,int q,double* v) {
    double dis_q=0;
    for(int j=0;j<d;++j) dis_q+=pow(x[id*d+j]-x[q*d+j],2);
    dis_q=pow(dis_q,0.5);*v=dis_q;
}
__global__ void leaf_value(const float* x,int d,int id,int q,double* v) {
    double result=0;
    if(id!=q) {
        for(int j=0;j<d;++j) result+=pow(x[id*d+j]-x[q*d+j],2);
        result=pow(result,0.5);
    }
    *v=result;
}
int main() {
    for(int d:{96,960}) {
        std::vector<float> host(4*d);
        for(int id=0;id<4;++id) for(int j=0;j<d;++j)
            host[id*d+j]=float(((j*17+(id==2?1:id)*137)%1031)-515)/1024;
        float* x;double *a,*b;
        CHECK(cudaMalloc(&x,host.size()*sizeof(float)));CHECK(cudaMallocManaged(&a,sizeof(double)));
        CHECK(cudaMallocManaged(&b,sizeof(double)));CHECK(cudaMemcpy(x,host.data(),host.size()*sizeof(float),cudaMemcpyHostToDevice));
        pr_capacity=4;
        for(int iteration=0;iteration<64;++iteration) {
            int q=iteration%4;pr_begin();
            std::vector<int> tags(4);CHECK(cudaMemcpy(tags.data(),pr_valid,16,cudaMemcpyDeviceToHost));
            for(int value:tags) if(value) throw std::runtime_error("stale query validity");
            for(int id=0;id<4;++id) {
                pivot_value<<<1,1>>>(x,d,id,q,a);leaf_value<<<1,1>>>(x,d,id,q,b);
                CHECK(cudaDeviceSynchronize());
                uint64_t av,bv;std::memcpy(&av,a,8);std::memcpy(&bv,b,8);
                if(av!=bv)
                    throw std::runtime_error("pivot/leaf rounding bridge");
                CHECK(cudaMemcpy(pr_distance+id,a,sizeof(double),cudaMemcpyDeviceToDevice));
                int valid=1;CHECK(cudaMemcpy(pr_valid+id,&valid,4,cudaMemcpyHostToDevice));
                double returned;CHECK(cudaMemcpy(&returned,pr_distance+id,8,cudaMemcpyDeviceToHost));
                if(returned!=*b) throw std::runtime_error("cache payload");
            }
            pr_end(); // Fresh allocations every query: miss/hit/reset/pointer reuse.
        }
        CHECK(cudaFree(x));CHECK(cudaFree(a));CHECK(cudaFree(b));
    }
    printf("PASS 512 pivot/leaf bitwise bridges, 128 cold-query resets, duplicate-vector distinct IDs, self and four-object cache (fewer than K8)\n");
}
