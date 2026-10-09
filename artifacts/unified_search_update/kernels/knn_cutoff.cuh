#pragma once
#include <cuda_runtime.h>
#include <cstdint>
#include <cmath>
struct TN { int pid; float min_dis; int size; int lid; int is_leaf; };

// See knn_reference_contract.md. All float32 differences/squares are normal
// finite double values (or zero); gamma bounds the ordered RN accumulation.
__device__ inline double gamma_l2(int d) {
    const double mu = double(d+3)*0x1p-53;
    return __ddiv_ru(mu, __dsub_rd(1.0,mu));
}
__device__ inline void norm_enclosure(double s,int d,double& lo,double& hi) {
    const double g=gamma_l2(d);
    lo=__dsqrt_rd(__ddiv_rd(s,__dadd_ru(1.,g)));
    hi=__dsqrt_ru(__ddiv_ru(s,__dsub_rd(1.,g)));
}
__device__ inline double rn_squared(const float* data,int a,int b,int d) {
    double s=0;
    for(int j=0;j<d;++j) {
        double x=__dsub_rn(double(data[size_t(a)*d+j]),double(data[size_t(b)*d+j]));
        s=__dadd_rn(s,__dmul_rn(x,x));
    }
    return s;
}
__global__ void refit_node_bounds(const float* data,const int* order,
    const int* mapping,const TN* tree,int n,int d,
    unsigned long long* lower,unsigned long long* upper) {
    int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    int nid=mapping[pos];if(nid<0)return; double lo,hi;
    norm_enclosure(rn_squared(data,order[pos],tree[nid].pid,d),d,lo,hi);
    atomicMin(lower+nid,(unsigned long long)__double_as_longlong(lo));
    atomicMax(upper+nid,(unsigned long long)__double_as_longlong(hi));
}
__global__ void init_root(int* flags,int stride,int b) {
    int q=blockIdx.x*blockDim.x+threadIdx.x;
    if(q<b)flags[size_t(q)*stride]=1;
}
__global__ void knn_parent_walk(int* flags,int stride,int start,int groups,
    const TN* tree,const int* empty,const unsigned long long* lower,
    const unsigned long long* upper,const float* data,const int* qids,
    const double* cutoff,int b,int d) {
    int group=blockIdx.x*blockDim.x+threadIdx.x,q=blockIdx.y;
    if(group>=groups||q>=b)return;
    int first=start+group*10; int* qflags=flags+size_t(q)*stride;
    if(!qflags[(first-1)/10])return;
    double ignored,radius;norm_enclosure(cutoff[q],d,ignored,radius);
    int cached_ids[10],used=0;double cached_lo[10],cached_hi[10];
    for(int c=0;c<10;++c) {
        int nid=first+c;if(empty[nid])continue;
        int pid=tree[nid].pid,slot=0;
        for(;slot<used;++slot)if(cached_ids[slot]==pid)break;
        if(slot==used) {
            cached_ids[used]=pid;
            norm_enclosure(rn_squared(data,pid,qids[q],d),d,cached_lo[used],cached_hi[used]);
            ++used;
        }
        double lo=__longlong_as_double((long long)lower[nid]);
        double hi=__longlong_as_double((long long)upper[nid]);
        // Nonfinite or unproved intervals retain the node. Equality retains.
        bool proved=isfinite(lo)&&isfinite(hi)&&lo<=hi&&isfinite(radius);
        if(!proved || (cached_lo[slot]<=__dadd_ru(hi,radius) &&
                       lo<=__dadd_ru(cached_hi[slot],radius)))qflags[nid]=1;
    }
}
__global__ void knn_mask(const int* flags,int stride,const int* mapping,
    uint8_t* mask,int n,int b) {
    size_t i=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<size_t(n)*b)mask[i]=uint8_t(flags[(i/n)*stride+mapping[i%n]]);
}
