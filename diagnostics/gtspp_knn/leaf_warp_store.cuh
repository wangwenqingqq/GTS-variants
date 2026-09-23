// Warp-coalesced reads; one shared handoff restores thread-coalesced finalization.
template <bool VectorQuery>
__device__ __forceinline__ void knnLeafL2Warp(
    TN* nodes, float* disk, float* data, int* qids, float* queries, int* info,
    double* work, int offset, int* ids, int level, int* sizes)
{
    const int bid=blockIdx.x, lane=threadIdx.x&31, warp=threadIdx.x>>5;
    const int slots=sizes[level]/(MAX_SIZE*3+3);
    const int nid=int(work[offset+slots+bid]);
    const int qid=int(work[offset+2*slots+bid]);
    const TN node=nodes[nid];
    const int d=info[0];
    const float* query=VectorQuery ? queries+qid*d : data+qids[qid]*d;
    __shared__ int point_ids[20];
    __shared__ double point_sums[20];
    for(int did=warp;did<MAX_SIZE;did+=blockDim.x/32){
        int id=-1;double sum=0;
        if(did<node.size&&node.is_leaf==1){
            id=ids[node.lid+did];
            if(VectorQuery||id!=qids[qid]){
                for(int j=lane;j<d;j+=32){float diff=data[id*d+j]-query[j];sum+=diff*diff;}
            }
            for(int step=16;step;step>>=1)sum+=__shfl_down_sync(0xffffffffu,sum,step);
        }
        if(lane==0){point_ids[did]=id;point_sums[did]=sum;}
    }
    __syncthreads();
    const int did=threadIdx.x;
    if(did<MAX_SIZE){
        const int id=point_ids[did];float distance=INFI_DIS;
        if(id>=0){distance=sqrtf(point_sums[did]);if(distance>disk[qid])distance=INFI_DIS;}
        work[offset+slots*3+bid*MAX_SIZE+did]=double(id);
        work[offset+slots*(3+MAX_SIZE)+bid*MAX_SIZE+did]=double(distance);
        work[offset+slots*(3+2*MAX_SIZE)+bid*MAX_SIZE+did]=double(double(distance)/INFI_DIS+qid*DIS_CODE);
    }
}
