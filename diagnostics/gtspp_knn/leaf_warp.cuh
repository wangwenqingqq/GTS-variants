// One warp owns one point; the original leaf-query CTA and result layout remain.
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
    for(int did=warp;did<MAX_SIZE;did+=16){
        int id=-1;double sum=0;float distance=INFI_DIS;
        const bool valid=did<node.size&&node.is_leaf==1;
        if(valid){
            id=ids[node.lid+did];
            if(VectorQuery||id!=qids[qid]){
                for(int j=lane;j<d;j+=32){float diff=data[id*d+j]-query[j];sum+=diff*diff;}
            }
            for(int step=16;step;step>>=1)sum+=__shfl_down_sync(0xffffffffu,sum,step);
            if(lane==0){distance=sqrtf(sum);if(distance>disk[qid])distance=INFI_DIS;}
        }
        if(lane==0){
            work[offset+slots*3+bid*MAX_SIZE+did]=double(id);
            work[offset+slots*(3+MAX_SIZE)+bid*MAX_SIZE+did]=double(distance);
            work[offset+slots*(3+2*MAX_SIZE)+bid*MAX_SIZE+did]=double(double(distance)/INFI_DIS+qid*DIS_CODE);
        }
    }
}
