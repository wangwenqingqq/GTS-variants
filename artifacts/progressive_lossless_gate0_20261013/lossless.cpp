// CPU logical-byte reference. Candidate search has no raw-vector/oracle pointer.
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559 &&
              std::numeric_limits<float>::digits==24, "IEEE FP32 required");
static_assert(sizeof(double)==8 && std::numeric_limits<double>::is_iec559 &&
              std::numeric_limits<double>::digits==53, "IEEE FP64 required");

static uint32_t inverse(uint32_t key) {
    return key & 0x80000000u ? key ^ 0x80000000u : ~key;
}
static double value(uint32_t key) {
    uint32_t u=inverse(key); float x; std::memcpy(&x,&u,4); return double(x);
}
static double down(double x) {
    if(x==0) return 0;
    uint64_t u; std::memcpy(&u,&x,8); --u; std::memcpy(&x,&u,8); return x;
}
static bool interval(uint32_t key,int b,double& lo,double& hi) {
    const uint32_t mask=b==32?0u:(uint32_t(1)<<(32-b))-1;
    uint32_t low=std::max(key & ~mask,0x00800000u);
    uint32_t high=std::min(key | mask,0xff7fffffu);
    if(low>high) return false;
    lo=value(low); hi=value(high); return true;
}
extern "C" int interval_key(uint32_t key,int b,double* bounds) {
    if(!bounds || !(b==4||b==8||b==16||b==32)) return 2;
    return interval(key,b,bounds[0],bounds[1])?0:1;
}
static uint32_t nibble(const uint8_t* layer,size_t row,int d,int j) {
    uint8_t v=layer[row*size_t((d+1)/2)+j/2];
    return j%2?v & 15:v>>4;
}
static uint32_t complete(const uint8_t* a,const uint8_t* b,const uint8_t* c,
    const uint8_t* e,size_t row,int d,int j) {
    size_t i=row*size_t(d)+j;
    return (nibble(a,row,d,j)<<28) | (nibble(b,row,d,j)<<24) |
        (uint32_t(c[i])<<16) | uint32_t(e[2*i]) | (uint32_t(e[2*i+1])<<8);
}
extern "C" int recover(const uint8_t* a,const uint8_t* b,const uint8_t* c,
    const uint8_t* e,size_t n,int d,uint32_t* out) {
    if(!a||!b||!c||!e||!n||d<1||d>960||!out) return 1;
    #pragma omp parallel for schedule(static)
    for(size_t row=0;row<n;row++)
        for(int j=0;j<d;j++) out[row*size_t(d)+j]=inverse(complete(a,b,c,e,row,d,j));
    return 0;
}
extern "C" int search(const uint8_t* a,const uint8_t* b,const uint8_t* c,
    const uint8_t* e,const float* q,size_t n,int d,double cutoff,uint8_t* bits,
    double* lower,double* full) {
    if(!a||!b||!c||!e||!q||!n||d<1||d>960||!bits||!lower||!full||
       !std::isfinite(cutoff)||cutoff<0||std::fegetround()!=FE_TONEAREST) return 1;
    for(int j=0;j<d;j++) if(!std::isfinite(q[j])) return 2;
    int bad=0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for(size_t row=0;row<n;row++) {
        // Retain fetched prefixes locally; each next stage reads only new bits.
        uint32_t prefix[960]; double previous=0; bool rejected=false;
        for(int s=0;s<3;s++) {
            const int width=s==0?4:s==1?8:16; double sum=0;
            for(int j=0;j<d;j++) {
                if(s==0) prefix[j]=nibble(a,row,d,j)<<28;
                else if(s==1) prefix[j]|=nibble(b,row,d,j)<<24;
                else prefix[j]|=uint32_t(c[row*size_t(d)+j])<<16;
                double lo,hi;
                if(!interval(prefix[j],width,lo,hi)) {bad=3;lo=hi=0;}
                const double query=double(q[j]);
                double gap=query<lo?lo-query:query>hi?query-hi:0;
                gap=down(gap); const double square=down(gap*gap);
                sum=down(sum+square);
            }
            sum=std::max(previous,sum); previous=sum;
            lower[size_t(s)*n+row]=sum;
            if(!std::isfinite(sum)||sum<0) bad=4;
            if(sum>cutoff) {bits[row]=uint8_t(width);rejected=true;break;}
        }
        if(rejected) continue;
        double sum=0;
        for(int j=0;j<d;j++) {
            const size_t i=row*size_t(d)+j;
            uint32_t key=prefix[j] | uint32_t(e[2*i]) | (uint32_t(e[2*i+1])<<8);
            if(key<0x00800000u||key>0xff7fffffu) {bad=3;key=0x80000000u;}
            const double delta=value(key)-double(q[j]);
            const double square=delta*delta; sum=sum+square;
        }
        bits[row]=32;full[row]=sum;
        if(!std::isfinite(sum)||sum<previous) bad=4;
    }
    return bad;
}
