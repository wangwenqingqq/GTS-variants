// Direct CPU oracle for the four diagnostic kernels, including a partial tile.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <vector>
#include "rootcause_l2.cuh"

static void ck(cudaError_t e) {
    if (e != cudaSuccess) { std::fprintf(stderr, "%s\n", cudaGetErrorString(e)); std::exit(2); }
}

static uint32_t bits(float x) { uint32_t u; std::memcpy(&u, &x, 4); return u; }

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    std::ifstream file(argv[1], std::ios::binary);
    int h[3]; file.read(reinterpret_cast<char*>(h), sizeof h);
    const int d=h[0], base_n=h[1];
    if (!file || base_n != 4096 || h[2] != 2) return 3;
    std::vector<float> data(size_t(base_n)*d);
    file.read(reinterpret_cast<char*>(data.data()), data.size()*4);
    if (!file || file.peek() != EOF) return 4;
    float *dd, *dp, *out_d; int *di, *dq, *out_h, *out_i;
    ck(cudaMalloc(&dd, data.size()*4)); ck(cudaMemcpy(dd,data.data(),data.size()*4,cudaMemcpyHostToDevice));
    const float radii[]={-1.0f,0.0f,std::numeric_limits<float>::denorm_min(),
                         std::nextafter(1.0f,0.0f),1.0f,
                         std::nextafter(1.0f,2.0f),0x1p120f};
    long long checked=0;
    for (int n : {4096,4103}) {
        std::vector<int> order(n);
        for (int pos=0;pos<n;++pos) order[pos]=((pos%base_n)*13)%base_n;
        ck(cudaMalloc(&di,size_t(n)*4)); ck(cudaMemcpy(di,order.data(),size_t(n)*4,cudaMemcpyHostToDevice));
        ck(cudaMalloc(&dp,size_t((n+31)/32)*32*d*4)); ck(cudaMalloc(&dq,4));
        ck(cudaMalloc(&out_h,size_t(n)*4)); ck(cudaMalloc(&out_i,size_t(n)*4));
        ck(cudaMalloc(&out_d,size_t(n)*4));
        rootcausePack32<<<(n+511)/512,512>>>(di,dd,dp,n,d);
        ck(cudaGetLastError()); ck(cudaDeviceSynchronize());
        std::vector<int> hits(n),ids(n); std::vector<float> distances(n);
        for (int q : {0,2,4,5}) {
            ck(cudaMemcpy(dq,&q,4,cudaMemcpyHostToDevice));
            std::vector<double> sums(base_n);
            for (int id=0;id<base_n;++id) {
                double sum=0;
                for (int j=0;j<d;++j) {
                    const double delta=double(data[size_t(id)*d+j])-double(data[size_t(q)*d+j]);
                    sum=sum+delta*delta;
                }
                sums[id]=sum;
            }
            for (float radius : radii) for (int mode=0;mode<4;++mode) {
                if (mode==0) rootcauseFlat<false,false><<<(n+511)/512,512>>>(di,dd,dp,dq,n,d,radius,out_h,out_i,out_d,nullptr);
                if (mode==1) rootcauseFlat<true,false><<<(n+511)/512,512>>>(di,dd,dp,dq,n,d,radius,out_h,out_i,out_d,nullptr);
                if (mode==2) rootcauseFlat<false,true><<<(n+511)/512,512>>>(di,dd,dp,dq,n,d,radius,out_h,out_i,out_d,nullptr);
                if (mode==3) rootcauseFlat<true,true><<<(n+511)/512,512>>>(di,dd,dp,dq,n,d,radius,out_h,out_i,out_d,nullptr);
                ck(cudaGetLastError());
                ck(cudaMemcpy(hits.data(),out_h,size_t(n)*4,cudaMemcpyDeviceToHost));
                ck(cudaMemcpy(ids.data(),out_i,size_t(n)*4,cudaMemcpyDeviceToHost));
                ck(cudaMemcpy(distances.data(),out_d,size_t(n)*4,cudaMemcpyDeviceToHost));
                int actual=0, expected_count=0;
                for (int pos=0;pos<n;++pos) {
                    const int id=order[pos];
                    const bool expected=radius>=0 && sums[id]<=double(radius)*double(radius);
                    expected_count+=expected;
                    if (hits[pos]!=int(expected) || (expected && (ids[pos]!=id ||
                        bits(distances[pos])!=bits(float(std::sqrt(sums[id])))))) {
                        std::fprintf(stderr,"FAIL d=%d n=%d q=%d r=%a mode=%d pos=%d id=%d hit=%d expected=%d\n",
                                     d,n,q,radius,mode,pos,id,hits[pos],int(expected));
                        return 5;
                    }
                    actual+=hits[pos]; ++checked;
                }
                if (actual!=expected_count) return 6;
            }
        }
        ck(cudaFree(out_d));ck(cudaFree(out_i));ck(cudaFree(out_h));
        ck(cudaFree(dq));ck(cudaFree(dp));ck(cudaFree(di));
    }
    ck(cudaFree(dd));
    std::printf("PASS d=%d checked=%lld\n",d,checked);
}
