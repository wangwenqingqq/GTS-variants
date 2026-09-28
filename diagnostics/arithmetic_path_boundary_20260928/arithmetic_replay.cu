// Fixed (query, object) pairs, identical thread mapping and output delivery.
#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <string>
#include <vector>

static void ck(cudaError_t e) {
    if(e!=cudaSuccess){fprintf(stderr,"CUDA: %s\n",cudaGetErrorString(e));exit(2);}
}

__global__ void old_pow(const float* data,const int* ids,const int* query,int m,int d,float* out) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=m)return;
    const int id=ids[pos],q=query[0];
    float sum=0;
    for(int j=0;j<d;++j)
        sum+=pow(data[size_t(id)*d+j]-data[size_t(q)*d+j],2);
    out[pos]=pow(sum,0.5);
}

__global__ void direct(const float* data,const int* ids,const int* query,int m,int d,float* out) {
    const int pos=blockIdx.x*blockDim.x+threadIdx.x;
    if(pos>=m)return;
    const int id=ids[pos],q=query[0];
    float sum=0;
    for(int j=0;j<d;++j) {
        const float delta=__fsub_rn(data[size_t(id)*d+j],data[size_t(q)*d+j]);
        sum=__fadd_rn(sum,__fmul_rn(delta,delta));
    }
    out[pos]=sqrtf(sum);
}

struct Graph {
    cudaGraph_t graph=nullptr;
    cudaGraphExec_t exec=nullptr;
};

