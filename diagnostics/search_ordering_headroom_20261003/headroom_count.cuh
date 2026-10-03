#pragma once
// Diagnostics only: this kernel is never captured in the timed query graph.
struct WorkCount {
    unsigned long long candidate[2], updates[2], unions, shared_steps;
};
__global__ void materialize_cutoff(const double* seed_u,const double* oracle_u,
    const int* qids,double* u,int b,bool star) {
    int q=threadIdx.x;
    if(q<b)u[q]=star?oracle_u[qids[q]]:seed_u[q];
}
__device__ unsigned long long warp_sum(unsigned long long v) {
    for(int delta=16;delta;delta/=2)v+=__shfl_down_sync(0xffffffff,v,delta);
    return v;
}
template<int QT,bool Mask>
__global__ void count_verify(const float* data,const float* packed,const int* qids,
    const double* cutoff,const uint8_t* mask,int n,int d,int b,WorkCount* counts) {
    extern __shared__ float query[];
    int first=blockIdx.y*QT;
    for(int j=threadIdx.x;j<QT*d;j+=blockDim.x)
        query[j]=first+j/d<b?data[size_t(qids[first+j/d])*d+j%d]:0.f;
    __syncthreads();
    int pos=blockIdx.x*blockDim.x+threadIdx.x;
    double sums[QT]={0};bool active[QT];
    unsigned long long c[2]={0},updates[2]={0},unions=0,shared=0;
    for(int t=0;t<QT;++t) {
        active[t]=pos<n&&first+t<b&&(!Mask||mask[size_t(first+t)*n+pos]);
        c[t]=active[t];unions|=c[t];
    }
    size_t tile=size_t(pos/32)*d*32;
    for(int j=0;j<d;++j) {
        bool any=false;for(int t=0;t<QT;++t)any|=active[t];
        if(!any)break;
        ++shared;float x=packed[tile+j*32+(pos&31)];
        for(int t=0;t<QT;++t)if(active[t]) {
            ++updates[t];double dx=__dsub_rn(double(x),double(query[t*d+j]));
            sums[t]=__dadd_rn(sums[t],__dmul_rn(dx,dx));
            if((j&31)==31&&sums[t]>cutoff[first+t])active[t]=false;
        }
    }
    // All lanes, including the ragged object tail, participate in reduction.
    for(int t=0;t<2;++t) {
        c[t]=warp_sum(c[t]);updates[t]=warp_sum(updates[t]);
        if((threadIdx.x&31)==0) {
            atomicAdd(&counts[blockIdx.y].candidate[t],c[t]);
            atomicAdd(&counts[blockIdx.y].updates[t],updates[t]);
        }
    }
    unions=warp_sum(unions);shared=warp_sum(shared);
    if((threadIdx.x&31)==0) {
        atomicAdd(&counts[blockIdx.y].unions,unions);
        atomicAdd(&counts[blockIdx.y].shared_steps,shared);
    }
}
