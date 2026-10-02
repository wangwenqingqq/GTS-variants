#include <cuda_runtime.h>
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include "batch_candidate_tasks.cuh"

static void check(cudaError_t result) {
    if(result!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(result));
}

int main() {
    constexpr int n=35,b=3,tiles=2,pairs=2;
    std::vector<uint8_t> input(b*n,0);
    uint8_t *source;uint32_t *m0,*m1;uint8_t *keep;
    check(cudaMalloc(&source,input.size()));
    check(cudaMalloc(&m0,pairs*tiles*sizeof(uint32_t)));
    check(cudaMalloc(&m1,pairs*tiles*sizeof(uint32_t)));
    check(cudaMalloc(&keep,pairs*tiles));
    auto run=[&](const uint32_t expected0[4],const uint32_t expected1[4],
                 const uint8_t expected_keep[4]) {
        check(cudaMemcpy(source,input.data(),input.size(),cudaMemcpyHostToDevice));
        make_tile_masks<<<dim3(1,pairs),256>>>(source,n,b,tiles,m0,m1,keep);
        check(cudaGetLastError());
        uint32_t a[4],c[4];uint8_t k[4];
        check(cudaMemcpy(a,m0,sizeof(a),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(c,m1,sizeof(c),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(k,keep,sizeof(k),cudaMemcpyDeviceToHost));
        for(int i=0;i<4;++i)
            if(a[i]!=expected0[i]||c[i]!=expected1[i]||k[i]!=expected_keep[i])
                throw std::runtime_error("mask mismatch");
    };
    const uint32_t zero[4]={0,0,0,0};
    const uint8_t none[4]={0,0,0,0};
    run(zero,zero,none); // every task empty
    for(int lane=0;lane<32;++lane)input[lane]=input[n+lane]=1;
    input[32]=1;input[n+33]=1;input[2*n+34]=1;
    const uint32_t full0[4]={0xffffffffu,1,0,4};
    const uint32_t full1[4]={0xffffffffu,2,0,0};
    const uint8_t present[4]={1,1,0,1};
    run(full0,full1,present); // same/full, disjoint tail, singleton, missing q3
    std::fill(input.begin(),input.end(),0);
    for(int lane=0;lane<16;++lane)input[lane]=1;
    for(int lane=16;lane<32;++lane)input[n+lane]=1;
    const uint32_t apart0[4]={0x0000ffffu,0,0,0};
    const uint32_t apart1[4]={0xffff0000u,0,0,0};
    const uint8_t only_first[4]={1,0,0,0};
    run(apart0,apart1,only_first); // disjoint masks keep the union
    check(cudaFree(keep));check(cudaFree(m1));check(cudaFree(m0));check(cudaFree(source));
}
