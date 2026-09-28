// Directly test the strict reference and screened backend on edge-case inputs.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <vector>

#define TREE_ORDER 10
#define MAX_SIZE 20
struct TN { int pid; float min_dis; int size; int lid; int is_leaf; };
#include "strict_l2.cuh"

static void ck(cudaError_t e) {
    if(e!=cudaSuccess){fprintf(stderr,"CUDA: %s\n",cudaGetErrorString(e));exit(2);}
}

template<bool Fast>
__global__ void evaluate(const float* data,int n,int d,int q,float radius,int* hits,float* distances) {
    const int id=blockIdx.x*blockDim.x+threadIdx.x;
    if(id>=n)return;
    float distance=0;
    const bool hit=strict_hit<Fast>(data,d,id,q,radius,distance);
    hits[id]=int(hit);
    if(hit)distances[id]=distance;
}

static double cpu_sum(const float* a,const float* b,int d) {
    double sum=0;
    for(int j=0;j<d;++j){const double delta=double(a[j])-double(b[j]);
                           const double square=delta*delta;sum=sum+square;}
    return sum;
}

int main(int argc,char** argv) {
    if(argc!=2){fprintf(stderr,"usage: boundary_validate data.f32bin\n");return 1;}
    std::ifstream file(argv[1],std::ios::binary);int h[3];file.read(reinterpret_cast<char*>(h),sizeof(h));
    const int d=h[0],n=h[1];if(!file||n!=4096||h[2]!=2)return 3;
    std::vector<float> data(size_t(n)*d);
    file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    if(!file||file.peek()!=EOF)return 4;
    float* dev_data;int* dev_hits;float* dev_dist;
    ck(cudaMalloc(&dev_data,data.size()*sizeof(float)));
    ck(cudaMalloc(&dev_hits,size_t(n)*sizeof(int)));
    ck(cudaMalloc(&dev_dist,size_t(n)*sizeof(float)));
    ck(cudaMemcpy(dev_data,data.data(),data.size()*sizeof(float),cudaMemcpyHostToDevice));
    std::vector<int> hits(n);std::vector<float> distances(n);
    const float radii[]={-1.0f,0.0f,std::numeric_limits<float>::denorm_min(),
                         std::nextafter(1.0f,0.0f),1.0f,
                         std::nextafter(1.0f,2.0f),0x1p120f};
    int cases=0;long long pairs=0;
    for(int q:{0,2,4,5}){
        std::vector<double> sums(n);
        for(int id=0;id<n;++id)sums[id]=cpu_sum(data.data()+size_t(id)*d,data.data()+size_t(q)*d,d);
        for(float radius:radii){
            const double cutoff=double(radius)*double(radius);
            for(int backend=0;backend<2;++backend){
                if(backend)evaluate<true><<<(n+255)/256,256>>>(dev_data,n,d,q,radius,dev_hits,dev_dist);
                else evaluate<false><<<(n+255)/256,256>>>(dev_data,n,d,q,radius,dev_hits,dev_dist);
                ck(cudaGetLastError());
                ck(cudaMemcpy(hits.data(),dev_hits,size_t(n)*sizeof(int),cudaMemcpyDeviceToHost));
                ck(cudaMemcpy(distances.data(),dev_dist,size_t(n)*sizeof(float),cudaMemcpyDeviceToHost));
                int count=0;
                for(int id=0;id<n;++id){
                    const bool expected=radius>=0&&sums[id]<=cutoff;
                    if(hits[id]!=int(expected)){fprintf(stderr,"MEMBERSHIP d=%d q=%d id=%d radius=%g backend=%d\n",d,q,id,radius,backend);return 5;}
                    if(expected){
                        ++count;
                        const double reference=std::sqrt(sums[id]);
                        if(std::abs(double(distances[id])-reference)>1e-7+1e-5*reference){
                            fprintf(stderr,"DISTANCE d=%d q=%d id=%d radius=%g backend=%d\n",d,q,id,radius,backend);return 6;}
                    }
                }
                if(radius<0&&count!=0)return 7;
                if(radius==0&&q==0&&(!hits[0]||!hits[1]))return 8;
                if(radius==0x1p120f&&count!=n)return 9;
                ++cases;pairs+=n;
            }
        }
    }
    ck(cudaFree(dev_dist));ck(cudaFree(dev_hits));ck(cudaFree(dev_data));
    printf("PASS d=%d cases=%d checked_pairs=%lld\n",d,cases,pairs);
}
