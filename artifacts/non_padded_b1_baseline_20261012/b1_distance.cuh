// Baseline diagnostic only: direct FP32 squared differences, one warp per row.
#pragma once
#include <cuda_runtime.h>
#include <cuvs/distance/pairwise_distance.h>
#include <cmath>
#include <stdexcept>

__global__ void squared_l2_b1(const float* x,const float* q,float* out,int n,int d){
    int row=int(blockIdx.x)*8+int(threadIdx.x)/32,lane=int(threadIdx.x)%32;
    if(row>=n)return; // Uniform within a warp; every participating lane reaches all shuffles.
    float sum=0;
    for(int j=lane;j<d;j+=32){float delta=x[size_t(row)*d+j]-q[j];sum=fmaf(delta,delta,sum);}
    for(int offset=16;offset;offset/=2)sum+=__shfl_down_sync(0xffffffff,sum,offset);
    if(!lane)out[row]=sum;
}

static cuvsError_t b1PairwiseDistance(cuvsResources_t resource,DLManagedTensor* q,
                                     DLManagedTensor* x,DLManagedTensor* out,
                                     cuvsDistanceType metric,float argument){
    auto valid=[](DLManagedTensor* t){return t&&t->dl_tensor.ndim==2&&t->dl_tensor.shape&&
        t->dl_tensor.data&&t->dl_tensor.device.device_type==kDLCUDA&&
        t->dl_tensor.dtype.code==kDLFloat&&t->dl_tensor.dtype.bits==32&&
        t->dl_tensor.dtype.lanes==1&&t->dl_tensor.strides==nullptr&&t->dl_tensor.byte_offset==0;};
    if(!valid(q)||!valid(x)||!valid(out)||metric!=L2Unexpanded||argument!=0||
       q->dl_tensor.shape[0]!=1||q->dl_tensor.shape[1]!=960||x->dl_tensor.shape[1]!=960||
       x->dl_tensor.shape[0]<1||x->dl_tensor.shape[0]>1000000||out->dl_tensor.shape[0]!=1||
       out->dl_tensor.shape[1]!=x->dl_tensor.shape[0])throw std::runtime_error("B1 diagnostic contract");
    cudaStream_t stream{};auto status=cuvsStreamGet(resource,&stream);if(status!=CUVS_SUCCESS)return status;
    int n=int(x->dl_tensor.shape[0]);
    squared_l2_b1<<<(n+7)/8,256,0,stream>>>(static_cast<const float*>(x->dl_tensor.data),
        static_cast<const float*>(q->dl_tensor.data),static_cast<float*>(out->dl_tensor.data),n,960);
    auto error=cudaGetLastError();if(error!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(error));
    return CUVS_SUCCESS;
}
