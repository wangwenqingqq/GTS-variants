__global__ void findNextRnn(int* flags,int start,TN* nodes,float radius,float* data,int* qids,
    int count,int* nn,int* info,int* empty,char*,int*) {
    int q=blockIdx.x;__shared__ double rupper;
    if(!threadIdx.x)rupper=target::radius_upper(radius,info[0]);__syncthreads();
    for(int i=threadIdx.x;i<count;i+=blockDim.x){int nid=start+i;
        if(nid<nn[0]&&flags[q*nn[0]+(nid-1)/TREE_ORDER]&&!empty[nid]&&nodes[nid].size>0){
            auto qi=target::norm_query(data,info[0],nodes[nid].pid,data+size_t(qids[q])*info[0]);
            if(target::survives(target::bounds.lo[nid],target::bounds.hi[nid],qi,rupper))flags[q*nn[0]+nid]=1;}}
}
