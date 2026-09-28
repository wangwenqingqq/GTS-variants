#pragma once

// Batch-one L2 leaf path. Early=false isolates metric specialization.
// Early=true preserves all hit distances but may stop a provable miss after
// each 32-coordinate chunk; cutoff is set conservatively by the host.
template<bool Early>
__global__ void leafL2(int *query_lnode, TN *node_list, int *id_list,
                       int *query_qid, float *data_d, int *qid_list,
                       int *init_result_id, float *init_result_dis,
                       int *data_info, float r, int *qresult_idx,
                       int *search_num, int *is_delete, double cutoff) {
    const int bid=blockIdx.x;
    const int tid=threadIdx.x;
    if(bid < search_num[0]) {
        __shared__ int query_id[1];
        __shared__ TN node[1];
        if(tid==0) {
            query_id[0]=query_qid[bid];
            node[0]=node_list[query_lnode[bid]];
        }
        __syncthreads();
        for(int i=tid; i<node[0].size && node[0].is_leaf==1; i+=blockDim.x) {
            const int data_id=id_list[i+node[0].lid];
            const int qid=qid_list[query_id[0]];
            if(is_delete[data_id]==0) {
                float result=0;
                bool rejected=false;
                if(data_id!=qid) {
                    for(int j=0;j<data_info[0];j++) {
                        result += pow(data_d[data_id*data_info[0]+j]-
                                      data_d[qid*data_info[0]+j],2);
                        if constexpr(Early) {
                            if(r>=0 && (j&31)==31 && double(result)>cutoff) {
                                rejected=true;
                                break;
                            }
                        }
                    }
                    if(!rejected) result=pow(result,0.5);
                }
                if(!rejected && result<=r) {
                    qresult_idx[bid*MAX_SIZE+i]=1;
                    init_result_id[bid*MAX_SIZE+i]=data_id;
                    init_result_dis[bid*MAX_SIZE+i]=result;
                }
            }
        }
    }
}
