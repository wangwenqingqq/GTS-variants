#pragma once
#include <cstdint>

// Dense positions remain the output address in every mode. A tree-rejected
// position is initialized to zero before any distance kernel is launched.
template<int QueryTile,bool Early>
__global__ void masked_distance(const int* order,const float* data,const float* packed,
                                const int* qids,const float* radii,const uint8_t* mask,
                                int n,int d,int batch,uint8_t* flags,float* raw_distance) {
    extern __shared__ float query_cache[];
    const int first_query=int(blockIdx.y)*QueryTile;
    for(int k=threadIdx.x;k<QueryTile*d;k+=blockDim.x) {
        const int q=first_query+k/d;
        query_cache[k]=q<batch?data[size_t(qids[q])*d+(k%d)]:0.0f;
    }
    __syncthreads();
    const int pos=int(blockIdx.x)*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    const size_t tile=size_t(pos/32)*size_t(d)*32;
    const int lane=pos&31;
    double sums[QueryTile],cutoffs[QueryTile];bool active[QueryTile];
#pragma unroll
    for(int t=0;t<QueryTile;++t) {
        const int q=first_query+t;
        const float radius=q<batch?radii[q]:-1.0f;
        active[t]=q<batch&&radius>=0&&mask[size_t(q)*n+pos];
        cutoffs[t]=__dmul_rn(double(radius),double(radius));
        sums[t]=0;
    }
    for(int j=0;j<d;++j) {
        bool any=false;
#pragma unroll
        for(int t=0;t<QueryTile;++t)any|=active[t];
        if(!any)break;
        const float x=packed[tile+size_t(j)*32+lane];
#pragma unroll
        for(int t=0;t<QueryTile;++t)if(active[t]) {
            const double delta=__dsub_rn(double(x),double(query_cache[t*d+j]));
            sums[t]=__dadd_rn(sums[t],__dmul_rn(delta,delta));
            if constexpr(Early)if((j&31)==31&&sums[t]>cutoffs[t])active[t]=false;
        }
    }
#pragma unroll
    for(int t=0;t<QueryTile;++t) {
        const int q=first_query+t;
        if(q>=batch)continue;
        if(active[t]&&sums[t]<=cutoffs[t]) {
            const size_t out=size_t(q)*n+pos;
            flags[out]=1;raw_distance[out]=float(sqrt(sums[t]));
        }
    }
}

template<bool Early>
__global__ void id_distance(const int* data_order,const float* data,const float* packed,
                            const int* qids,const float* radii,const int* positions,
                            const int* counts,int n,int d,int batch,
                            uint8_t* flags,float* raw_distance) {
    extern __shared__ float query_cache[];
    const int q=blockIdx.y;
    for(int j=threadIdx.x;j<d;j+=blockDim.x)
        query_cache[j]=data[size_t(qids[q])*d+j];
    __syncthreads();
    const int rank=int(blockIdx.x)*blockDim.x+threadIdx.x;
    if(rank>=counts[q])return;
    const int pos=positions[size_t(q)*n+rank];
    const double cutoff=__dmul_rn(double(radii[q]),double(radii[q]));
    const size_t tile=size_t(pos/32)*size_t(d)*32;
    const int lane=pos&31;
    double sum=0;
    for(int j=0;j<d;++j) {
        const double delta=__dsub_rn(double(packed[tile+size_t(j)*32+lane]),
                                     double(query_cache[j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));
        if constexpr(Early)if((j&31)==31&&sum>cutoff)break;
    }
    if(radii[q]>=0&&sum<=cutoff) {
        const size_t out=size_t(q)*n+pos;
        flags[out]=1;raw_distance[out]=float(sqrt(sum));
    }
}

__global__ void make_tile_masks(const uint8_t* candidates,int n,int batch,int tiles,
                                uint32_t* mask0,uint32_t* mask1,uint8_t* keep) {
    const int tile=blockIdx.x*blockDim.x+threadIdx.x;
    const int pair=blockIdx.y;
    if(tile>=tiles)return;
    const int first=pair*2;
    uint32_t a=0,b=0;
    for(int lane=0;lane<32;++lane) {
        const int pos=tile*32+lane;
        if(pos>=n)break;
        if(candidates[size_t(first)*n+pos])a|=uint32_t(1)<<lane;
        if(first+1<batch&&candidates[size_t(first+1)*n+pos])b|=uint32_t(1)<<lane;
    }
    const size_t at=size_t(pair)*tiles+tile;
    mask0[at]=a;mask1[at]=b;keep[at]=uint8_t((a|b)!=0);
}

template<bool Early>
__global__ void task_distance(const float* data,const float* packed,const int* qids,
                              const float* radii,const int* task_tiles,const int* task_counts,
                              const uint32_t* mask0,const uint32_t* mask1,
                              int n,int d,int batch,int tiles,
                              uint8_t* flags,float* raw_distance) {
    extern __shared__ float query_cache[];
    const int pair=blockIdx.y,first=pair*2;
    for(int k=threadIdx.x;k<2*d;k+=blockDim.x) {
        const int q=first+k/d;
        query_cache[k]=q<batch?data[size_t(qids[q])*d+(k%d)]:0.0f;
    }
    __syncthreads();
    const int task=int(blockIdx.x)*16+threadIdx.x/32;
    if(task>=task_counts[pair])return;
    const int tile=task_tiles[size_t(pair)*tiles+task];
    const int lane=threadIdx.x&31,pos=tile*32+lane;
    if(pos>=n)return;
    const size_t at=size_t(pair)*tiles+tile;
    bool active[2]={bool(mask0[at]&(uint32_t(1)<<lane)),
                    first+1<batch&&bool(mask1[at]&(uint32_t(1)<<lane))};
    double sums[2]={0,0};
    const double cutoffs[2]={__dmul_rn(double(radii[first]),double(radii[first])),
                              first+1<batch?__dmul_rn(double(radii[first+1]),double(radii[first+1])):0};
    if(radii[first]<0)active[0]=false;
    if(first+1<batch&&radii[first+1]<0)active[1]=false;
    const size_t packed_tile=size_t(tile)*size_t(d)*32;
    for(int j=0;j<d;++j) {
        if(!active[0]&&!active[1])break;
        const float x=packed[packed_tile+size_t(j)*32+lane];
#pragma unroll
        for(int t=0;t<2;++t)if(active[t]) {
            const double delta=__dsub_rn(double(x),double(query_cache[t*d+j]));
            sums[t]=__dadd_rn(sums[t],__dmul_rn(delta,delta));
            if constexpr(Early)if((j&31)==31&&sums[t]>cutoffs[t])active[t]=false;
        }
    }
#pragma unroll
    for(int t=0;t<2;++t)if(first+t<batch&&active[t]&&sums[t]<=cutoffs[t]) {
        const size_t out=size_t(first+t)*n+pos;
        flags[out]=1;raw_distance[out]=float(sqrt(sums[t]));
    }
}
