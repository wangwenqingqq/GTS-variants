// Independent exhaustive reference; no tree, memo, candidate, or online bounds.
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
static void check(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
__global__ void exhaustive(const float* data,double* scores,int n,int d,int query){
    int row=blockIdx.x*blockDim.x+threadIdx.x;if(row>=n)return;
    double sum=0.;
    for(int j=0;j<d;++j){double delta=__dsub_rn(double(data[size_t(row)*d+j]),double(data[size_t(query)*d+j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));}
    scores[row]=sum;
}
struct Key {double score;int id;};
static bool less(Key a,Key b){return a.score<b.score || (a.score==b.score&&a.id<b.id);}
int main(int argc,char** argv)try{
    require(argc==5,"oracle data qids K output.bin");int k=std::stoi(argv[3]);
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);require(bool(f),"input header");
    int d=h[0],n=h[1];require(n>0&&d>0&&d<=960&&h[2]==2&&k>0&&k<=n,"contract");
    std::vector<float> host(size_t(n)*d);f.read((char*)host.data(),host.size()*4);require(bool(f),"input data");
    for(float x:host)require(std::isfinite(x)&&x>=0.f&&x<=2.f,"finite [0,2] input");
    float* data;double* scores;check(cudaMalloc((void**)&data,host.size()*4));
    check(cudaMemcpy(data,host.data(),host.size()*4,cudaMemcpyHostToDevice));host.clear();host.shrink_to_fit();
    check(cudaMalloc((void**)&scores,n*8ULL));
    std::ifstream qfile(argv[2]);int q;qfile>>q;require(bool(qfile)&&q>0,"queries");
    std::vector<int> ids(q*k);std::vector<double> out(q*k),all(n);std::vector<Key> keys(n);
    for(int i=0;i<q;++i){int query;qfile>>query;require(bool(qfile)&&query>=0&&query<n,"query ID");
        exhaustive<<<(n+255)/256,256>>>(data,scores,n,d,query);check(cudaDeviceSynchronize());
        check(cudaMemcpy(all.data(),scores,n*8ULL,cudaMemcpyDeviceToHost));
        for(int row=0;row<n;++row)keys[row]={all[row],row};
        std::partial_sort(keys.begin(),keys.begin()+k,keys.end(),less);
        for(int j=0;j<k;++j){ids[i*k+j]=keys[j].id;out[i*k+j]=keys[j].score;}
    }
    int extra;require(!(qfile>>extra),"extra queries");
    std::ofstream o(argv[4],std::ios::binary);int oh[4]={n,d,q,k};o.write((char*)oh,16);
    o.write((char*)ids.data(),ids.size()*4);o.write((char*)out.data(),out.size()*8);require(bool(o),"output");
    check(cudaFree(data));check(cudaFree(scores));
    std::cout<<"ORACLE {\"metric_contract_id\":\"fp32_input_rn_fp64_ordered_squared_l2_id_v1\",\"Q\":"<<q<<",\"N\":"<<n<<",\"K\":"<<k<<",\"independent_exhaustive\":true}"<<std::endl;
}catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
