#pragma once
// One same-stream mirror of the native live multiset; no second update owner.
#undef short
#include <sstream>
#include <algorithm>
#include <limits>
#include "input.hpp"
#include "knn_cutoff.cuh"
#include "knn_verify.cuh"
#include "knn_select.cuh"
namespace uk {
__global__ void publish(const float* data,float* packed,const int* deleted,const int* prefix,
    const int* insertion,int* order,uint8_t* mask,int n,int b,int d) {
    int p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=n+b)return;
    if(p<n){mask[p]=!deleted[p];order[p]=mask[p]?p-prefix[p]:0x7fffffff;}
    else {int j=p-n;mask[p]=1;order[p]=n-(n?prefix[n-1]:0)+j;
        for(int dim=0;dim<d;dim++)packed[size_t(p/32)*d*32+dim*32+(p&31)]=data[size_t(insertion[j])*d+dim];}
}
__global__ void normalize(int* ids,float* distances,int k) {
    int p=threadIdx.x;if(p<k&&(ids[p]==0x7fffffff)){ids[p]=-1;distances[p]=INFINITY;}
}
struct LiveKnn {
    int capacity=0,max_k=0;size_t neighbor_items=0;
    float *packed=nullptr,*distances=nullptr;double *scores=nullptr,*cutoff=nullptr;
    int *identity=nullptr,*order=nullptr,*ids=nullptr;uint8_t* mask=nullptr;
    Neighbor *a=nullptr,*b=nullptr;const float* base=nullptr;
    int n=0,d=128,k=0,refreshes=0,queries=0,allocations=0;uint64_t published_epoch=0;bool bounded=true;
    size_t owned_bytes=0,peak_owned_bytes=0;std::vector<double> refresh_ms;
    template<class T> void allocate(T*& p,size_t count) {
        u10_ck(cudaMalloc((void**)&p,checked_product(count,sizeof(T))));owned_bytes+=checked_product(count,sizeof(T));
        ++allocations;peak_owned_bytes=std::max(owned_bytes,peak_owned_bytes);
    }
    void initialize(const float* data,int count,int dimensions,int topk,int maximum) {
        const char* v=std::getenv("KNN_MODE");std::string mode=v?v:"BOUND";
        require(mode=="BOUND"||mode=="FULL","unknown kNN mode");bounded=mode=="BOUND";
        require((dimensions==128||dimensions==960)&&(topk==8||topk==32),"kNN shape");k=max_k=topk;d=dimensions;
        require(maximum>0&&maximum%32==0,"packed capacity");capacity=maximum;
        neighbor_items=checked_product(size_t((capacity+255)/256),size_t(max_k));
        allocate(packed,size_t(capacity)*d);allocate(distances,max_k);allocate(scores,capacity);allocate(cutoff,1);
        allocate(identity,capacity);allocate(order,capacity);allocate(ids,max_k);allocate(mask,capacity);
        allocate(a,neighbor_items);allocate(b,neighbor_items);
        std::vector<int> host(capacity);for(int i=0;i<capacity;i++)host[i]=i;
        u10_ck(cudaMemcpy(identity,host.data(),capacity*sizeof(int),cudaMemcpyHostToDevice));refresh(data,count);
    }
    void refresh(const float* data,int count) {
        require(count>=0&&count<=capacity,"rebuild physical capacity");auto start=U10Clock::now();
        base=data;n=count;if(n)pack32<<<(n+255)/256,256>>>(data,identity,packed,n,d);
        u10_ck(cudaDeviceSynchronize());published_epoch=target::bounds.epoch;++refreshes;refresh_ms.push_back(u10_ms(start));
    }
    Neighbor* select(int count) {
        require(count>0&&count<=capacity,"Top-K capacity");
        int blocks=(count+255)/256;require(size_t(blocks)*k<=neighbor_items,"Top-K scratch");block_topk<<<blocks,256>>>(scores,order,nullptr,a,count,k,1,true);
        Neighbor* input=a;Neighbor* output=b;count=blocks*k;
        while(blocks>1){blocks=(count+255)/256;block_topk<<<blocks,256>>>(nullptr,nullptr,input,output,count,k,1,false);
            std::swap(input,output);count=blocks*k;}
        return input;
    }
    void search(const float* data,const int* deleted,int* prefix,const int* insertion,int count,int buffer,const int* qids) {
        target::require_epoch(data,target::bounds.nodes,count,d);
        require(published_epoch==target::bounds.epoch,"stale kNN published epoch");
        require(data==base&&count==n&&buffer>=0&&buffer<10&&n+buffer<=capacity,"stale kNN epoch");
        thrust::inclusive_scan(thrust::device,deleted,deleted+n,prefix);
        int total=n+buffer;if(!total){
            u10_ck(cudaMemset(ids,0xff,k*sizeof(int)));
            std::vector<float> missing(k,INFINITY);u10_ck(cudaMemcpy(distances,missing.data(),k*sizeof(float),cudaMemcpyHostToDevice));
            ++queries;return;}
        publish<<<(total+255)/256,256>>>(data,packed,deleted,prefix,insertion,order,mask,n,buffer,d);
        if(bounded){int seeds=std::min(256,total);
            verify_distances<1,false,true><<<(seeds+255)/256,256,d*sizeof(float)>>>(data,packed,qids,cutoff,mask,scores,seeds,d,1);
            select_cutoff<<<1,1>>>(select(seeds),cutoff,k,1);
            verify_distances<1,true,true><<<(total+255)/256,256,d*sizeof(float)>>>(data,packed,qids,cutoff,mask,scores,total,d,1);
        }else verify_distances<1,false,true><<<(total+255)/256,256,d*sizeof(float)>>>(data,packed,qids,cutoff,mask,scores,total,d,1);
        final_output<<<1,32>>>(select(total),ids,distances,1,k);normalize<<<1,32>>>(ids,distances,k);
        u10_ck(cudaGetLastError());++queries;
    }
    void finish() {
        for(void* p:{(void*)packed,(void*)distances,(void*)scores,(void*)cutoff,(void*)identity,
                    (void*)order,(void*)ids,(void*)mask,(void*)a,(void*)b})if(p)u10_ck(cudaFree(p));
        packed=distances=nullptr;scores=cutoff=nullptr;identity=order=ids=nullptr;mask=nullptr;a=b=nullptr;base=nullptr;owned_bytes=0;
    }
    void write(const std::string& path) {
        std::ofstream out(path+".unified.json");out<<std::setprecision(17)
            <<"{\"knn_mode\":\""<<(bounded?"BOUND":"FULL")<<"\",\"k\":"<<k<<",\"queries\":"<<queries
            <<",\"refreshes\":"<<refreshes<<",\"allocations\":"<<allocations<<",\"peak_owned_bytes\":"<<peak_owned_bytes
            <<",\"capacity\":"<<capacity<<",\"neighbor_items_per_buffer\":"<<neighbor_items
            <<",\"final_owned_bytes\":"<<owned_bytes<<",\"refresh_ms\":[";
        for(size_t i=0;i<refresh_ms.size();i++)out<<(i?",":"")<<refresh_ms[i];out<<"]}\n";
        require(bool(out),"write unified receipt");
    }
};
LiveKnn live;
}
#define short float
