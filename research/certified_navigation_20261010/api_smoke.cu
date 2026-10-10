// Isolate context/API setup from navigation: no data, tree search, or memo.
#include <cuda_runtime.h>
#include <iostream>
#include <vector>
#include <algorithm>
#include <curand_kernel.h>
#include <thrust/sort.h>
#include <thrust/reduce.h>
#include <thrust/scan.h>
#include <thrust/count.h>
#ifdef INCLUDE_ORIGINAL_GTS
#include "tree.cuh"
#include "search_v2.cuh"
#undef short
#endif
__global__ void api_smoke(int* p){if(threadIdx.x==0)p[0]=7;}
static bool ok(cudaError_t e){if(e!=cudaSuccess){std::cerr<<cudaGetErrorString(e)<<'\n';return false;}return true;}
int main(){
    if(!ok(cudaFree(nullptr)))return 1;std::cout<<"INIT_RETURNED_SUCCESS"<<std::endl;
    int* p;if(!ok(cudaMalloc((void**)&p,4)))return 1;
    api_smoke<<<1,1>>>(p);if(!ok(cudaDeviceSynchronize()))return 1;
    int h;if(!ok(cudaMemcpy(&h,p,4,cudaMemcpyDeviceToHost))||h!=7)return 1;
    if(!ok(cudaFree(p)))return 1;std::cout<<"PASS no tree query executed"<<std::endl;
}
