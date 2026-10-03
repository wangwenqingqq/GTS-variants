#pragma once
struct Neighbor { double squared; int id; };
__device__ inline bool before(const Neighbor& a,const Neighbor& b) {
    return a.squared<b.squared || (a.squared==b.squared && a.id<b.id);
}
// Each disjoint block keeps its K smallest pairs. Repeatedly reduce the union;
// any item omitted locally has at least K predecessors and cannot be global K.
__global__ void block_topk(const double* scores,const int* order,
    const Neighbor* input,Neighbor* output,int count,int k,int b,bool first) {
    __shared__ Neighbor values[256];
    int t=threadIdx.x,q=blockIdx.y,pos=blockIdx.x*256+t;
    Neighbor value={INFINITY,0x7fffffff};
    if(pos<count) value=first?Neighbor{scores[size_t(q)*count+pos],order[pos]}:
                              input[size_t(q)*count+pos];
    values[t]=value;__syncthreads();
    for(int width=2;width<=256;width<<=1)for(int step=width>>1;step;step>>=1) {
        int partner=t^step;
        if(partner>t) {
            Neighbor a=values[t],c=values[partner];bool asc=(t&width)==0;
            if(asc?before(c,a):before(a,c)){values[t]=c;values[partner]=a;}
        }
        __syncthreads();
    }
    if(t<k) output[(size_t(q)*gridDim.x+blockIdx.x)*k+t]=values[t];
}
__global__ void select_cutoff(const Neighbor* seed_result,double* cutoff,int k,int b) {
    int q=blockIdx.x*blockDim.x+threadIdx.x;
    if(q<b)cutoff[q]=seed_result[size_t(q)*k+k-1].squared;
}
__global__ void final_output(const Neighbor* input,int* ids,float* dist,int b,int k) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<b*k){ids[i]=input[i].id;dist[i]=__double2float_rn(__dsqrt_rn(input[i].squared));}
}
