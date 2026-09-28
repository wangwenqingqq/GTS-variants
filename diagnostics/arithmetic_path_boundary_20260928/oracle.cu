// Independent float64 reference. No GTS headers, tree, or measured kernels.
#include <cuda_runtime.h>
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <random>
#include <string>
#include <vector>

static void check(cudaError_t e) {
    if (e != cudaSuccess) { fprintf(stderr, "%s\n", cudaGetErrorString(e)); exit(2); }
}

// Keep the subtraction, square, and increasing-dimension accumulation distinct.
__global__ void reference(const float* data, int n, int d, int q, double* sums) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id >= n) return;
    double acc = 0.0;
    for (int j = 0; j < d; ++j) {
        double delta = __dsub_rn(double(data[size_t(id)*d+j]), double(data[size_t(q)*d+j]));
        double square = __dmul_rn(delta, delta);
        acc = __dadd_rn(acc, square);
    }
    sums[id] = acc;
}

// Built without contraction or fast math; deliberately independent of the GPU routine.
static double cpu_reference(const float* a, const float* b, int d) {
    double acc = 0.0;
    for (int j = 0; j < d; ++j) {
        double delta = double(a[j]) - double(b[j]);
        double square = delta * delta;
        acc = acc + square;
    }
    return acc;
}

static uint64_t bits(double v) { uint64_t u; memcpy(&u, &v, 8); return u; }

int main(int argc, char** argv) {
    if (argc != 5) {
        fprintf(stderr, "usage: oracle data.f32bin queries.qid output.sq64 cpu_sample_count\n");
        return 1;
    }
    std::ifstream in(argv[1], std::ios::binary);
    int32_t h[3]; in.read(reinterpret_cast<char*>(h), sizeof(h));
    if (!in || h[0] < 1 || h[0] > 960 || h[1] < 1 || h[1] > 1000000 || h[2] != 2) return 2;
    const int d=h[0], n=h[1];
    std::vector<float> data(size_t(n)*d);
    in.read(reinterpret_cast<char*>(data.data()), data.size()*sizeof(float));
    if (!in || in.peek()!=EOF) return 3;
    for (float v:data) if (!std::isfinite(v)) return 4;
    std::ifstream qi(argv[2]); int nq; qi>>nq;
    if (!qi || nq<1 || nq>100000) return 5;
    std::vector<int> qs(nq);
    for (int& q:qs) { qi>>q; if (!qi || q<0 || q>=n) return 6; }
    int extra; if (qi>>extra) return 7;
    const int samples=std::atoi(argv[4]); if (samples<0 || samples>n) return 8;
    float* dev_data; double* dev_sums;
    check(cudaMalloc(&dev_data,data.size()*sizeof(float)));
    check(cudaMalloc(&dev_sums,size_t(n)*sizeof(double)));
    check(cudaMemcpy(dev_data,data.data(),data.size()*sizeof(float),cudaMemcpyHostToDevice));
    std::ofstream out(argv[3],std::ios::binary|std::ios::trunc);
    if (!out) return 9;
    int32_t oh[3]={d,n,nq}; out.write(reinterpret_cast<const char*>(oh),sizeof(oh));
    std::vector<double> sums(n);
    std::mt19937_64 rng(20260928);
    for (int i=0;i<nq;++i) {
        const int q=qs[i];
        reference<<<(n+255)/256,256>>>(dev_data,n,d,q,dev_sums);
        check(cudaGetLastError());
        check(cudaMemcpy(sums.data(),dev_sums,size_t(n)*sizeof(double),cudaMemcpyDeviceToHost));
        auto inspect=[&](int id) {
            const double expected=cpu_reference(data.data()+size_t(id)*d,data.data()+size_t(q)*d,d);
            if (bits(expected)!=bits(sums[id])) {
                fprintf(stderr,"MISMATCH q=%d id=%d cpu=%016llx gpu=%016llx\n",q,id,
                        (unsigned long long)bits(expected),(unsigned long long)bits(sums[id]));
                exit(10);
            }
        };
        inspect(q);
        for (int k=0;k<samples;++k) inspect(samples==n?k:int(rng()%n));
        out.write(reinterpret_cast<const char*>(&q),sizeof(q));
        out.write(reinterpret_cast<const char*>(sums.data()),size_t(n)*sizeof(double));
        if (!out) return 11;
        fprintf(stderr,"checked query %d/%d qid=%d cpu_pairs=%d\n",i+1,nq,q,samples+1);
    }
    out.close(); check(cudaFree(dev_sums)); check(cudaFree(dev_data));
    return out ? 0 : 12;
}
