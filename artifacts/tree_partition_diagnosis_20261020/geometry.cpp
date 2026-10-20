// Construction only: no queries, thresholds, or reference arrays are accepted.
#include "../block_local_ball_20261011/pairs.cpp"
#include <algorithm>
#include <vector>
extern "C" int node_center(const float* x, int64_t n, int d, const int64_t* ids,
    int64_t m, double* mean, double* span, int64_t* center) {
    if (!x || !ids || !mean || !span || !center || n<=0 || d<=0 || d>4096 || m<=0 ||
        n>std::numeric_limits<int64_t>::max()/d) return 1;
    std::vector<double> low(d,INFINITY),high(d,-INFINITY),scores(m);
    std::fill(mean,mean+d,0.0);
    for (int64_t i=0;i<m;++i) {
        if (ids[i]<0 || ids[i]>=n || (i && ids[i]<=ids[i-1])) return 2;
        for (int j=0;j<d;++j) {
            double v=x[ids[i]*d+j];if(!std::isfinite(v)) return 3;
            mean[j]+=v;low[j]=std::min(low[j],v);high[j]=std::max(high[j],v);
        }
    }
    for (int j=0;j<d;++j) {mean[j]/=double(m);span[j]=high[j]-low[j];}
    #pragma omp parallel for schedule(static) num_threads(4)
    for (int64_t i=0;i<m;++i) {
        double s=0;
        for (int j=0;j<d;++j) {double delta=double(x[ids[i]*d+j])-mean[j];s+=delta*delta;}
        scores[i]=s;
    }
    int64_t best=0;
    for (int64_t i=1;i<m;++i) if(scores[i]<scores[best]) best=i;
    *center=ids[best];return 0;
}
