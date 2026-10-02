#pragma once
#include <cstddef>
#include <cstdint>

// One thread owns one logical id_list position. A query microtile shares the
// loaded object coordinate, while each pair retains its own ordered FP64 sum.
template<int QueryTile, bool Early>
__global__ void batchDistance(const int* id_list, const float* data,
                              const float* packed, const int* qids,
                              const float* radii, int n, int d, int batch,
                              int query_base, uint8_t* flags, float* raw_distance) {
    extern __shared__ float query_cache[];
    const int first_query = query_base + int(blockIdx.y) * QueryTile;
    for (int k = threadIdx.x; k < QueryTile*d; k += blockDim.x) {
        const int slot = k/d;
        const int q = first_query + slot;
        query_cache[k] = q < batch ? data[size_t(qids[q])*d + (k%d)] : 0.0f;
    }
    __syncthreads();
    const int pos = int(blockIdx.x)*blockDim.x + threadIdx.x;
    if (pos >= n) return; // No barrier follows this point.
    const size_t tile = size_t(pos/32)*size_t(d)*32;
    const int lane = pos & 31;
    double sums[QueryTile];
    double cutoffs[QueryTile];
    bool active[QueryTile];
#pragma unroll
    for (int t=0;t<QueryTile;++t) {
        const int q=first_query+t;
        const float radius=q<batch?radii[q]:-1.0f;
        active[t]=q<batch && radius>=0.0f;
        cutoffs[t]=__dmul_rn(double(radius),double(radius));
        sums[t]=0.0;
    }
    for (int j=0;j<d;++j) {
        if constexpr(Early) {
            bool any=false;
#pragma unroll
            for(int t=0;t<QueryTile;++t) any |= active[t];
            if(!any)break;
        }
        const float x=packed[tile+size_t(j)*32+lane];
#pragma unroll
        for (int t=0;t<QueryTile;++t) {
            if (!active[t]) continue;
            const float q=query_cache[t*d+j];
            const double delta=__dsub_rn(double(x),double(q));
            sums[t]=__dadd_rn(sums[t],__dmul_rn(delta,delta));
            if constexpr(Early) {
                if ((j&31)==31 && sums[t]>cutoffs[t]) active[t]=false;
            }
        }
    }
#pragma unroll
    for (int t=0;t<QueryTile;++t) {
        const int q=first_query+t;
        if(q>=batch)continue;
        const bool hit=active[t] && sums[t]<=cutoffs[t];
        const size_t out=size_t(q)*n+pos;
        flags[out]=uint8_t(hit);
        if(hit)raw_distance[out]=float(sqrt(sums[t]));
    }
}
