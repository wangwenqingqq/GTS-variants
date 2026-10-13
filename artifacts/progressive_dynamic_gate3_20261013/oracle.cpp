// CPU-only ordered FP64 oracle; parallel rows never change coordinate order.
#include <cstdint>
extern "C" void exact_scores(const float* x,const float* q,int n,int d,double* out){
    #pragma omp parallel for schedule(static)
    for(int r=0;r<n;r++){
        double s=0;
        for(int j=0;j<d;j++){double a=double(x[uint64_t(r)*d+j])-double(q[j]);double t=a*a;s=s+t;}
        out[r]=s;
    }
}
