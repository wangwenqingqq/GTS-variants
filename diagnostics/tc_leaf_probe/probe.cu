// Resident replay of real GTS leaf candidates; no production dispatch changes.
#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <mma.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#define CK(call) do { auto e=(call); if(e!=cudaSuccess) { std::fprintf(stderr,"CUDA %s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); std::exit(90); } } while(0)
static void require(bool ok,const char* msg) { if(!ok) throw std::runtime_error(msg); }
struct Leaf { int start,size; };
struct Pair { int q,l; };
struct Chunk { int l,j; };
__device__ int sumwarp(int x) { for(int d=16;d;d/=2)x+=__shfl_down_sync(0xffffffff,x,d);return x; }

__global__ void simt(const float* x,const int* qids,const int* ids,const Leaf* leaves,
                     const Pair* pairs,int r2,int n,int* counts,int* distances) {
    Pair p=pairs[blockIdx.x];Leaf l=leaves[p.l];
    int lane=threadIdx.x%32,warp=threadIdx.x/32,hits=0;
    for(int j=warp;j<l.size;j+=4) {
        int id=ids[l.start+j];float acc=0;
        #pragma unroll
        for(int k=lane;k<128;k+=32) {float v=x[id*128+k]-x[qids[p.q]*128+k];acc+=v*v;}
        for(int d=16;d;d/=2) acc+=__shfl_down_sync(0xffffffff,acc,d);
        if(!lane) { hits+=acc<=r2; if(distances)distances[p.q*n+id]=int(acc); }
    }
    __shared__ int sums[4];if(!lane)sums[warp]=hits;__syncthreads();
    if(threadIdx.x==0)atomicAdd(counts+p.q,sums[0]+sums[1]+sums[2]+sums[3]);
}
__global__ void make_masks(const Pair* pairs,int np,unsigned* masks,int groups) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<np) {Pair p=pairs[i];atomicOr(masks+p.l*groups+p.q/16,1u<<(p.q%16));}
}
__global__ void tensor(const float* x,const float* norms,const int* qids,const int* ids,
                       const Leaf* leaves,const Chunk* chunks,const unsigned* masks,
                       int groups,int r2,int n,int* counts,int* distances) {
    int lane=threadIdx.x,g=blockIdx.y;Chunk ch=chunks[blockIdx.x];Leaf l=leaves[ch.l];
    unsigned mask=masks[ch.l*groups+g];if(!mask)return; // Warp-uniform tail.
    __shared__ __align__(32) half a[16*128],b[16*128];
    __shared__ __align__(32) float c[256];
    for(int i=lane;i<16*128;i+=32) {
        int row=i/128,k=i%128,j=ch.j+row;
        a[i]=__float2half_rn(x[qids[g*16+row]*128+k]);
        b[i]=j<l.size?__float2half_rn(x[ids[l.start+j]*128+k]):__float2half_rn(0.f);
    }
    __syncwarp();
    nvcuda::wmma::fragment<nvcuda::wmma::accumulator,16,16,16,float> acc;
    nvcuda::wmma::fill_fragment(acc,0.f);
    #pragma unroll
    for(int k=0;k<128;k+=16) {
        nvcuda::wmma::fragment<nvcuda::wmma::matrix_a,16,16,16,half,nvcuda::wmma::row_major> af;
        nvcuda::wmma::fragment<nvcuda::wmma::matrix_b,16,16,16,half,nvcuda::wmma::col_major> bf;
        nvcuda::wmma::load_matrix_sync(af,a+k,128);
        nvcuda::wmma::load_matrix_sync(bf,b+k,128);
        nvcuda::wmma::mma_sync(acc,af,bf,acc);
    }
    nvcuda::wmma::store_matrix_sync(c,acc,16,nvcuda::wmma::mem_row_major);__syncwarp();
    for(int row=0;row<16;++row) if(mask&(1u<<row)) {
        int hit=0,q=g*16+row,j=ch.j+lane;
        if(lane<16 && j<l.size) {
            int id=ids[l.start+j];float d=norms[qids[q]]+norms[id]-2.f*c[row*16+lane];
            hit=d<=r2; if(distances)distances[q*n+id]=int(d);
        }
        hit=sumwarp(hit);if(!lane)atomicAdd(counts+q,hit);
    }
}

