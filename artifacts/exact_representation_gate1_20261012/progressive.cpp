// CPU-only diagnostic: preserve ordered FP64 while observing the first strict crossing.
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53,"IEEE FP64 required");
static_assert(std::numeric_limits<float>::is_iec559 && std::numeric_limits<float>::digits==24,"IEEE FP32 required");
extern "C" int progressive_scores(const float* data,const float* query,double* full,
    uint16_t* required,double* before,double* crossing,size_t n,int d,double threshold) {
    if(!data||!query||!full||!required||!before||!crossing||!n||d<1||d>960||
       !std::isfinite(threshold)||threshold<0||std::fegetround()!=FE_TONEAREST)return 1;
    for(int j=0;j<d;++j)if(!std::isfinite(query[j]))return 2;
    for(size_t i=0;i<n;++i) {
        double sum=0,previous=0,first_before=0,first_at=0;
        int first=0;
        for(int j=0;j<d;++j) {
            const float coordinate=data[i*size_t(d)+j];
            if(!std::isfinite(coordinate))return 2;
            const double delta=double(coordinate)-double(query[j]);
            const double square=delta*delta;
            previous=sum;sum=sum+square;
            if(!std::isfinite(sum)||sum<previous)return 3;
            if(!first&&sum>threshold){first=j+1;first_before=previous;first_at=sum;}
        }
        full[i]=sum;required[i]=uint16_t(first?first:d);
        before[i]=first?first_before:previous;crossing[i]=first?first_at:sum;
    }
    return 0;
}
