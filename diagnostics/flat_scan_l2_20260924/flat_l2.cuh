#pragma once

// Exact batch-one L2 scan in tree leaf order. The tree's id_list is a
// permutation of records and concatenates leaves in node order, so this
// order matches the existing result selector after sound tree pruning.
__global__ void flatL2(const int* id_list,const float* data_d,const int* qid,
                       const int* data_info,float r,const int* is_delete,
                       int n,double cutoff,int* hits,int* rawids,float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    hits[pos]=0;
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

__global__ void flatResultSelect(int n,const int* hits,const int* rawids,
                                 const float* rawdis,const int* deletion_prefix,
                                 int* count,int* outids,float* outdis) {
    using Scan=cub::BlockScan<int,512>;
    __shared__ Scan::TempStorage scratch;
    int carry=0;
    for(int base=0;base<n;base+=512) {
        const int i=base+threadIdx.x;
        const int hit=i<n?hits[i]:0;
        int rank,total;
        Scan(scratch).ExclusiveSum(hit,rank,total);
        if(hit) {
            const int id=rawids[i];
            outids[carry+rank]=id-deletion_prefix[id];
            outdis[carry+rank]=rawdis[i];
        }
        __syncthreads();
        carry+=total;
    }
    if(threadIdx.x==0)*count=carry;
}
