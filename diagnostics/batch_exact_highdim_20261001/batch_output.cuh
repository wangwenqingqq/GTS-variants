#pragma once
#include <cub/cub.cuh>
#include <cstddef>
#include <cstdint>

constexpr int kObjectBlock = 512;

template<class Hit>
__global__ void batchBlockCount(const Hit* flags, int n, int blocks,
                                int64_t* block_counts) {
    using Reduce = cub::BlockReduce<int,kObjectBlock>;
    __shared__ typename Reduce::TempStorage temp;
    const int q=blockIdx.y, b=blockIdx.x;
    const int pos=b*kObjectBlock+threadIdx.x;
    const int hit=pos<n?int(flags[size_t(q)*n+pos]):0;
    const int count=Reduce(temp).Sum(hit);
    if(threadIdx.x==0)block_counts[size_t(q)*blocks+b]=count;
}

__global__ void batchOffsets(const int64_t* block_counts,
                             const int64_t* block_prefix, int batch,
                             int blocks, int64_t* offsets) {
    const int q=blockIdx.x*blockDim.x+threadIdx.x;
    if(q<batch)offsets[q]=block_prefix[size_t(q)*blocks];
    if(q==batch){
        const size_t last=size_t(batch)*blocks-1;
        offsets[q]=block_prefix[last]+block_counts[last];
    }
}

template<class Hit>
__global__ void batchScatter(const Hit* flags, const float* raw_distance,
                             const int* id_list, const int64_t* block_prefix,
                             int n, int blocks, int* out_ids, float* out_distance) {
    using Scan = cub::BlockScan<int,kObjectBlock>;
    __shared__ typename Scan::TempStorage temp;
    const int q=blockIdx.y,b=blockIdx.x;
    const int pos=b*kObjectBlock+threadIdx.x;
    const int hit=pos<n?int(flags[size_t(q)*n+pos]):0;
    int local;
    Scan(temp).ExclusiveSum(hit,local);
    if(hit){
        const size_t source=size_t(q)*n+pos;
        const size_t target=size_t(block_prefix[size_t(q)*blocks+b]+local);
        out_ids[target]=id_list[pos];
        out_distance[target]=raw_distance[source];
    }
}
