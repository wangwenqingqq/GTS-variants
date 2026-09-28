#pragma once

// Scan the unresolved frontier after a dataset-wide fixed number of tree levels.
// Positions remain in id_list order so result compaction matches the exact F path.
__global__ void cutoffL2(const int* id_list,const float* data_d,const int* qid,
                         const int* data_info,float r,const int* is_delete,
                         int n,double cutoff,const int* node_for_pos,const int* flags,
                         int* hits,int* rawids,float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    hits[pos]=0;
    if(flags[node_for_pos[pos]]!=1)return;
    const int data_id=id_list[pos],query_id=qid[0];
    if(is_delete[data_id]!=0)return;
    float result=0;
    bool rejected=false;
    if(data_id!=query_id) {
        for(int j=0;j<data_info[0];++j) {
            result+=pow(data_d[data_id*data_info[0]+j]-
                        data_d[query_id*data_info[0]+j],2);
            if(r>=0 && (j&31)==31 && double(result)>cutoff) {
                rejected=true;break;
            }
        }
        if(!rejected)result=pow(result,0.5);
    }
    if(!rejected && result<=r) {
        hits[pos]=1;rawids[pos]=data_id;rawdis[pos]=result;
    }
}
