// CPU projection: ordered FP64 dots, four lanes; independent scalar entry for audit.
#include <cmath>
#include <cstdint>
#include <limits>
#include <cfenv>
#if defined(__x86_64__) || defined(__i386__)
#include <xmmintrin.h>
#endif
extern "C" int projections(const float* x, int64_t n, int d, const double* u,
                            double* out, double* maxabs, int scalar) {
    if (!x || !u || !out || !maxabs || n<=0 || d<=0 || d>4096 ||
        n>std::numeric_limits<int64_t>::max()/d || n>std::numeric_limits<int64_t>::max()/4) return 1;
    if (std::fegetround()!=FE_TONEAREST) return 1;
#if defined(__x86_64__) || defined(__i386__)
    if (_mm_getcsr() & 0x8040) return 1; // No flush-to-zero or denormals-are-zero.
#endif
    for (int i=0;i<d*4;++i) if (!std::isfinite(u[i]) || std::fabs(u[i])>1) return 1;
    int bad=0;
    #pragma omp parallel for schedule(static) reduction(|:bad) num_threads(4)
    for (int64_t row=0;row<n;++row) {
        double m=0;
        if (scalar) {
            for (int k=0;k<d;++k) {
                double v=x[row*d+k];if (!std::isfinite(v)) bad=1;
                if (std::fabs(v)>m) m=std::fabs(v);
            }
            for (int j=0;j<4;++j) {
                double s=0;
                for (int k=0;k<d;++k) s+=double(x[row*d+k])*u[k*4+j];
                out[row*4+j]=s;
            }
        } else {
            double s[4]={0,0,0,0};
            for (int k=0;k<d;++k) {
                double v=x[row*d+k];if (!std::isfinite(v)) bad=1;
                if (std::fabs(v)>m) m=std::fabs(v);
                for (int j=0;j<4;++j) s[j]+=v*u[k*4+j];
            }
            for (int j=0;j<4;++j) out[row*4+j]=s[j];
        }
        maxabs[row]=m;
    }
    return bad;
}
