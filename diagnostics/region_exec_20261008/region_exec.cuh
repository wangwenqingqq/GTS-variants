#pragma once
#include "parallel_range.cuh"
namespace rex {
// Shared traversal for both interventions; only the final leaf handoff differs.
template<bool Fused,bool Warp=false>
__global__ void traverse_regions(View v,const int* root_active,uint64_t task_epoch,
                                int* global_leaves,int* global_counts,float radius,
                                int* hit,float* distances,int* error,Work w) {
    int rid=blockIdx.x;Region region=v.regions[rid];
    RegionTask task{0,rid,region.root,task_epoch};
    if(task.tree_epoch!=v.tree_epoch) {
        if(!threadIdx.x){atomicExch(error,1);if(!Fused)global_counts[rid]=0;}return;
    }
    if(!root_active[region.root]) {if(!Fused && !threadIdx.x)global_counts[rid]=0;return;}
    __shared__ float query[QUERY_DIM];
    __shared__ int frontier[LOCAL_NODE_CAPACITY],next[LOCAL_NODE_CAPACITY],leaves[LOCAL_NODE_CAPACITY];
    __shared__ int nf,nn,nl,failed;
    for(int j=threadIdx.x;j<QUERY_DIM;j+=blockDim.x)query[j]=v.data[v.qids[0]*QUERY_DIM+j];
    if(!threadIdx.x){nf=1;frontier[0]=region.root;nl=0;failed=0;}
    __syncthreads();
    while(nf && !failed) {
        if(!threadIdx.x)nn=0;
        __syncthreads();
        if(threadIdx.x<nf) {
            int nid=frontier[threadIdx.x];Node node=v.nodes[nid];
            if(node.is_leaf) {
                int pos=atomicAdd(&nl,1);
                if(pos>=LOCAL_NODE_CAPACITY || pos>=region.leaves)atomicExch(&failed,1);
                else {leaves[pos]=nid;count(w.leaves,nid);}
            } else {
                // Same actual-pid owner and native expression as parent_groups.
                float cached[10];
                for(int k=0;k<v.arity;k++) {
                    int child=nid*v.arity+1+k;
                    if(child>=v.node_count || v.empty[child] || v.nodes[child].size==0)continue;
                    int owner=k;
                    for(int j=0;j<k;j++) {
                        int c=nid*v.arity+1+j;
                        if(!v.empty[c] && v.nodes[c].size>0 && v.nodes[c].pid==v.nodes[child].pid){owner=j;break;}
                    }
                    if(owner==k){cached[k]=legacy_pivot_distance(v.data,v.nodes[child].pid,query);count(w.pivots,child);}
                    count(w.nodes,child);
                    if(legacy_bound(v.nodes,child,v.arity,cached[owner],radius)) {
                        int pos=atomicAdd(&nn,1);
                        if(pos>=LOCAL_NODE_CAPACITY)atomicExch(&failed,1);else next[pos]=child;
                    }
                }
            }
        }
        __syncthreads();
        if(!threadIdx.x)nf=nn;
        __syncthreads();
        if(threadIdx.x<nf && threadIdx.x<LOCAL_NODE_CAPACITY)frontier[threadIdx.x]=next[threadIdx.x];
        __syncthreads();
    }
    if(failed){if(!threadIdx.x)atomicExch(error,2);return;}
    if(Fused) {
        if constexpr(Warp)verify_leaves_warp(v,leaves,nl,query,radius,hit,distances,w);
        else for(int i=0;i<nl;i++)verify_leaf(v,leaves[i],query,radius,hit,distances,w);
    } else {
        for(int i=threadIdx.x;i<nl;i+=blockDim.x)global_leaves[region.leaf_offset+i]=leaves[i];
        if(!threadIdx.x)global_counts[rid]=nl;
    }
}
template<bool Warp=false>
__global__ void verify_regions(View v,const int* leaf_list,const int* counts,float radius,int* hit,float* distances,Work w) {
    int rid=blockIdx.x;Region region=v.regions[rid];int nl=counts[rid];if(!nl)return;
    __shared__ float query[QUERY_DIM];
    for(int j=threadIdx.x;j<QUERY_DIM;j+=blockDim.x)query[j]=v.data[v.qids[0]*QUERY_DIM+j];
    __syncthreads();
    if constexpr(Warp)verify_leaves_warp(v,leaf_list+region.leaf_offset,nl,query,radius,hit,distances,w);
    else for(int i=0;i<nl;i++)verify_leaf(v,leaf_list[region.leaf_offset+i],query,radius,hit,distances,w);
}
}
