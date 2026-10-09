__global__ void leafProcessRnnUpdate(int* leaves,TN* nodes,int* order,int* query_index,float* data,
    int* qids,int* ids,float* fields,int* info,float radius,int* hits,int* count,char*,int*,int* deleted) {
    int bid=blockIdx.x;if(bid>=count[0])return;TN node=nodes[leaves[bid]];
    int qid=qids[query_index[bid]];
    for(int j=threadIdx.x;j<node.size&&node.is_leaf;j+=blockDim.x){int id=order[node.lid+j];
        if(!deleted[id]){float field;bool keep=target::hit(data,info[0],id,data+size_t(qid)*info[0],radius,field);
            if(keep){int slot=bid*MAX_SIZE+j;hits[slot]=1;ids[slot]=id;fields[slot]=field;}}}
}
