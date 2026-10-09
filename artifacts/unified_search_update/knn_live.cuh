#pragma once
// One same-stream mirror of the native live multiset; no second update owner.
#undef short
#include <sstream>
#include <algorithm>
#include <limits>
#include "knn_cutoff.cuh"
#include "knn_verify.cuh"
#include "knn_select.cuh"
namespace uk {
inline void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
struct Input {std::vector<float> data;std::vector<std::pair<int,int>> events;int queries=0;};
inline std::istringstream row(std::ifstream& f) {
    std::string s;require(bool(std::getline(f,s)),"truncated input");return std::istringstream(s);
}
inline void end(std::istringstream& s) {s>>std::ws;require(s.eof(),"extra or malformed input token");}
inline Input parse(const char* data_path,const char* event_path,int k,float radius) {
    require((k==8||k==32)&&(radius==0||radius==10000),"unsupported K/radius");
    Input x;std::ifstream f(data_path);require(bool(f),"cannot open data");
    int d=0,n=0,m=0;auto h=row(f);require(bool(h>>d>>n>>m),"data header");end(h);
    require(d==128&&n==1000&&m==2,"requires initial N1000 D128 metric2");
    for(int i=0;i<n;i++) {auto s=row(f);for(int j=0;j<d;j++) {
        double v;require(bool(s>>v)&&std::isfinite(v)&&v>=0&&v<=255&&v==std::floor(v),"integer coordinate domain");
        x.data.push_back(float(v));}end(s);}
    std::string extra;require(!std::getline(f,extra),"extra data row");
    std::ifstream e(event_path);require(bool(e),"cannot open events");int count=0;
    h=row(e);require(bool(h>>count),"event header");end(h);require(count>0&&count<=12000,"event count");
    std::vector<bool> alive(n,true);int buffer=0;
    for(int step=0;step<count;step++) {
        auto s=row(e);int flag=-1,index=-1;require(bool(s>>flag>>index),"event row");end(s);
        require(flag>=0&&flag<=3&&index>=0,"event flag/index");
        int live=int(std::count(alive.begin(),alive.end(),true));
        if(flag==1) {require(index<live+buffer,"delete live rank");
            if(index>=live)--buffer;else {int rank=0;for(size_t p=0;p<alive.size();p++)if(alive[p]&&rank++==index){alive[p]=false;break;}}}
        else {require(index<int(alive.size()),"physical query/reinsertion index");
            if(flag==0){++buffer;if(buffer==10){alive.assign(live+buffer,true);buffer=0;}}
            else ++x.queries;}
        live=int(std::count(alive.begin(),alive.end(),true));
        require(alive.size()+buffer<=1024&&live+buffer<=1010,"live/physical capacity");
        x.events.emplace_back(flag,index);
    }
    require(!std::getline(e,extra),"extra event row");require(x.queries>0&&x.queries<=10000,"query count");return x;
}
__global__ void publish(const float* data,float* packed,const int* deleted,const int* prefix,
    const int* insertion,int* order,uint8_t* mask,int n,int b,int d) {
    int p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=n+b)return;
    if(p<n){mask[p]=!deleted[p];order[p]=mask[p]?p-prefix[p]:0x7fffffff;}
    else {int j=p-n;mask[p]=1;order[p]=n-prefix[n-1]+j;
        for(int dim=0;dim<d;dim++)packed[size_t(p/32)*d*32+dim*32+(p&31)]=data[size_t(insertion[j])*d+dim];}
}
__global__ void normalize(int* ids,float* distances,int k) {
    int p=threadIdx.x;if(p<k&&(!isfinite(distances[p])||ids[p]==0x7fffffff)){ids[p]=-1;distances[p]=INFINITY;}
}
struct LiveKnn {
    static constexpr int capacity=1024,max_k=32;
    float *packed=nullptr,*distances=nullptr;double *scores=nullptr,*cutoff=nullptr;
    int *identity=nullptr,*order=nullptr,*ids=nullptr;uint8_t* mask=nullptr;
    Neighbor *a=nullptr,*b=nullptr;const float* base=nullptr;
    int n=0,d=128,k=0,refreshes=0,queries=0,allocations=0;bool bounded=true;
    size_t owned_bytes=0,peak_owned_bytes=0;std::vector<double> refresh_ms;
    template<class T> void allocate(T*& p,size_t count) {
        u10_ck(cudaMalloc((void**)&p,count*sizeof(T)));owned_bytes+=count*sizeof(T);
        ++allocations;peak_owned_bytes=std::max(owned_bytes,peak_owned_bytes);
    }
    void initialize(const float* data,int count,int dimensions,int topk) {
        const char* v=std::getenv("KNN_MODE");std::string mode=v?v:"BOUND";
        require(mode=="BOUND"||mode=="FULL","unknown kNN mode");bounded=mode=="BOUND";
        require(dimensions==128&&(topk==8||topk==32),"kNN shape");k=topk;d=dimensions;
        allocate(packed,size_t(capacity)*d);allocate(distances,max_k);allocate(scores,capacity);allocate(cutoff,1);
        allocate(identity,capacity);allocate(order,capacity);allocate(ids,max_k);allocate(mask,capacity);
        allocate(a,4*max_k);allocate(b,4*max_k);
        std::vector<int> host(capacity);for(int i=0;i<capacity;i++)host[i]=i;
        u10_ck(cudaMemcpy(identity,host.data(),capacity*sizeof(int),cudaMemcpyHostToDevice));refresh(data,count);
    }
    void refresh(const float* data,int count) {
        require(count>0&&count<=capacity,"rebuild physical capacity");auto start=U10Clock::now();
        base=data;n=count;pack32<<<(n+255)/256,256>>>(data,identity,packed,n,d);
        u10_ck(cudaDeviceSynchronize());++refreshes;refresh_ms.push_back(u10_ms(start));
    }
    Neighbor* select(int count) {
        int blocks=(count+255)/256;block_topk<<<blocks,256>>>(scores,order,nullptr,a,count,k,1,true);
        Neighbor* input=a;Neighbor* output=b;count=blocks*k;
        while(blocks>1){blocks=(count+255)/256;block_topk<<<blocks,256>>>(nullptr,nullptr,input,output,count,k,1,false);
            std::swap(input,output);count=blocks*k;}
        return input;
    }
    void search(const float* data,const int* deleted,int* prefix,const int* insertion,int count,int buffer,const int* qids) {
        require(data==base&&count==n&&buffer>=0&&buffer<10&&n+buffer<=capacity,"stale kNN epoch");
        thrust::inclusive_scan(thrust::device,deleted,deleted+n,prefix);
        int total=n+buffer;publish<<<(total+255)/256,256>>>(data,packed,deleted,prefix,insertion,order,mask,n,buffer,d);
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
            <<",\"final_owned_bytes\":"<<owned_bytes<<",\"refresh_ms\":[";
        for(size_t i=0;i<refresh_ms.size();i++)out<<(i?",":"")<<refresh_ms[i];out<<"]}\n";
        require(bool(out),"write unified receipt");
    }
};
LiveKnn live;
}
#define short float
