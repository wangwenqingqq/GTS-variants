// CPU diagnostic only. Ordered FP64 accumulation matches the Gate1/Gate3 oracle.
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53,"IEEE FP64 required");
static_assert(std::numeric_limits<float>::is_iec559 && std::numeric_limits<float>::digits==24,"IEEE FP32 required");

static double safe_lower(double sum) {
    return std::max(0., std::nextafter(sum*(1.-0x1p-40)-0x1p-100, -INFINITY));
}

extern "C" int interval_prefix(const float* x, const float* q, const uint8_t* code,
    const double* lut, size_t n, double cutoff, double* exact128, double* exact256,
    double* lower128, double* lower256, double* fallback) {
    if(!x||!q||!code||!lut||!n||!exact128||!exact256||!lower128||!lower256||!fallback||
       !std::isfinite(cutoff)||cutoff<0||
       std::fegetround()!=FE_TONEAREST)return 1;
    int bad=0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for(size_t row=0;row<n;row++) {
        double exact=0, lower=0;
        for(int j=0;j<256;j++) {
            double delta=double(x[row*960+j])-double(q[j]);
            double square=delta*delta;exact=exact+square;
            double term=lut[j*256+code[row*256+j]];lower=lower+term;
            if(!std::isfinite(exact)||!std::isfinite(lower)||term<0)bad=2;
            if(j==127){exact128[row]=exact;lower128[row]=safe_lower(lower);}
        }
        exact256[row]=exact;lower256[row]=safe_lower(lower);fallback[row]=NAN;
        // Full-prefix calculation above is also an all-row diagnostic bound check.
        // A screened service would reread those coordinates only for code survivors.
        if(lower256[row]<=cutoff&&exact<=cutoff) {
            for(int j=256;j<512;j++) {
                double delta=double(x[row*960+j])-double(q[j]);
                double square=delta*delta;exact=exact+square;
            }
            if(exact<=cutoff) {
                for(int j=512;j<960;j++) {
                    double delta=double(x[row*960+j])-double(q[j]);
                    double square=delta*delta;exact=exact+square;
                }
                fallback[row]=exact;
            }
        }
    }
    return bad;
}

extern "C" int knn_crossings(const float* x, const float* q, size_t n, int d,
    double oracle_cutoff, double seed_cutoff, double* full,
    uint16_t* dims0, uint16_t* dims1, double* before0, double* crossing0,
    double* before1, double* crossing1) {
    if(!x||!q||!n||d<1||d>960||!full||!dims0||!dims1||!before0||!crossing0||
       !before1||!crossing1||!std::isfinite(oracle_cutoff)||oracle_cutoff<0||
       !std::isfinite(seed_cutoff)||seed_cutoff<oracle_cutoff||
       std::fegetround()!=FE_TONEAREST)return 1;
    int bad=0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for(size_t row=0;row<n;row++) {
        double sum=0, previous=0, b0=0, c0=0, b1=0, c1=0;int first0=0,first1=0;
        for(int j=0;j<d;j++) {
            double delta=double(x[row*size_t(d)+j])-double(q[j]);
            double square=delta*delta;previous=sum;sum=sum+square;
            if(!std::isfinite(sum)||sum<previous)bad=2;
            if(!first0&&sum>oracle_cutoff){first0=j+1;b0=previous;c0=sum;}
            if(!first1&&sum>seed_cutoff){first1=j+1;b1=previous;c1=sum;}
        }
        full[row]=sum;dims0[row]=uint16_t(first0?first0:d);dims1[row]=uint16_t(first1?first1:d);
        before0[row]=first0?b0:previous;crossing0[row]=first0?c0:sum;
        before1[row]=first1?b1:previous;crossing1[row]=first1?c1:sum;
    }
    return bad;
}
