#pragma once

__global__ void pcaReorder(const int* id_list,const float* by_id,float* by_dim,int n) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    const int id=id_list[pos];
    for(int j=0;j<64;++j)by_dim[size_t(j)*n+pos]=by_id[size_t(id)*64+j];
}

// The projected vectors are a reject-only filter. Every survivor follows the
// exact F arithmetic and output path, retaining its result ordering and bits.
__global__ void pcaFlatL2(const int* id_list,const float* data_d,const int* qid,
                          const int* data_info,float r,const int* is_delete,
                          const float* projected_by_dim,const float* projected_by_id,
                          int n,int k,double pca_cutoff,double exact_cutoff,
                          int* hits,int* rawids,float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    hits[pos]=0;
    const int data_id=id_list[pos],query_id=qid[0];
    if(is_delete[data_id]!=0)return;
    float result=0;
    bool rejected=false;
    if(data_id!=query_id) {
        if(r>=0) {
            float lower2=0;
            for(int j=0;j<k;++j) {
                const float delta=projected_by_dim[size_t(j)*n+pos]-
                                  projected_by_id[size_t(query_id)*64+j];
                lower2+=delta*delta;
            }
            if(double(lower2)>pca_cutoff)return;
        }
        for(int j=0;j<data_info[0];++j) {
            result+=pow(data_d[data_id*data_info[0]+j]-
                        data_d[query_id*data_info[0]+j],2);
            if(r>=0 && (j&31)==31 && double(result)>exact_cutoff) {
                rejected=true;break;
            }
        }
        if(!rejected)result=pow(result,0.5);
    }
    if(!rejected && result<=r) {
        hits[pos]=1;rawids[pos]=data_id;rawdis[pos]=result;
    }
}