int main(int argc,char** argv) {
    if(argc!=6) {
        fprintf(stderr,"usage: arithmetic_replay data.f32bin queries.qid pair_ids.i32 radius output.csv\n");
        return 1;
    }
    std::ifstream in(argv[1],std::ios::binary);
    int32_t header[3];in.read(reinterpret_cast<char*>(header),sizeof(header));
    const int d=header[0],n=header[1];
    if(!in||d<1||d>960||n<1||n>1000000||header[2]!=2)return 3;
    std::vector<float> data(size_t(n)*d);
    in.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    if(!in||in.peek()!=EOF)return 4;
    std::ifstream qi(argv[2]);int nq;qi>>nq;
    if(!qi||nq<1||nq>100)return 5;
    std::vector<int> queries(nq);
    for(int& q:queries){qi>>q;if(!qi||q<0||q>=n)return 6;}
    std::ifstream pi(argv[3],std::ios::binary|std::ios::ate);
    const auto bytes=pi.tellg();
    if(!pi||bytes<=0||bytes%4!=0)return 7;
    const int m=int(bytes/4);if(m>1000000)return 8;
    std::vector<int> ids(m);pi.seekg(0);pi.read(reinterpret_cast<char*>(ids.data()),bytes);
    if(!pi)return 9;
    for(int id:ids)if(id<0||id>=n)return 10;
    const float radius=std::stof(argv[4]);
    float *dev_data,*dev_out,*host_out;int *dev_ids,*dev_query,*host_query;
    ck(cudaMalloc(&dev_data,data.size()*sizeof(float)));ck(cudaMalloc(&dev_out,size_t(m)*sizeof(float)));
    ck(cudaMalloc(&dev_ids,size_t(m)*sizeof(int)));ck(cudaMalloc(&dev_query,sizeof(int)));
    ck(cudaMallocHost(&host_out,size_t(m)*sizeof(float)));ck(cudaMallocHost(&host_query,sizeof(int)));
    ck(cudaMemcpy(dev_data,data.data(),data.size()*sizeof(float),cudaMemcpyHostToDevice));
    ck(cudaMemcpy(dev_ids,ids.data(),size_t(m)*sizeof(int),cudaMemcpyHostToDevice));
    cudaStream_t stream;ck(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
    Graph graphs[2];
    for(int mode=0;mode<2;++mode){
        ck(cudaStreamBeginCapture(stream,cudaStreamCaptureModeGlobal));
        ck(cudaMemcpyAsync(dev_query,host_query,sizeof(int),cudaMemcpyHostToDevice,stream));
        if(mode==0)old_pow<<<(m+511)/512,512,0,stream>>>(dev_data,dev_ids,dev_query,m,d,dev_out);
        else direct<<<(m+511)/512,512,0,stream>>>(dev_data,dev_ids,dev_query,m,d,dev_out);
        ck(cudaMemcpyAsync(host_out,dev_out,size_t(m)*sizeof(float),cudaMemcpyDeviceToHost,stream));
        ck(cudaStreamEndCapture(stream,&graphs[mode].graph));
        ck(cudaGraphInstantiate(&graphs[mode].exec,graphs[mode].graph,0));
    }
    auto run=[&](int mode,int q){
        *host_query=q;
        auto start=std::chrono::steady_clock::now();
        ck(cudaGraphLaunch(graphs[mode].exec,stream));ck(cudaStreamSynchronize(stream));
        return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count();
    };
    for(int mode=0;mode<2;++mode)for(int i=0;i<8;++i)run(mode,queries[i%nq]);
    std::ofstream out(argv[5]);out<<"round,mode,qid,host_ready_us,output_hash\n"<<std::setprecision(12);
    for(int round=0;round<6;++round)for(int i=0;i<2;++i){
        const int mode=(round+i)&1;
        for(int q:queries){
            const double us=run(mode,q);
            uint64_t hash=1469598103934665603ull;
            for(int j=0;j<m;++j){uint32_t bits;memcpy(&bits,host_out+j,4);hash=(hash^bits)*1099511628211ull;}
            out<<round+1<<','<<(mode?"direct":"old_pow")<<','<<q<<','<<us<<','<<hash<<'\n';
        }
    }
    const int audit_q=queries[0];
    run(0,audit_q);std::vector<float> old_values(host_out,host_out+m);
    run(1,audit_q);std::vector<float> direct_values(host_out,host_out+m);
    int old_wrong=0,direct_wrong=0;double old_max_error=0,direct_max_error=0;
    const double cutoff=double(radius)*double(radius);
    for(int i=0;i<m;++i){
        double sum=0;
        for(int j=0;j<d;++j){
            const double delta=double(data[size_t(ids[i])*d+j])-double(data[size_t(audit_q)*d+j]);
            const double square=delta*delta;sum=sum+square;
        }
        const bool hit=radius>=0&&sum<=cutoff;
        old_wrong+=int((radius>=0&&old_values[i]<=radius)!=hit);
        direct_wrong+=int((radius>=0&&direct_values[i]<=radius)!=hit);
        old_max_error=std::max(old_max_error,std::abs(double(old_values[i])-std::sqrt(sum)));
        direct_max_error=std::max(direct_max_error,std::abs(double(direct_values[i])-std::sqrt(sum)));
    }
    std::ofstream audit(std::string(argv[5])+".audit.json");
    audit<<std::setprecision(17)<<"{\"audit_qid\":"<<audit_q
         <<",\"pairs\":"<<m<<",\"old_membership_errors\":"<<old_wrong
         <<",\"direct_membership_errors\":"<<direct_wrong
         <<",\"old_max_distance_error\":"<<old_max_error
         <<",\"direct_max_distance_error\":"<<direct_max_error<<"}\n";
    if(!audit||!out)return 11;
    for(auto& g:graphs){ck(cudaGraphExecDestroy(g.exec));ck(cudaGraphDestroy(g.graph));}
    ck(cudaStreamDestroy(stream));ck(cudaFreeHost(host_query));ck(cudaFreeHost(host_out));
    ck(cudaFree(dev_query));ck(cudaFree(dev_ids));ck(cudaFree(dev_out));ck(cudaFree(dev_data));
    printf("PASS replay d=%d n=%d pairs=%d queries=%d\n",d,n,m,nq);
}
