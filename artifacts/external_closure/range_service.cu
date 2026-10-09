// Complete B1 cuVS FP32 L2Unexpanded scan adapter. No tree or finite top-K.
#include <cuda_runtime.h>
#include <cub/cub.cuh>
#include <cuvs/distance/pairwise_distance.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
using Clock=std::chrono::steady_clock;
static double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
static void ck(cudaError_t s){if(s!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(s));}
static void cv(cuvsError_t s){if(s!=CUVS_SUCCESS)throw std::runtime_error(cuvsGetLastErrorText());}
template<class T> void alloc(T*& p,size_t n){if(n)ck(cudaMalloc(&p,n*sizeof(T)));}
template<class T> void drop(T*& p){if(p){ck(cudaFree(p));p=nullptr;}}
static DLManagedTensor tensor(void* p,int64_t* shape){DLManagedTensor t{};t.dl_tensor.data=p;t.dl_tensor.device={kDLCUDA,0};t.dl_tensor.ndim=2;t.dl_tensor.dtype={kDLFloat,32,1};t.dl_tensor.shape=shape;return t;}
__global__ void flags_kernel(const float* sq,int* ids,uint8_t* flags,int n,double cutoff,bool enabled){
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n){ids[i]=i;flags[i]=enabled&&double(sq[i])<=cutoff;}
}
__global__ void fields_kernel(const float* sq,const int* ids,const int* count,float* fields,double* raw,int n){
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n&&i<*count){float x=sq[ids[i]];raw[i]=double(x);fields[i]=sqrtf(fmaxf(0,x));}
}
struct Scan {
    int n,d,*identity=nullptr,*outids=nullptr,*count=nullptr;uint8_t* flags=nullptr;
    float *database=nullptr,*query=nullptr,*squared=nullptr,*fields=nullptr;double* raw=nullptr;
    void* scratch=nullptr;size_t bytes=0;cuvsResources_t resource{};cudaStream_t stream{};
    void build(const std::vector<float>& data,int rows,int dim){
        n=rows;d=dim;ck(cudaStreamCreate(&stream));cv(cuvsResourcesCreate(&resource));cv(cuvsStreamSet(resource,stream));
        alloc(database,data.size());alloc(query,d);alloc(squared,n);alloc(identity,n);alloc(outids,n);alloc(flags,n);alloc(fields,n);alloc(raw,n);alloc(count,1);
        if(n){ck(cudaMemcpyAsync(database,data.data(),data.size()*4,cudaMemcpyHostToDevice,stream));
            ck(cub::DeviceSelect::Flagged(nullptr,bytes,identity,flags,outids,count,n,stream));ck(cudaMalloc(&scratch,bytes));}
        ck(cudaStreamSynchronize(stream));
    }
    void range(const float* q,float radius,std::vector<int>& ids,std::vector<float>& dist,std::vector<double>& native){
        if(!std::isfinite(radius))throw std::runtime_error("nonfinite radius");ids.clear();dist.clear();native.clear();if(!n)return;
        ck(cudaMemcpyAsync(query,q,size_t(d)*4,cudaMemcpyHostToDevice,stream));
        int64_t qs[2]={1,d},ds[2]={n,d},os[2]={1,n};auto a=tensor(query,qs),b=tensor(database,ds),c=tensor(squared,os);
        cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));
        flags_kernel<<<(n+255)/256,256,0,stream>>>(squared,identity,flags,n,double(radius)*double(radius),radius>=0);
        ck(cub::DeviceSelect::Flagged(scratch,bytes,identity,flags,outids,count,n,stream));
        fields_kernel<<<(n+255)/256,256,0,stream>>>(squared,outids,count,fields,raw,n);ck(cudaGetLastError());
        int result;ck(cudaMemcpyAsync(&result,count,4,cudaMemcpyDeviceToHost,stream));ck(cudaStreamSynchronize(stream));
        if(result<0||result>n)throw std::runtime_error("capacity");ids.resize(result);dist.resize(result);native.resize(result);
        if(result){ck(cudaMemcpyAsync(ids.data(),outids,result*4,cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(dist.data(),fields,result*4,cudaMemcpyDeviceToHost,stream));ck(cudaMemcpyAsync(native.data(),raw,result*8,cudaMemcpyDeviceToHost,stream));}
        ck(cudaStreamSynchronize(stream));
    }
    void release(){drop(database);drop(query);drop(squared);drop(identity);drop(outids);drop(flags);drop(fields);drop(raw);drop(count);drop(scratch);cv(cuvsResourcesDestroy(resource));ck(cudaStreamDestroy(stream));ck(cudaDeviceSynchronize());}
};
int main(int argc,char** argv){try{
    if(argc!=4)throw std::runtime_error("usage: range_service data.f32bin requests.txt output_prefix");
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);
    if(!f||h[0]<1||h[0]>960||h[1]<0||h[1]>1000000||h[2]!=2)throw std::runtime_error("header");
    std::vector<float> host(size_t(h[0])*h[1]);f.read((char*)host.data(),host.size()*4);
    if(!f||f.peek()!=EOF)throw std::runtime_error("data length");for(float x:host)if(!std::isfinite(x))throw std::runtime_error("nonfinite");
    std::string out=argv[3];std::ifstream req(argv[2]);int count;req>>count;if(!req||count<1||count>80)throw std::runtime_error("request count");
    std::ofstream ids(out+".ids.i32",std::ios::binary),dist(out+".dist.f32",std::ios::binary),raw(out+".native_squared.f64",std::ios::binary),rows(out+".queries.csv"),meta(out+".native.json");
    if(!ids||!dist||!raw||!rows||!meta)throw std::runtime_error("output open");
    rows<<"task,query,qid,count,offset,ack_ms\n"<<std::setprecision(14);
    Scan s;auto start=Clock::now();s.build(host,h[1],h[0]);double build=ms(start);size_t at=0;std::vector<float> zero(h[0],0);
    for(int i=0;i<count;++i){int task,row,k;float r;req>>task>>row>>r>>k;if(!req||task!=1||row<0||(h[1]&&row>=h[1]))throw std::runtime_error("request");
        std::vector<int> oi;std::vector<float> od;std::vector<double> os;start=Clock::now();
        s.range(h[1]?host.data()+size_t(row)*h[0]:zero.data(),r,oi,od,os);double ack=ms(start);
        ids.write((char*)oi.data(),oi.size()*4);dist.write((char*)od.data(),od.size()*4);raw.write((char*)os.data(),os.size()*8);
        rows<<"range,"<<i<<','<<row<<','<<oi.size()<<','<<at<<','<<ack<<'\n';at+=oi.size();
    }
    start=Clock::now();s.release();double release=ms(start);
    meta<<std::setprecision(14)<<"{\"build_ms\":"<<build<<",\"release_ms\":"<<release<<",\"queries\":"<<count<<",\"scratch_bytes\":"<<s.bytes<<",\"backend\":\"cuVS FP32 L2Unexpanded + complete inclusive CUB compact + D2H\"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
