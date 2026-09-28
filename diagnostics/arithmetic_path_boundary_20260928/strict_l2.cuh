#pragma once
#include <cfloat>
#include <cmath>
#include <cstdint>

// For D<=960, 4*gamma_(D+2) exceeds the normal-range FP32 subtraction,
// multiplication and sequential positive-sum relative error, plus FP64 sum
// rounding. Abnormal intermediate values use the reference path.
__device__ __forceinline__ double fast_eta(int d) {
    const double u=0x1p-24;
    const double x=(double(d)+2.0)*u;
    return 4.0*x/(1.0-x);
}

__device__ __forceinline__ double down_positive(double v) {
    return v<=0 ? 0 : __longlong_as_double(__double_as_longlong(v)-1);
}
__device__ __forceinline__ double up_positive(double v) {
    return __longlong_as_double(__double_as_longlong(v)+1);
}

__device__ __forceinline__ double strict_ref_sum(const float* data,int d,int a,int b) {
    double acc=0;
    for(int j=0;j<d;++j) {
        const double delta=__dsub_rn(double(data[size_t(a)*d+j]),double(data[size_t(b)*d+j]));
        const double square=__dmul_rn(delta,delta);
        acc=__dadd_rn(acc,square);
    }
    return acc;
}

__device__ __forceinline__ float strict_fast_sum(const float* data,int d,int a,int b,bool& abnormal) {
    float acc=0;
    abnormal=false;
    for(int j=0;j<d;++j) {
        const float va=data[size_t(a)*d+j],vb=data[size_t(b)*d+j];
        const float delta=__fsub_rn(va,vb);
        const float square=__fmul_rn(delta,delta);
        acc=__fadd_rn(acc,square);
        if(!isfinite(delta)||!isfinite(square)||!isfinite(acc)||
           (delta==0 && va!=vb)||
           (delta!=0 && fabsf(delta)<FLT_MIN)||
           (square==0 && delta!=0)||
           (square!=0 && square<FLT_MIN)||
           (acc!=0 && acc<FLT_MIN)) abnormal=true;
    }
    return acc;
}

// An outward interval for true Euclidean distance from the specified FP64 sum.
// gamma_960(double)<1.1e-13; 1e-10 also covers sqrt and interval operations.
__device__ __forceinline__ void ref_norm_interval(double sum,double& lo,double& hi) {
    const double norm=sqrt(sum);
    lo=down_positive(fmax(0.0,norm*(1.0-1e-10)-1e-12));
    hi=up_positive(norm*(1.0+1e-10)+1e-12);
}

template<bool Fast>
__device__ __forceinline__ void pivot_interval(const float* data,int d,int a,int b,double& lo,double& hi) {
    if constexpr(Fast) {
        bool abnormal=false;
        const float sum=strict_fast_sum(data,d,a,b,abnormal);
        if(!abnormal) {
            const double eta=fast_eta(d);
            lo=down_positive(fmax(0.0,sqrt(double(sum)/(1.0+eta))*(1.0-1e-10)-1e-12));
            hi=up_positive(sqrt(double(sum)/(1.0-eta))*(1.0+1e-10)+1e-12);
            return;
        }
    }
    ref_norm_interval(strict_ref_sum(data,d,a,b),lo,hi);
}

template<bool Fast>
__device__ __forceinline__ bool strict_hit(const float* data,int d,int a,int b,float radius,float& distance) {
    if(radius<0)return false;
    const double cutoff=double(radius)*double(radius);
    if constexpr(Fast) {
        bool abnormal=false;
        const float sum=strict_fast_sum(data,d,a,b,abnormal);
        if(!abnormal && double(sum)>cutoff*(1.0+fast_eta(d)))return false;
    }
    const double sum=strict_ref_sum(data,d,a,b);
    if(sum>cutoff)return false;
    distance=float(sqrt(sum));
    return true;
}

__global__ void refit_bounds(const int* pos_node,const int* ids,const TN* tree,
                             const float* data,int n,int d,
                             unsigned long long* lower,unsigned long long* upper) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    const int nid=pos_node[pos];
    const double sum=strict_ref_sum(data,d,ids[pos],tree[nid].pid);
    double lo,hi;ref_norm_interval(sum,lo,hi);
    atomicMin(lower+nid,(unsigned long long)__double_as_longlong(lo));
    atomicMax(upper+nid,(unsigned long long)__double_as_longlong(hi));
}

template<bool Fast>
__global__ void strict_walk(int* flags,int start,const TN* tree,float radius,
                            const float* data,const int* qid,int width,int d,
                            const int* empty,const unsigned long long* lower,
                            const unsigned long long* upper) {
    const int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=width)return;
    const int nid=start+i;
    if(radius<0||flags[(nid-1)/TREE_ORDER]!=1||empty[nid]!=0)return;
    double qlo,qhi;
    pivot_interval<Fast>(data,d,qid[0],tree[nid].pid,qlo,qhi);
    const double pmin=__longlong_as_double((long long)lower[nid]);
    const double pmax=__longlong_as_double((long long)upper[nid]);
    const double safe_radius=double(radius)*(1.0+1e-10)+1e-12;
    if(qlo>pmax+safe_radius || pmin>qhi+safe_radius)return;
    flags[nid]=1;
}

__global__ void clear_parents(int* flags,int start,int width) {
    const int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=width/TREE_ORDER)return;
    flags[(start+i*TREE_ORDER-1)/TREE_ORDER]=0;
}

template<bool Fast>
__global__ void strict_flat(const int* ids,const float* data,const int* qid,int n,int d,
                            float radius,int* hits,int* rawids,float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    float dist=0;
    const int id=ids[pos];
    const bool hit=strict_hit<Fast>(data,d,id,qid[0],radius,dist);
    hits[pos]=int(hit);
    if(hit){rawids[pos]=id;rawdis[pos]=dist;}
}

template<bool Fast>
__global__ void strict_compact(const int* ids,const float* data,const int* qid,int n,int d,
                               float radius,const int* positions,const int* candidate_count,
                               int* hits,int* rawids,float* rawdis) {
    const int rank=blockIdx.x*blockDim.x+threadIdx.x;
    if(rank>=*candidate_count)return;
    const int id=ids[positions[rank]];
    float dist=0;
    const bool hit=strict_hit<Fast>(data,d,id,qid[0],radius,dist);
    hits[rank]=int(hit);
    if(hit){rawids[rank]=id;rawdis[rank]=dist;}
}

template<bool Fast>
__global__ void strict_leaf(const int* candidates,const TN* tree,const int* ids,
                            const float* data,const int* qid,int d,float radius,
                            int* hits,int* rawids,float* rawdis,const int* candidate_count) {
    const int rank=blockIdx.x;
    if(rank>=*candidate_count)return;
    const TN node=tree[candidates[rank]];
    if(node.is_leaf!=1)return;
    for(int i=threadIdx.x;i<node.size;i+=blockDim.x) {
        const int id=ids[node.lid+i];
        float dist=0;
        const bool hit=strict_hit<Fast>(data,d,id,qid[0],radius,dist);
        hits[rank*MAX_SIZE+i]=int(hit);
        if(hit){rawids[rank*MAX_SIZE+i]=id;rawdis[rank*MAX_SIZE+i]=dist;}
    }
}
