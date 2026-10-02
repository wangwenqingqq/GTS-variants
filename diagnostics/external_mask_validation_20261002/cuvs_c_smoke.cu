#include <cuda_runtime.h>
#include <cuvs/distance/pairwise_distance.h>
#include <cstdio>
#include <cstdlib>

static void check(cudaError_t e) {
    if (e != cudaSuccess) { std::fprintf(stderr, "CUDA: %s\n", cudaGetErrorString(e)); std::exit(2); }
}
static void check(cuvsError_t e) {
    if (e != CUVS_SUCCESS) { std::fprintf(stderr, "cuVS: %s\n", cuvsGetLastErrorText()); std::exit(3); }
}
static DLManagedTensor matrix(void* data, int64_t* shape, uint8_t bits) {
    DLManagedTensor t{};
    t.dl_tensor.data = data;
    t.dl_tensor.device = {kDLCUDA, 0};
    t.dl_tensor.ndim = 2;
    t.dl_tensor.dtype = {kDLFloat, bits, 1};
    t.dl_tensor.shape = shape;
    return t;
}
template<class T> static void run(cuvsResources_t res, cuvsDistanceType metric) {
    const T x[6] = {0,0,0, 1,2,3}, y[6] = {1,2,3, 2,2,3};
    T *dx, *dy, *dz;
    check(cudaMalloc(&dx, sizeof x)); check(cudaMalloc(&dy, sizeof y));
    check(cudaMalloc(&dz, 4*sizeof(T)));
    check(cudaMemcpy(dx,x,sizeof x,cudaMemcpyHostToDevice));
    check(cudaMemcpy(dy,y,sizeof y,cudaMemcpyHostToDevice));
    int64_t xy[2]={2,3}, zz[2]={2,2};
    auto a=matrix(dx,xy,8*sizeof(T)), b=matrix(dy,xy,8*sizeof(T)), c=matrix(dz,zz,8*sizeof(T));
    check(cuvsPairwiseDistance(res,&a,&b,&c,metric,0));
    T z[4]; check(cudaMemcpy(z,dz,sizeof z,cudaMemcpyDeviceToHost));
    std::printf("bits=%zu metric=%d values=%.9g,%.9g,%.9g,%.9g\n",8*sizeof(T),int(metric),double(z[0]),double(z[1]),double(z[2]),double(z[3]));
    if(z[0]!=T(14)||z[1]!=T(17)||z[2]!=T(0)||z[3]!=T(1))std::exit(4);
    check(cudaFree(dz)); check(cudaFree(dy)); check(cudaFree(dx));
}
int main() {
    cuvsResources_t res;
    check(cuvsResourcesCreate(&res));
    cudaStream_t stream; check(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
    check(cuvsStreamSet(res,stream));
    run<double>(res,L2Unexpanded); run<double>(res,L2Expanded);
    run<float>(res,L2Unexpanded); run<float>(res,L2Expanded);
    check(cuvsResourcesDestroy(res)); check(cudaStreamDestroy(stream));
}
