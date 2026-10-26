// Host-ready external-query harness; approved search patch plus output adapters.
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
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
#ifndef BUILD_ID
#define BUILD_ID "unrecorded"
#endif
#ifdef ARM_G
#include "source_g/include/tree.cuh"
#include "source_g/include/search_v2.cuh"
#else
#define RP_DEFINE_CONSTANTS
#include "source_p/include/residual_pruning.cuh"
#include "source_p/include/tree.cuh"
#include "source_p/include/search_v2.cuh"
#endif
#undef short
using Wall=std::chrono::steady_clock;
double ms(Wall::time_point t){return std::chrono::duration<double,std::milli>(Wall::now()-t).count();}
std::vector<float> read(const char* p,int rows,int &d){std::ifstream f(p,std::ios::binary);int n;f.read((char*)&n,4);f.read((char*)&d,4);assert(f&&d>0&&rows<=n);std::vector<float>x(size_t(rows)*d);f.read((char*)x.data(),x.size()*4);assert(f);return x;}
template<class T>void alloc(T*&p,size_t n){CHECK(cudaMalloc(&p,n*sizeof(T)));}
int configured_height(int n){int h=1;int64_t capacity=20;while(capacity<n){capacity*=10;++h;}return h;}
int main(int argc,char**argv){
 std::cout<<std::unitbuf;std::cerr<<std::unitbuf;
 assert(argc==9); // base query N Q reps warm outprefix ignored-legacy-cache
 int n=std::stoi(argv[3]),batch=std::stoi(argv[4]),reps=std::stoi(argv[5]),warm=std::stoi(argv[6]),d,dq;
 if(n<8||n>10000000||configured_height(n)>=8){std::cerr<<"infeasible: workspace chunking (tree_h=8); N must be <=10M\n";return 3;}
 assert(batch==1||batch==32||batch==1024);assert(reps>=0&&warm>=0);
 auto x=read(argv[1],n,d),q=read(argv[2],1000,dq);
 assert(d==dq&&int64_t(n+batch)*d<=INT32_MAX);
 std::string out=argv[7];std::ofstream(out+".pid")<<getpid();
 int *info,*ids,*nodes_n,*empty,*output;TN*nodes;float *data,*query;
 CHECK(cudaMallocManaged(&info,12));info[0]=d;info[1]=n;info[2]=2;
#ifdef ARM_G
 alloc(data,size_t(n+batch)*d);
 int *qids;alloc(qids,batch);
#else
 alloc(data,x.size());
#endif
 CHECK(cudaMemcpy(data,x.data(),x.size()*4,cudaMemcpyHostToDevice));
 alloc(query,size_t(batch)*d);alloc(output,size_t(batch)*8);
#ifndef ARM_G
 int mode=0;CHECK(cudaMemcpyToSymbol(c_rp_mode,&mode,sizeof(mode)));
#endif
 int h;double build=0;auto t=Wall::now();
 // Configure the original managed native height, never its default three levels.
 MAX_H=configured_height(n);
 indexConstru(data,nullptr,nullptr,info,ids,nodes,nodes_n,h,empty);CHECK(cudaDeviceSynchronize());build=ms(t);
 if(h>=8){std::cerr<<"infeasible: workspace chunking (tree_h=8)\n";return 3;}
 // Prove leaf capacity and complete ID coverage before the first search.
 std::vector<TN> hn(*nodes_n);std::vector<int> hi(n),he(*nodes_n);std::vector<unsigned char> seen(n,0);
 CHECK(cudaMemcpy(hn.data(),nodes,hn.size()*sizeof(TN),cudaMemcpyDeviceToHost));
 CHECK(cudaMemcpy(hi.data(),ids,size_t(n)*4,cudaMemcpyDeviceToHost));
 CHECK(cudaMemcpy(he.data(),empty,he.size()*4,cudaMemcpyDeviceToHost));
 int max_leaf=0,leaf_count=0;int64_t coverage=0;
 for(size_t i=0;i<hn.size();++i){if(he[i]!=0||!hn[i].is_leaf)continue;auto node=hn[i];
   assert(node.size>=0&&node.size<=20&&node.lid>=0&&int64_t(node.lid)+node.size<=n);
   max_leaf=std::max(max_leaf,node.size);++leaf_count;coverage+=node.size;
   for(int j=0;j<node.size;++j){int id=hi[node.lid+j];assert(id>=0&&id<n&&!seen[id]);seen[id]=1;}
 }
 assert(coverage==n&&std::all_of(seen.begin(),seen.end(),[](unsigned char v){return v==1;}));
 std::cout<<"BUILD_ID="<<BUILD_ID<<" N="<<n<<" D="<<d<<" configured_height="<<configured_height(n)<<" tree_h="<<h<<" nodes="<<*nodes_n<<" max_leaf="<<max_leaf<<" indexed_coverage="<<coverage<<" build_ms="<<build<<" timing_scope=host-ready batch_queries="<<batch<<"\n";
#ifdef ARM_G
 size_t available_bytes,total_bytes;CHECK(cudaMemGetInfo(&available_bytes,&total_bytes));
 if(available_bytes/2/sizeof(double)>INT32_MAX){
   std::cerr<<"infeasible: native G half-free workspace exceeds signed int32 slot count; no query launched\n";
   std::ofstream(out+".json")<<"{\"arm\":\"G\",\"state\":\"infeasible: native workspace int32\",\"query_launched\":false,\"available_gpu_bytes\":"<<available_bytes<<",\"tree_h\":"<<h<<",\"configured_height\":"<<configured_height(n)<<",\"nodes\":"<<*nodes_n<<",\"max_leaf_size\":"<<max_leaf<<",\"leaf_coverage\":"<<coverage<<"}\n";
   return 2;
 }
#endif
 auto call=[&](int start,int b){
   std::vector<float> hq(size_t(b)*d);for(int i=0;i<b;i++)std::copy_n(q.data()+size_t((start+i)%1000)*d,d,hq.data()+size_t(i)*d);
   std::vector<int> result(size_t(b)*8,-1);CHECK(cudaMemset(output,0xff,result.size()*4));
#ifdef ARM_G
   std::vector<int> hids(b);for(int i=0;i<b;++i)hids[i]=n+i;
   CHECK(cudaMemcpy(data+size_t(n)*d,hq.data(),hq.size()*4,cudaMemcpyHostToDevice));
   CHECK(cudaMemcpy(qids,hids.data(),size_t(b)*4,cudaMemcpyHostToDevice));
   audit_result_ids=output;
   searchIndexKnnV2(data,nodes,ids,nodes_n,qids,b,8,h,info,empty,nullptr,nullptr);
#else
   CHECK(cudaMemcpy(query,hq.data(),hq.size()*4,cudaMemcpyHostToDevice));
   searchIndexKnnV2(data,nodes,ids,nodes_n,query,output,b,8,h,info,empty,nullptr,nullptr);
#endif
   CHECK(cudaDeviceSynchronize());CHECK(cudaGetLastError());CHECK(cudaMemcpy(result.data(),output,result.size()*4,cudaMemcpyDeviceToHost));CHECK(cudaFree(res_dis));return result;
 };
 auto pass=[&](bool dump,std::ofstream &csv,int it){
   std::ofstream f;if(dump)f.open(out+".ids",std::ios::binary);
   for(int s=0;s<1000;s+=batch){int b=batch==1024?1024:std::min(batch,1000-s);auto begin=Wall::now();auto r=call(s,b);double dt=ms(begin);csv<<it<<','<<s<<','<<b<<','<<std::setprecision(12)<<dt<<'\n';csv.flush();if(dump)f.write((char*)r.data(),r.size()*4);}
 };
 std::ofstream times(out+".csv");times<<"iteration,start,batch,batch_ms\n";
 unsigned long long z[3]={};CHECK(cudaMemcpyToSymbol(counts,z,sizeof(z)));
 pass(true,times,-1);
 for(int i=0;i<warm;i++){auto unused=call(0,batch);}
 for(int i=0;i<reps;i++)pass(false,times,i);
 CHECK(cudaMemcpyFromSymbol(z,counts,sizeof(z)));
#ifdef ARM_G
 const char* arm="G";const char* workspace="native half available GPU memory";
#else
 const char* arm="P";const char* workspace="native capped 4GiB";
#endif
 std::ofstream(out+".json")<<std::setprecision(12)<<"{\"arm\":\""<<arm<<"\",\"build_id\":\""<<BUILD_ID<<"\",\"N\":"<<n<<",\"D\":"<<d<<",\"Q\":"<<batch<<",\"build_ms\":"<<build<<",\"cache_load_ms\":0,\"cache_disabled\":true,\"tree_h\":"<<h<<",\"configured_height\":"<<configured_height(n)<<",\"nodes\":"<<*nodes_n<<",\"leaf_count\":"<<leaf_count<<",\"max_leaf_size\":"<<max_leaf<<",\"leaf_coverage\":"<<coverage<<",\"workspace\":\""<<workspace<<"\",\"C2_mode\":0,\"instrumented\":"<<INSTRUMENT<<",\"distance_calls\":"<<z[0]<<",\"candidate_leaves\":"<<z[1]<<",\"leaf_distances\":"<<z[2]<<"}\n";
}
