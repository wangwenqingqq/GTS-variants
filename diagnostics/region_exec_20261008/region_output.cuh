#pragma once
#include "legacy_ops.cuh"
namespace rex {
__device__ inline void verify_leaf(View v,int nid,const float* query,float radius,int* hit,float* distances,Work w) {
    Node node=v.nodes[nid];
    for(int j=threadIdx.x;j<node.size;j+=blockDim.x) {
        int id=v.order[node.lid+j];
        if(!v.deleted[id]) {
            if(id!=v.qids[0])count(w.objects,id);
            float distance=legacy_object_distance(v.data,id,v.qids[0],query);
            if(distance<=radius) {
                int slot=v.leaf_slot[nid]+j; hit[slot]=1;distances[slot]=distance;
            }
        }
    }
}
__global__ void verify_materialized(View v,const int* leaf_list,float radius,int* hit,float* distances,Work w) {
    int nid=leaf_list[blockIdx.x];if(nid<0)return;
    __shared__ float query[QUERY_DIM];
    for(int j=threadIdx.x;j<QUERY_DIM;j+=blockDim.x)query[j]=v.data[v.qids[0]*QUERY_DIM+j];
    __syncthreads();verify_leaf(v,nid,query,radius,hit,distances,w);
}
// N-sized flags/prefix/distances are intentionally retained in every new mode.
// The host performs common stable exclusive scan; each slot has one writer.
__global__ void collect(View v,const int* hit,const int* prefix,const float* distances,int* ids,float* result) {
    int s=blockIdx.x*blockDim.x+threadIdx.x;
    if(s<v.n && hit[s]){ids[prefix[s]]=v.slot_pid[s];result[prefix[s]]=distances[s];}
}
}
