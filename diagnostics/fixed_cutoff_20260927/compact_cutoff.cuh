#pragma once

__global__ void frontierFlags(int n,const int* node_for_pos,const int* node_flags,int* active) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos<n)active[pos]=node_flags[node_for_pos[pos]]==1;
}

// CUB selects positions in increasing id_list order. Only those positions
// enter the exact L2 loop; the result selector scans this compact sequence.
__global__ void compactL2(const int* id_list,const float* data_d,const int* qid,
                          const int* data_info,float r,const int* is_delete,
                          const int* positions,const int* candidate_count,
                          double cutoff,int* hits,int* rawids,float* rawdis) {
    const int rank=blockIdx.x*blockDim.x+threadIdx.x;
    if(rank>=*candidate_count)return;
    hits[rank]=0;
    const int data_id=id_list[positions[rank]],query_id=qid[0];
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
        hits[rank]=1;rawids[rank]=data_id;rawdis[rank]=result;
    }
}

__global__ void compactResultSelect(const int* candidate_count,int n,
                                    const int* hits,const int* rawids,
                                    const float* rawdis,const int* deletion_prefix,
                                    int* count,int* outids,float* outdis) {
    using Scan=cub::BlockScan<int,512>;
    __shared__ Scan::TempStorage scratch;
    const int limit=*candidate_count;
    assert(limit>=0 && limit<=n);
    int carry=0;
    for(int base=0;base<limit;base+=512) {
        const int i=base+threadIdx.x;
        const int hit=i<limit?hits[i]:0;
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
