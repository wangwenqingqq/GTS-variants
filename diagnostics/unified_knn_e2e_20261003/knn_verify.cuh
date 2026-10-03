#pragma once
#include <cstdint>
__global__ void pack32(const float* data,const int* order,float* packed,int n,int d) {
    int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    for(int j=0;j<d;++j)packed[size_t(pos/32)*d*32+j*32+(pos&31)]=data[size_t(order[pos])*d+j];
}
__global__ void seed_distances(const float* data,const int* seeds,const int* qids,
    double* scores,int m,int d,int b) {
    int pos=blockIdx.x*blockDim.x+threadIdx.x,q=blockIdx.y;
    if(pos<m&&q<b)scores[size_t(q)*m+pos]=rn_squared(data,seeds[pos],qids[q],d);
}
template<int QT,bool Early,bool Mask>
__global__ void verify_distances(const float* data,const float* packed,const int* qids,
    const double* cutoff,const uint8_t* mask,double* scores,int n,int d,int b) {
    extern __shared__ float query[];
    int first=blockIdx.y*QT;
    for(int j=threadIdx.x;j<QT*d;j+=blockDim.x)
        query[j]=first+j/d<b?data[size_t(qids[first+j/d])*d+j%d]:0.f;
    __syncthreads();
    int pos=blockIdx.x*blockDim.x+threadIdx.x;if(pos>=n)return;
    double sums[QT]={0};bool active[QT];
#pragma unroll
    for(int t=0;t<QT;++t)active[t]=first+t<b&&(!Mask||mask[size_t(first+t)*n+pos]);
    size_t tile=size_t(pos/32)*d*32;
    for(int j=0;j<d;++j) {
        bool any=false;
#pragma unroll
        for(int t=0;t<QT;++t)any|=active[t];
        if(!any)break;
        float x=packed[tile+j*32+(pos&31)];
#pragma unroll
        for(int t=0;t<QT;++t)if(active[t]) {
            double dx=__dsub_rn(double(x),double(query[t*d+j]));
            sums[t]=__dadd_rn(sums[t],__dmul_rn(dx,dx));
            if constexpr(Early)if((j&31)==31&&sums[t]>cutoff[first+t])active[t]=false;
        }
    }
#pragma unroll
    for(int t=0;t<QT;++t)if(first+t<b)
        scores[size_t(first+t)*n+pos]=active[t]?sums[t]:INFINITY;
}
