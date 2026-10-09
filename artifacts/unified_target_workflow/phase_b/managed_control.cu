#include <cuda_runtime.h>
#include <cstdio>
__managed__ int scalar=10;
__global__ void touch(){scalar+=1;}
int main(){if(cudaFree(nullptr)!=cudaSuccess)return 1;touch<<<1,1>>>();if(cudaDeviceSynchronize()!=cudaSuccess)return 2;
if(scalar!=11)return 3;return cudaDeviceReset()==cudaSuccess?0:4;}
