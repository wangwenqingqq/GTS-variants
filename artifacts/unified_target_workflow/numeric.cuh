#pragma once
#include "input.hpp"
namespace target {
struct Interval {double lo,hi;};
// The ordered reference matches the fixed strict_l2.cuh reference function.
__device__ __forceinline__ double reference(const float* data,int d,int a,int b) {
    double sum=0;
    for(int j=0;j<d;++j){double delta=__dsub_rn(double(data[size_t(a)*d+j]),double(data[size_t(b)*d+j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));}return sum;
}
__device__ __forceinline__ double reference_query(const float* data,int d,int a,const float* q) {
    double sum=0;
    for(int j=0;j<d;++j){double delta=__dsub_rn(double(data[size_t(a)*d+j]),double(q[j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));}return sum;
}
__device__ __forceinline__ Interval norm_query(const float* data,int d,int a,const float* q) {
    double lo=0,hi=0;
    for(int j=0;j<d;++j){double x=double(data[size_t(a)*d+j]),y=double(q[j]);
        double dl=__dsub_rd(x,y),dh=__dsub_ru(x,y);
        double amin=(dl<=0&&dh>=0)?0:fmin(fabs(dl),fabs(dh));
        double amax=fmax(fabs(dl),fabs(dh));
        lo=__dadd_rd(lo,__dmul_rd(amin,amin));hi=__dadd_ru(hi,__dmul_ru(amax,amax));}
    return {__dsqrt_rd(lo),__dsqrt_ru(hi)};
}
__device__ __forceinline__ double radius_upper(float radius,int d) {
    double alpha=1,one_minus_u=__dsub_rd(1.0,0x1p-53);
    for(int j=0;j<d+3;++j)alpha=__dmul_rd(alpha,one_minus_u);
    return __dsqrt_ru(__ddiv_ru(__dmul_rn(double(radius),double(radius)),alpha));
}
__device__ __forceinline__ bool survives(double lo,double hi,Interval q,double rupper) {
    return !(q.lo>__dadd_ru(hi,rupper)||lo>__dadd_ru(q.hi,rupper));
}
__device__ __forceinline__ bool hit(const float* data,int d,int a,const float* query,float radius,float& field) {
    double sum=reference_query(data,d,a,query);
    field=__double2float_rn(__dsqrt_rn(sum));return sum<=__dmul_rn(double(radius),double(radius));
}
struct Bounds {
    double *lo=nullptr,*hi=nullptr;const float* base=nullptr;TN* nodes=nullptr;
    int n=0,d=0,nn=0,refreshes=0;uint64_t epoch=0;size_t bytes=0,peak_bytes=0;
};
__managed__ Bounds bounds;
static std::vector<double> bounds_refresh_ms;
__global__ void refit(const float* data,const TN* nodes,const int* empty,const int* order,
                      int d,int nn,double* lower,double* upper) {
    int nid=blockIdx.x;if(nid>=nn)return;
    TN node=nodes[nid];double lo=INFINITY,hi=0;
    if(!empty[nid]&&node.size>0&&node.pid>=0){
        const float* q=data+size_t(node.pid)*d;
        for(int j=threadIdx.x;j<node.size;j+=blockDim.x){Interval v=norm_query(data,d,order[node.lid+j],q);
            lo=fmin(lo,v.lo);hi=fmax(hi,v.hi);}}
    __shared__ double low[256],high[256];low[threadIdx.x]=lo;high[threadIdx.x]=hi;__syncthreads();
    for(int stride=128;stride;stride/=2){if(threadIdx.x<stride){
        low[threadIdx.x]=fmin(low[threadIdx.x],low[threadIdx.x+stride]);
        high[threadIdx.x]=fmax(high[threadIdx.x],high[threadIdx.x+stride]);}__syncthreads();}
    if(!threadIdx.x){lower[nid]=node.pid<0?0:low[0];upper[nid]=node.pid<0?INFINITY:high[0];}
}
inline void release_bounds() {
    if(bounds.lo)u10_ck(cudaFree(bounds.lo));if(bounds.hi)u10_ck(cudaFree(bounds.hi));
    bounds.lo=bounds.hi=nullptr;bounds.base=nullptr;bounds.nodes=nullptr;bounds.bytes=0;
}
inline void refresh_bounds(const float* data,TN* nodes,const int* empty,const int* order,int nn,int n,int d) {
    auto start=U10Clock::now();u10_ck(cudaDeviceSynchronize());release_bounds();
    std::vector<TN> hn(nn);std::vector<int> he(nn),ho(n),seen(n),cover(n);
    u10_ck(cudaMemcpy(hn.data(),nodes,uk::checked_product(nn,sizeof(TN)),cudaMemcpyDeviceToHost));
    u10_ck(cudaMemcpy(he.data(),empty,uk::checked_product(nn,sizeof(int)),cudaMemcpyDeviceToHost));
    if(n)u10_ck(cudaMemcpy(ho.data(),order,uk::checked_product(n,sizeof(int)),cudaMemcpyDeviceToHost));
    for(int id:ho)uk::require(id>=0&&id<n&&++seen[id]==1,"tree physical permutation");
    uk::require(!he[0]&&hn[0].lid==0&&hn[0].size==n,"tree root coverage");
    for(int i=0;i<nn;++i)if(!he[i]&&hn[i].size>0){TN v=hn[i];
        uk::require(v.lid>=0&&v.size<=n-v.lid,"tree member interval");
        if(i)uk::require(v.pid>=0&&v.pid<n,"tree pivot physical row");
        if(v.is_leaf){uk::require(v.size<=MAX_SIZE,"tree leaf scratch capacity");
            for(int j=0;j<v.size;++j)++cover[v.lid+j];}
        else {int next=v.lid;for(int c=i*TREE_ORDER+1;c<=i*TREE_ORDER+TREE_ORDER&&c<nn;++c)
            if(!he[c]&&hn[c].size>0){uk::require(hn[c].lid==next,"tree child partition");next+=hn[c].size;}
            uk::require(next==v.lid+v.size,"tree child coverage");}}
    for(int c:cover)uk::require(c==1,"tree complete leaf coverage");
    size_t bytes=uk::checked_product(nn,sizeof(double));
    u10_ck(cudaMalloc((void**)&bounds.lo,bytes));u10_ck(cudaMalloc((void**)&bounds.hi,bytes));
    bounds.bytes=bytes*2;bounds.peak_bytes=std::max(bounds.peak_bytes,bounds.bytes);
    refit<<<nn,256>>>(data,nodes,empty,order,d,nn,bounds.lo,bounds.hi);u10_ck(cudaDeviceSynchronize());
    bounds.base=data;bounds.nodes=nodes;bounds.n=n;bounds.d=d;bounds.nn=nn;++bounds.epoch;++bounds.refreshes;
    bounds_refresh_ms.push_back(u10_ms(start));
    if(u10.tree_audit){std::vector<double> lo(nn),hi(nn);
        u10_ck(cudaMemcpy(lo.data(),bounds.lo,bytes,cudaMemcpyDeviceToHost));
        u10_ck(cudaMemcpy(hi.data(),bounds.hi,bytes,cudaMemcpyDeviceToHost));
        std::cout<<std::setprecision(17)<<"TARGET_BOUNDS {\"epoch\":"<<bounds.epoch<<",\"members\":[";
        bool first=true;for(int i=0;i<nn;++i)if(!he[i]&&hn[i].size>0&&hn[i].pid>=0){
            std::cout<<(first?"":",")<<'['<<i<<','<<lo[i]<<','<<hi[i]<<']';first=false;}
        std::cout<<"]}\n";}

}
inline void write_bounds(const std::string& path){
    std::ofstream out(path+".numeric.json");out<<std::setprecision(17)
        <<"{\"refreshes\":"<<bounds.refreshes<<",\"epoch\":"<<bounds.epoch<<",\"peak_bytes\":"<<bounds.peak_bytes
        <<",\"final_bytes\":"<<bounds.bytes<<",\"refresh_ms\":[";
    for(size_t i=0;i<bounds_refresh_ms.size();++i)out<<(i?",":"")<<bounds_refresh_ms[i];
    out<<"]}\n";uk::require(bool(out),"write common numeric receipt");
}
inline void require_epoch(const float* data,TN* nodes,int n,int d) {
    uk::require(bounds.base==data&&bounds.nodes==nodes&&bounds.n==n&&bounds.d==d&&bounds.epoch,
                "stale common numeric bounds");
}
}
