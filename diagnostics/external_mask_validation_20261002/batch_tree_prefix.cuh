#pragma once
#include <cstddef>
#include <cstdint>
#define TREE_ORDER 10
#define MAX_SIZE 20
struct TN { int pid; float min_dis; int size; int lid; int is_leaf; };
#include "strict_l2.cuh"

// One thread owns a sibling group. Cache a pivot interval only after checking
// its actual ID; a second child with the same ID reuses the complete interval.
__global__ void parent_walk(int* flags,int stride,int start,int groups,const TN* tree,
                            const int* empty,const unsigned long long* lower,
                            const unsigned long long* upper,const float* data,
                            const int* qids,const float* radii,int batch,int d,
                            unsigned long long* pivot_count) {
    const int group=blockIdx.x*blockDim.x+threadIdx.x;
    const int q=blockIdx.y;
    if(group>=groups||q>=batch)return;
    int* qflags=flags+size_t(q)*stride;
    const int first=start+group*TREE_ORDER;
    if(qflags[(first-1)/TREE_ORDER]!=1||radii[q]<0)return;
    int cached_pid[TREE_ORDER];double cached_lo[TREE_ORDER],cached_hi[TREE_ORDER];
    int unique=0;
    const double safe_radius=double(radii[q])*(1.0+1e-10)+1e-12;
    for(int child=0;child<TREE_ORDER;++child) {
        const int nid=first+child;
        if(empty[nid]!=0)continue;
        const int pid=tree[nid].pid;
        int slot=0;for(;slot<unique;++slot)if(cached_pid[slot]==pid)break;
        if(slot==unique) {
            cached_pid[unique]=pid;
            pivot_interval<false>(data,d,qids[q],pid,cached_lo[unique],cached_hi[unique]);
            ++unique;
        }
        const double pmin=__longlong_as_double((long long)lower[nid]);
        const double pmax=__longlong_as_double((long long)upper[nid]);
        if(cached_lo[slot]<=pmax+safe_radius &&
           pmin<=cached_hi[slot]+safe_radius)qflags[nid]=1;
    }
    if(pivot_count)atomicAdd(pivot_count+q,(unsigned long long)unique);
}

__global__ void roots(int* flags,int stride,int batch) {
    int q=blockIdx.x*blockDim.x+threadIdx.x;
    if(q<batch)flags[size_t(q)*stride]=1;
}
__global__ void candidate_mask(const int* flags,int stride,const int* node_for_pos,
                               int n,int batch,int force_all,uint8_t* mask) {
    const size_t i=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i>=size_t(n)*batch)return;
    const int q=int(i/n),pos=int(i%n);
    const uint8_t raw_keep=uint8_t(flags[size_t(q)*stride+node_for_pos[pos]]==1);
    mask[i]=uint8_t(raw_keep|uint8_t(force_all));
}
