// CPU-only ordered-prefix replay upper-bound screen, before CUDA implementation.
#include <cmath>
#include <cstdint>
extern "C" int prefix_cost(const float* x,const float* q,int n,double cutoff,
                           uint64_t* counts,double* full){
    const int k[4]={128,256,512,960};
    for(int i=0;i<8;i++)counts[i]=0;
    for(int row=0;row<n;row++){
        double sum=0;bool active=true;int stage=0;
        for(int j=0;j<960;j++){
            double delta=double(x[uint64_t(row)*960+j])-double(q[j]);
            double term=delta*delta;sum=sum+term;
            if(j+1==k[stage]){
                if(active){
                    bool hit=sum<=cutoff;
                    bool near=std::abs(sum-cutoff)<=std::ldexp(cutoff,-14)+std::ldexp(1.,-100);
                    if(near||(stage==3&&hit))++counts[4+stage];
                    if(hit)++counts[stage];else active=false;
                }
                if(stage<3)++stage;
            }
        }
        if(!std::isfinite(sum))return 1;full[row]=sum;
    }
    return 0;
}