template<class T> T* upload(const std::vector<T>& x) {
    T* p;CK(cudaMalloc(&p,x.size()*sizeof(T)));CK(cudaMemcpy(p,x.data(),x.size()*sizeof(T),cudaMemcpyHostToDevice));return p;
}
int main(int argc,char** argv) try {
    require(argc==9,"usage: probe data query index pairs native-cost radius AB|BA check|timing");
    using Clock=std::chrono::steady_clock;auto start=Clock::now();
    CK(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
    int d,n,metric;std::ifstream f(argv[1]);require(bool(f>>d>>n>>metric)&&d==128&&metric==2&&n>0&&n<=65536,"bad dataset header");
    std::vector<float>x(n*128),norms(n);
    for(int i=0;i<n*128;++i) {require(bool(f>>x[i])&&x[i]>=0&&x[i]<=255&&x[i]==int(x[i]),"non-integer SIFT value");norms[i/128]+=x[i]*x[i];}
    int q;std::ifstream fq(argv[2]);require(bool(fq>>q)&&(q==32||q==128),"bad query count");
    std::vector<int> qids(q);for(auto&v:qids)require(bool(fq>>v)&&v>=0&&v<n,"bad query id");
    std::vector<Leaf> leaves;std::vector<int> ids;std::vector<Chunk> chunks;std::map<int,int> native;
    std::ifstream fi(argv[3]);int nid,size;std::set<int> unique_ids;
    while(fi>>nid>>size) {require(size>0&&size<=20&&!native.count(nid),"bad leaf");int l=leaves.size();native[nid]=l;leaves.push_back({int(ids.size()),size});
        for(int j=0;j<size;++j){int id;require(bool(fi>>id)&&id>=0&&id<n&&unique_ids.insert(id).second,"bad/repeated leaf id");ids.push_back(id);}
        for(int j=0;j<size;j+=16)chunks.push_back({l,j});}
    require(fi.eof()&&int(ids.size())==n,"index must partition all objects");
    std::ifstream fp(argv[4]);std::vector<Pair> pairs;int qi;std::set<std::pair<int,int>> unique_pairs;
    std::vector<unsigned> masks(leaves.size()*(q/16));long useful=0;
    while(fp>>qi>>nid){require(qi>=0&&qi<q&&native.count(nid)&&unique_pairs.insert({qi,nid}).second,"bad/repeated candidate");int l=native.at(nid);pairs.push_back({qi,l});useful+=leaves[l].size;masks[l*(q/16)+qi/16]|=1u<<(qi%16);}
    require(fp.eof()&&!pairs.empty(),"no candidate pairs");
    int radius=std::stoi(argv[6]);require(radius==300||radius==500,"radius outside contract");int r2=radius*radius;
    std::vector<int> oracle(q*n,-1),expected(q),sparse(q),native_counts(q);
    // Independent integer squared-distance oracle, including non-candidates.
    for(int i=0;i<q;++i)for(int j=0;j<n;++j){int sum=0;for(int k=0;k<128;++k){int v=int(x[qids[i]*128+k])-int(x[j*128+k]);sum+=v*v;}oracle[i*n+j]=sum;expected[i]+=sum<=r2;}
    std::vector<int> sparse_dist(q*n,-1);
    for(auto p:pairs)for(int j=0;j<leaves[p.l].size;++j){int id=ids[leaves[p.l].start+j];sparse_dist[p.q*n+id]=oracle[p.q*n+id];sparse[p.q]+=oracle[p.q*n+id]<=r2;}
    require(expected==sparse,"GTS candidate coverage failed full-table oracle");
    std::ifstream fc(argv[5]);std::string line;while(std::getline(fc,line)&&line!="Result num: "){}
    for(auto&v:native_counts)require(bool(fc>>v),"missing native GTS count");require(native_counts==expected,"native GTS counts failed oracle");
    long tiles=0;for(auto ch:chunks)for(int g=0;g<q/16;++g)tiles+=bool(masks[ch.l*(q/16)+g]);
    std::printf("shape,%d,%d,%d,%zu,%zu,%ld,%ld,%zu,%.9f\n",n,q,radius,leaves.size(),pairs.size(),useful,tiles,chunks.size()*(q/16),double(useful)/(tiles*256));
    auto*dx=upload(x);auto*dn=upload(norms);auto*dq=upload(qids);auto*di=upload(ids);auto*dl=upload(leaves);auto*dp=upload(pairs);auto*dc=upload(chunks);
    unsigned*dm;int*counts;int*dist;CK(cudaMalloc(&dm,masks.size()*sizeof(unsigned)));CK(cudaMalloc(&counts,q*sizeof(int)));CK(cudaMalloc(&dist,q*n*sizeof(int)));
    auto run=[&](char variant,int* diagnostic=nullptr){CK(cudaMemsetAsync(counts,0,q*sizeof(int)));if(variant=='A')simt<<<pairs.size(),128>>>(dx,dq,di,dl,dp,r2,n,counts,diagnostic);else{CK(cudaMemsetAsync(dm,0,masks.size()*sizeof(unsigned)));make_masks<<<(pairs.size()+255)/256,256>>>(dp,pairs.size(),dm,q/16);tensor<<<dim3(chunks.size(),q/16),32>>>(dx,dn,dq,di,dl,dc,dm,q/16,r2,n,counts,diagnostic);}CK(cudaGetLastError());};
    std::vector<int> actual(q),actual_dist(q*n);
    auto validate=[&](char v){CK(cudaMemset(dist,0xff,q*n*sizeof(int)));run(v,dist);CK(cudaMemcpy(actual.data(),counts,q*sizeof(int),cudaMemcpyDeviceToHost));CK(cudaMemcpy(actual_dist.data(),dist,q*n*sizeof(int),cudaMemcpyDeviceToHost));require(actual==expected,"count mismatch");require(actual_dist==sparse_dist,"exact candidate distance mismatch");};
    validate('A');validate('B');std::printf("correct,full_oracle_native_sparse_A_B_exact\n");
    std::printf("setup_ms,%.6f\n",std::chrono::duration<double,std::milli>(Clock::now()-start).count());
    std::string order=argv[7],mode=argv[8];require(order=="AB"||order=="BA","invalid order");require(mode=="check"||mode=="timing","invalid mode");
    if(mode=="timing") {
        cudaEvent_t a,b;CK(cudaEventCreate(&a));CK(cudaEventCreate(&b));
        for(char v:order){for(int i=0;i<20;++i)run(v);CK(cudaDeviceSynchronize());
            for(int batch:{1,64})for(int sample=0;sample<(batch==1?100:20);++sample){auto t=Clock::now();CK(cudaEventRecord(a));for(int j=0;j<batch;++j)run(v);CK(cudaEventRecord(b));CK(cudaEventSynchronize(b));float ms;CK(cudaEventElapsedTime(&ms,a,b));double us=std::chrono::duration<double,std::micro>(Clock::now()-t).count()/batch;std::printf("sample,%c,%d,%d,%.6f,%.6f\n",v,batch,sample,ms*1000/batch,us);}
            validate(v);
        }CK(cudaEventDestroy(a));CK(cudaEventDestroy(b));
    } else {
        // Repeated buffer reuse is a correctness gate, not a timing result.
        for(int i=0;i<20;++i){run('A');run('B');}CK(cudaDeviceSynchronize());validate('A');validate('B');
    }
    for(void* p:{(void*)dx,(void*)dn,(void*)dq,(void*)di,(void*)dl,(void*)dp,(void*)dc,(void*)dm,(void*)counts,(void*)dist})CK(cudaFree(p));
    std::puts("pass");return 0;
} catch(const std::exception& e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}
