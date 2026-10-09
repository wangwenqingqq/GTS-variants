// Independent CPU row scan. No tree, pruning, FMA, cross-row reduction or GPU code.
#include <cstdint>
#include <cstddef>
#include <cfenv>
#include <limits>
static_assert(std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53,"IEEE FP64 required");
extern "C" int ordered_scores(const float* data,const int64_t* physical,const float* query,double* output,
                             size_t n,int d,int threads) {
    if(!data||!physical||!query||!output||(d!=128&&d!=960)||threads<1||threads>16)return 1;
    int bad=0;
    #pragma omp parallel num_threads(threads) reduction(|:bad)
    {
        bad|=std::fesetround(FE_TONEAREST)!=0;
        #pragma omp for schedule(static)
        for(size_t p=0;p<n;p++) {
            const float* row=data+size_t(physical[p])*d;double sum=0;
            for(int j=0;j<d;j++) {double delta=double(row[j])-double(query[j]);double square=delta*delta;sum=sum+square;}
            output[p]=sum;
        }
    }
    return bad;
}
