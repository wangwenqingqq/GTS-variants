// Host-ready external-query harness; archived kernels are included separately.
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <climits>
#include <stdexcept>
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
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
template<class T>void alloc(T*&p,size_t n){CHECK(cudaMalloc(&p,n*sizeof(T)));}
int main(int argc,char**argv){
 std::cout<<std::unitbuf;
 require(argc==9,"usage: edit_tree base query N Q reps warm outprefix unused_cache");
 int n=std::stoi(argv[3]),batch=std::stoi(argv[4]),reps=std::stoi(argv[5]),warm=std::stoi(argv[6]),d;
 require(n>=8&&n<=10000000&&batch>0&&batch<=1024&&reps>=0&&warm>=0,"invalid or unsafe Word workload");
 std::ofstream(std::string(argv[7])+".pid")<<getpid();
 struct Str{int n=0,m=0;std::vector<int>len;std::vector<char>text;Str(const char*p){
   std::ifstream f(p,std::ios::binary);f.read((char*)&n,4);f.read((char*)&m,4);
   require(bool(f)&&n>0&&m==M,"invalid Word header");f.seekg(0,std::ios::end);
   require(f.tellg()==std::streamoff(8+int64_t(n)*(m+4)),"invalid Word payload size");f.seekg(8);
   len.resize(n);text.resize(size_t(n)*m);f.read((char*)len.data(),size_t(n)*4);f.read(text.data(),text.size());
   require(bool(f),"truncated Word input");for(int v:len)require(v>=0&&v<M,"Word length exceeds DP array");
 }};
 Str x(argv[1]),q(argv[2]);require(n<=x.n&&q.n==1000&&int64_t(n+batch)*M<=INT32_MAX,"invalid Word query/index dimensions");d=M;
 std::string out=argv[7];
 int *info,*ids,*nodes_n,*empty,*output;TN*nodes;float *data;
 CHECK(cudaMallocManaged(&info,12));info[0]=d;info[1]=n;info[2]=6;
 data=nullptr;char* strings;int*lengths,*qids;alloc(strings,size_t(n+std::max(batch,1))*M);alloc(lengths,n+std::max(batch,1));alloc(qids,std::max(batch,1));CHECK(cudaMemcpy(strings,x.text.data(),size_t(n)*M,cudaMemcpyHostToDevice));CHECK(cudaMemcpy(lengths,x.len.data(),size_t(n)*4,cudaMemcpyHostToDevice));
 alloc(output,size_t(batch)*8);
 int mode=0;CHECK(cudaMemcpyToSymbol(c_rp_mode,&mode,sizeof(mode)));
 // Do not reuse the pre-incident unkeyed index caches.
 int h;double build=0,load=0;auto t=Wall::now();
 indexConstru(data,strings,lengths,info,ids,nodes,nodes_n,h,empty);
 CHECK(cudaDeviceSynchronize());CHECK(cudaGetLastError());build=ms(t);
 if(h>=8){std::cerr<<"infeasible: workspace chunking (tree_h="<<h<<")\n";return 3;}
 std::cout<<"Word tree_h="<<h<<" nodes="<<*nodes_n<<" N="<<n<<" queries=1000 C2=off\n";
 auto call=[&](int start,int b){
   std::vector<char> hq(size_t(b)*M);std::vector<int> hl(b),hi(b);for(int i=0;i<b;i++){int qi=(start+i)%1000;std::copy_n(q.text.data()+size_t(qi)*M,M,hq.data()+size_t(i)*M);hl[i]=q.len[qi];hi[i]=n+i;}
   std::vector<int> result(size_t(b)*8,-1);CHECK(cudaMemcpy(strings+size_t(n)*M,hq.data(),hq.size(),cudaMemcpyHostToDevice));CHECK(cudaMemcpy(lengths+n,hl.data(),size_t(b)*4,cudaMemcpyHostToDevice));CHECK(cudaMemcpy(qids,hi.data(),size_t(b)*4,cudaMemcpyHostToDevice));CHECK(cudaMemset(output,0xff,result.size()*4));
   searchIndexKnnV2(data,nodes,ids,nodes_n,qids,output,b,8,h,info,empty,strings,lengths);
   CHECK(cudaDeviceSynchronize());CHECK(cudaGetLastError());CHECK(cudaMemcpy(result.data(),output,result.size()*4,cudaMemcpyDeviceToHost));CHECK(cudaFree(res_dis));return result;
 };
 auto pass=[&](bool dump,std::ofstream &csv,int it){
   std::ofstream f;if(dump)f.open(out+".ids",std::ios::binary);
   for(int s=0;s<1000;s+=batch){int b=batch==1024?1024:std::min(batch,1000-s);auto t=Wall::now();auto r=call(s,b);double dt=ms(t);csv<<it<<','<<s<<','<<b<<','<<std::setprecision(12)<<dt<<'\n';if(dump)f.write((char*)r.data(),r.size()*4);}
 };
 std::ofstream times(out+".csv");times<<"iteration,start,batch,batch_ms\n";
 unsigned long long z[3]={};CHECK(cudaMemcpyToSymbol(counts,z,sizeof(z)));
 pass(true,times,-1);
 for(int i=0;i<warm;i++){auto unused=call(0,batch);}
 if(reps>0)CHECK(cudaMemcpyToSymbol(counts,z,sizeof(z)));
 for(int i=0;i<reps;i++)pass(false,times,i);
 CHECK(cudaMemcpyFromSymbol(z,counts,sizeof(z)));
 std::ofstream(out+".json")<<std::setprecision(12)<<"{\"N\":"<<n<<",\"D\":"<<d<<",\"Q\":"<<batch<<",\"build_ms\":"<<build<<",\"cache_load_ms\":"<<load<<",\"tree_h\":"<<h<<",\"cache_mode\":\"disabled\",\"C2_mode\":0,\"instrumented\":"<<INSTRUMENT<<",\"distance_calls\":"<<z[0]<<",\"candidate_leaves\":"<<z[1]<<",\"leaf_distances\":"<<z[2]<<"}\n";
}
