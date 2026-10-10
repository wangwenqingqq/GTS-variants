// Diagnostic-only observers; no index, pruning or queue state is modified.
#pragma once
#include <vector>
#include <stdexcept>
static int trace_call = -1;
__device__ int trace_call_d;
static void trace_check(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> void trace_array(const char* stage,T* data,int n){
    if(trace_call!=0)return;
    if(n<0||n>100000)throw std::runtime_error("trace capacity");
    std::vector<T> host(n);if(n)trace_check(cudaMemcpy(host.data(),data,n*sizeof(T),cudaMemcpyDeviceToHost));
    for(int i=0;i<n;i++)printf("TRACE %s %d %.17g\n",stage,i,double(host[i]));
}
__global__ void trace_topology(BPlusNode** roots,int* np,int* tp,int* tn){
    if(blockIdx.x||threadIdx.x)return;
    for(int p=0;p<PNUM;p++)for(int t=0;t<tn[p];t++){
        int root=np[tp[p]+t];BPlusNode* stack[2048];int top=0,seen=0;stack[top++]=roots[root];
        while(top){
            BPlusNode* n=stack[--top];if(++seen>2048){printf("TRACE ERROR cycle\n");return;}
            for(int j=0;j<n->KeyNum[0];j++){
                auto child=n->Children[j];
                printf("TRACE MAP %d %d %d %d %d %d %.9g\n",p,root,n->idx[0],j,child?child->idx[0]:-1,n->id[j],double(n->Key[j]));
                if(child){if(top==2048){printf("TRACE ERROR overflow\n");return;}stack[top++]=child;}
            }
        }
    }
}
__global__ void trace_heaps(PriorityQueue_k** queues,int n){
    if(blockIdx.x||threadIdx.x||trace_call_d!=0)return;
    for(int i=0;i<n;i++){
        auto q=queues[i];printf("TRACE HEAP_SIZE %d %d\n",i,q->size_k);
        for(int j=1;j<=q->size_k;j++)printf("TRACE HEAP %d %d %d %.9g\n",i,j,q->id[j],double(q->dis[j]));
    }
}
