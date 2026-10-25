// Host-ready external-query harness; archived kernels are included separately.
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>
#include <unistd.h>
#include <cuda_runtime.h>
__device__ unsigned long long counts[3];
#ifndef INSTRUMENT
#define INSTRUMENT 0
#endif
#if INSTRUMENT
#define WORK(i,n) atomicAdd(counts+i,(unsigned long long)(n))
#else
#define WORK(i,n) ((void)0)
#endif
#define RP_DEFINE_CONSTANTS
#include "source_p/include/residual_pruning.cuh"
#include "source_p/include/tree.cuh"
#include "source_p/include/search_v2.cuh"
#undef short
using Wall=std::chrono::steady_clock;
double ms(Wall::time_point t){return std::chrono::duration<double,std::milli>(Wall::now()-t).count();}
std::vector<float> read(const char* p,int rows,int &d){std::ifstream f(p,std::ios::binary);int n;f.read((char*)&n,4);f.read((char*)&d,4);assert(f&&rows<=n);std::vector<float>x(size_t(rows)*d);f.read((char*)x.data(),x.size()*4);assert(f);return x;}
template<class T>void alloc(T*&p,size_t n){CHECK(cudaMalloc(&p,n*sizeof(T)));}
int main(int argc,char**argv){
 assert(argc==9); // base query N Q reps warm outprefix cache
 int n=std::stoi(argv[3]),batch=std::stoi(argv[4]),reps=std::stoi(argv[5]),warm=std::stoi(argv[6]),d,dq;
 auto x=read(argv[1],n,d),q=read(argv[2],1000,dq);assert(d==dq&&int64_t(n)*d<=INT32_MAX);
 std::string out=argv[7],cache=argv[8];std::ofstream(out+".pid")<<getpid();
 int *info,*ids,*nodes_n,*empty,*output;TN*nodes;float *data,*query;
 CHECK(cudaMallocManaged(&info,12));info[0]=d;info[1]=n;info[2]=2;
 alloc(data,x.size());CHECK(cudaMemcpy(data,x.data(),x.size()*4,cudaMemcpyHostToDevice));
 alloc(query,size_t(std::max(batch,1))*d);alloc(output,size_t(std::max(batch,1))*8);
 int mode=0;CHECK(cudaMemcpyToSymbol(c_rp_mode,&mode,sizeof(mode)));
 int h;double build=0,load=0;auto t=Wall::now();
 std::ifstream in(cache,std::ios::binary);
 if(in){
   int nn;in.read((char*)&h,4);in.read((char*)&nn,4);CHECK(cudaMallocManaged(&nodes_n,4));*nodes_n=nn;
   std::vector<TN> hn(nn);std::vector<int> hi(n),he(nn);in.read((char*)hn.data(),size_t(nn)*sizeof(TN));in.read((char*)hi.data(),size_t(n)*4);in.read((char*)he.data(),size_t(nn)*4);assert(in);
   alloc(nodes,nn);alloc(ids,n);alloc(empty,nn);CHECK(cudaMemcpy(nodes,hn.data(),hn.size()*sizeof(TN),cudaMemcpyHostToDevice));CHECK(cudaMemcpy(ids,hi.data(),size_t(n)*4,cudaMemcpyHostToDevice));CHECK(cudaMemcpy(empty,he.data(),size_t(nn)*4,cudaMemcpyHostToDevice));load=ms(t);
 }else{
   indexConstru(data,nullptr,nullptr,info,ids,nodes,nodes_n,h,empty);CHECK(cudaDeviceSynchronize());build=ms(t);
   std::vector<TN> hn(*nodes_n);std::vector<int> hi(n),he(*nodes_n);CHECK(cudaMemcpy(hn.data(),nodes,hn.size()*sizeof(TN),cudaMemcpyDeviceToHost));CHECK(cudaMemcpy(hi.data(),ids,size_t(n)*4,cudaMemcpyDeviceToHost));CHECK(cudaMemcpy(he.data(),empty,he.size()*4,cudaMemcpyDeviceToHost));
   std::ofstream c(cache,std::ios::binary);c.write((char*)&h,4);c.write((char*)nodes_n,4);c.write((char*)hn.data(),hn.size()*sizeof(TN));c.write((char*)hi.data(),hi.size()*4);c.write((char*)he.data(),he.size()*4);assert(c);
 }
 auto call=[&](int start,int b){
   std::vector<float> hq(size_t(b)*d);for(int i=0;i<b;i++)std::copy_n(q.data()+size_t((start+i)%1000)*d,d,hq.data()+size_t(i)*d);
   std::vector<int> result(size_t(b)*8,-1);CHECK(cudaMemcpy(query,hq.data(),hq.size()*4,cudaMemcpyHostToDevice));CHECK(cudaMemset(output,0xff,result.size()*4));
   searchIndexKnnV2(data,nodes,ids,nodes_n,query,output,b,8,h,info,empty,nullptr,nullptr);
   CHECK(cudaDeviceSynchronize());CHECK(cudaGetLastError());CHECK(cudaMemcpy(result.data(),output,result.size()*4,cudaMemcpyDeviceToHost));CHECK(cudaFree(res_dis));return result;
 };
 auto pass=[&](bool dump,std::ofstream &csv,int it){
   std::ofstream f;if(dump)f.open(out+".ids",std::ios::binary);
   for(int s=0;s<1000;s+=batch){int b=batch==1024?1024:std::min(batch,1000-s);auto t=Wall::now();auto r=call(s,b);double dt=ms(t);csv<<it<<','<<s<<','<<b<<','<<std::setprecision(12)<<dt<<'\n';if(dump)f.write((char*)r.data(),r.size()*4);}
 };
 std::ofstream times(out+".csv");times<<"iteration,start,batch,batch_ms\n";
 for(int i=0;i<warm;i++){auto unused=call(0,batch);}
 unsigned long long z[3]={};CHECK(cudaMemcpyToSymbol(counts,z,sizeof(z)));
 pass(true,times,-1);
 for(int i=0;i<reps;i++)pass(false,times,i);
 CHECK(cudaMemcpyFromSymbol(z,counts,sizeof(z)));
 std::ofstream(out+".json")<<std::setprecision(12)<<"{\"N\":"<<n<<",\"D\":"<<d<<",\"Q\":"<<batch<<",\"build_ms\":"<<build<<",\"cache_load_ms\":"<<load<<",\"C2_mode\":0,\"instrumented\":"<<INSTRUMENT<<",\"distance_calls\":"<<z[0]<<",\"candidate_leaves\":"<<z[1]<<",\"leaf_distances\":"<<z[2]<<"}\n";
}
