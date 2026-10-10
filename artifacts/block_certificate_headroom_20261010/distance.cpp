// Ordered FP64 distance oracle helper; not a GPU implementation or a latency benchmark.
#include <cmath>
#include <cstdint>
#include <limits>
extern "C" int distances(const float* x, int64_t n, int d, int64_t pivot, double* out) {
    if(n<=0 || d<=0 || d>4096 || pivot<0 || pivot>=n) return 1;
    const float* p=x+pivot*d;
    int invalid=0;
    #pragma omp parallel for reduction(|:invalid) schedule(static) num_threads(4)
    for(int64_t i=0;i<n;i++) {
        double s=0;
        for(int j=0;j<d;j++) {
            double a=x[i*d+j], b=p[j];
            if(!std::isfinite(a)||!std::isfinite(b)) invalid=1;
            double delta=a-b; s+=delta*delta;
        }
        out[i]=s;
    }
    return invalid;
}
