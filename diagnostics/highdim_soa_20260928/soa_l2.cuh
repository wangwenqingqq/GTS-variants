#pragma once

// Keep the tree's id_list order, but store each coordinate contiguously for
// 32 adjacent output positions. The result selector can therefore remain the
// same as in F, including its exact ordered float32 output.
__global__ void reorderSoA32(const int* id_list,const float* data_d,
                             float* soa,int n,int dim) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    const int id=id_list[pos];
    const size_t tile=size_t(pos/32)*size_t(dim)*32;
    const int lane=pos&31;
    for(int j=0;j<dim;++j)
        soa[tile+size_t(j)*32+lane]=data_d[size_t(id)*dim+j];
}

// Same scalar accumulation, 32-coordinate early reject, final square root,
// deletion mapping and hit order as flatL2. Only the point-vector read layout
// changes. The query remains in original data order.
__global__ void soaFlatL2(const int* id_list,const float* soa,const float* data_d,
                          const int* qid,const int* data_info,float r,
                          const int* is_delete,int n,double cutoff,
                          int* hits,int* rawids,float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    hits[pos]=0;
    const int data_id=id_list[pos],query_id=qid[0];
    if(is_delete[data_id]!=0)return;
    const int dim=data_info[0];
    const size_t tile=size_t(pos/32)*size_t(dim)*32;
    const int lane=pos&31;
    float result=0;
    bool rejected=false;
    if(data_id!=query_id) {
        for(int j=0;j<dim;++j) {
            result+=pow(soa[tile+size_t(j)*32+lane]-
                        data_d[size_t(query_id)*dim+j],2);
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
