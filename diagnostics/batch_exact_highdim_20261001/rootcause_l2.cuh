#pragma once
#include <cstddef>

// Logical position is always the original id_list position. Only the point
// storage address differs between the four modes.
__global__ void rootcausePack32(const int* id_list,const float* data,
                                float* packed,int n,int d) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    const size_t tile=size_t(pos/32)*size_t(d)*32;
    const int lane=pos&31;
    const size_t source=size_t(id_list[pos])*d;
    for(int j=0;j<d;++j)
        packed[tile+size_t(j)*32+lane]=data[source+j];
}

template<bool Layout,bool Early,bool Count=false>
__global__ void rootcauseFlat(const int* id_list,const float* data,
                              const float* packed,const int* qid,int n,int d,
                              float radius,int* hits,int* rawids,float* rawdis,
                              int* processed) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    if(radius<0) {
        hits[pos]=0;
        if constexpr(Count)processed[pos]=0;
        return;
    }
    const int id=id_list[pos];
    const size_t query_base=size_t(qid[0])*d;
    const size_t point_base=size_t(id)*d;
    const size_t tile=size_t(pos/32)*size_t(d)*32;
    const int lane=pos&31;
    const double cutoff=__dmul_rn(double(radius),double(radius));
    double sum=0;
    for(int j=0;j<d;++j) {
        const float x=Layout?packed[tile+size_t(j)*32+lane]:data[point_base+j];
        const float q=data[query_base+j];
        const double delta=__dsub_rn(double(x),double(q));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));
        if constexpr(Early) {
            if((j&31)==31 && sum>cutoff) {
                hits[pos]=0;
                if constexpr(Count)processed[pos]=j+1;
                return;
            }
        }
    }
    if constexpr(Count)processed[pos]=d;
    const bool hit=sum<=cutoff;
    hits[pos]=int(hit);
    if(hit) {
        rawids[pos]=id;
        rawdis[pos]=float(sqrt(sum));
    }
}
