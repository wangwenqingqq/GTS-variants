#pragma once
#include "region_types.hpp"
namespace rex {
// Extracted L2 branch: float accumulator, original ascending dimension order,
// original pow overloads. config.cuh's short->float alias remains unchanged.
__device__ __forceinline__ float legacy_pivot_distance(const float* data,int pid,const float* query) {
    float dis_q=0;
    for(int j=0;j<QUERY_DIM;j++) dis_q+=pow(data[pid*QUERY_DIM+j]-query[j],2);
    dis_q=pow(dis_q,0.5);
    return dis_q;
}
__device__ __forceinline__ float legacy_object_distance(const float* data,int id,int qid,const float* query) {
    float result=0;
    if(id==qid) {} // Original special self branch; no distance evaluation.
    else {
        for(int j=0;j<QUERY_DIM;j++) result+=pow(data[id*QUERY_DIM+j]-query[j],2);
        result=pow(result,0.5);
    }
    return result;
}
__device__ __forceinline__ bool legacy_bound(const Node* nodes,int nid,int arity,float dis_q,float radius) {
    float dis_lb=nodes[nid].min_dis-dis_q;
    dis_lb=max(dis_lb,0.0);
    if(nid%arity!=0) {
        float dis_lb2=dis_q-nodes[nid+1].min_dis;
        dis_lb=max(dis_lb,dis_lb2);
    }
    return dis_lb<=radius;
}
#ifdef REGION_COUNTERS
__device__ inline void count(unsigned long long* x,int i) {atomicAdd(x+i,1ULL);}
#else
__device__ inline void count(unsigned long long*,int) {}
#endif
}
