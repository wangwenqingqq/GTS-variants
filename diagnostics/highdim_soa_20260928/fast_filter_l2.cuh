#pragma once

// Fast reject-only prefilter. The original flatL2 arithmetic is rerun for
// every point which passes, so hit distances and ordered hashes remain exact
// relative to F on validated data. The 0.01 guard is empirical, not a formal
// floating-point error bound for arbitrary inputs.
__global__ void filteredFlatL2(const int* id_list,const float* data_d,
                               const int* qid,const int* data_info,float r,
                               const int* is_delete,int n,double exact_cutoff,
                               double fast_cutoff,int* hits,int* rawids,
                               float* rawdis) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=n)return;
    hits[pos]=0;
    const int data_id=id_list[pos],query_id=qid[0];
    if(is_delete[data_id]!=0 || r<0)return;
    float result=0;
    bool rejected=false;
    if(data_id!=query_id) {
        float quick=0;
        for(int j=0;j<data_info[0];++j) {
            const float delta=data_d[size_t(data_id)*data_info[0]+j]-
                              data_d[size_t(query_id)*data_info[0]+j];
            quick=__fadd_rn(quick,__fmul_rn(delta,delta));
            if((j&31)==31 && double(quick)>fast_cutoff) {
                rejected=true;break;
            }
        }
        if(rejected)return;
        for(int j=0;j<data_info[0];++j) {
            result+=pow(data_d[size_t(data_id)*data_info[0]+j]-
                        data_d[size_t(query_id)*data_info[0]+j],2);
            if((j&31)==31 && double(result)>exact_cutoff) {
                rejected=true;break;
            }
        }
        if(!rejected)result=pow(result,0.5);
    }
    if(!rejected && result<=r) {
        hits[pos]=1;rawids[pos]=data_id;rawdis[pos]=result;
    }
}
