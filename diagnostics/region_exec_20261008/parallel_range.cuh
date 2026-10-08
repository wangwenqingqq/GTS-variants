#pragma once
#include "region_output.cuh"
namespace rex {
// One block per parent, rather than one block traversing a whole query layer.
// Distances are owned by the first child with the same ACTUAL pid (not assumed).
__device__ inline bool first_pid(View v,int parent,int child) {
    int first=parent*v.arity+1;
    for(int c=first;c<child;c++) if(c<v.node_count && !v.empty[c] && v.nodes[c].size>0 && v.nodes[c].pid==v.nodes[child].pid)return false;
    return true;
}
__global__ void parent_groups(View v,const int* parents,int begin,const int* current,int* next,int* active,float radius,Work w) {
    int parent=parents[begin+blockIdx.x]; if(!current[parent])return;
    __shared__ float query[QUERY_DIM],distance[10];
    for(int j=threadIdx.x;j<QUERY_DIM;j+=blockDim.x)query[j]=v.data[v.qids[0]*QUERY_DIM+j];
    __syncthreads();int k=threadIdx.x;
    int child=parent*v.arity+1+k;
    if(k<v.arity && child<v.node_count && !v.empty[child] && v.nodes[child].size>0 && first_pid(v,parent,child)) {
        count(w.pivots,child);distance[k]=legacy_pivot_distance(v.data,v.nodes[child].pid,query);
    }
    __syncthreads();
    if(k<v.arity && child<v.node_count && !v.empty[child] && v.nodes[child].size>0) {
        int owner=k;
        for(int j=0;j<k;j++)if(!v.empty[parent*v.arity+1+j] && v.nodes[parent*v.arity+1+j].size>0 && v.nodes[parent*v.arity+1+j].pid==v.nodes[child].pid){owner=j;break;}
        count(w.nodes,child);
        next[child]=active[child]=legacy_bound(v.nodes,child,v.arity,distance[owner],radius);
    }
}
__global__ void materialize(View v,const int* leaves,int leaf_count,const int* flags,int* leaf_list,Work w) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=leaf_count)return;
    int nid=leaves[i];leaf_list[i]=flags[nid]?nid:-1;
    if(flags[nid])count(w.leaves,nid);
}
}
