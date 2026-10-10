// Shared exact-score/complete-output repair and two independently gated mechanisms.
#pragma once
#include <array>
#include <set>
#include <thrust/sort.h>
// CUB copies the entire key, including alignment bytes; make every byte defined.
struct NavKey { double score; int id; int reserved=0; };
static_assert(sizeof(NavKey)==16);
struct NavLess { __host__ __device__ bool operator()(NavKey a,NavKey b) const {
    return a.score<b.score || (a.score==b.score && a.id<b.id);
}};
struct NavState {
    int mode,n,k,capacity,epoch;
    double *scores,*memo,*out_scores;
    int *slot,*tags,*safe,*out_ids;
    NavKey *keys,*candidates;
    unsigned long long *counts;
};
__managed__ NavState nav;
static std::vector<double> nav_replay_upper;
static size_t nav_replay_cursor=0;
static void nav_replay_level(double* disk) {
    if(nav_replay_upper.empty())return;
    if(!nav.counts || !(nav.mode&2) || nav_replay_cursor>=nav_replay_upper.size())
        throw std::runtime_error("invalid diagnostic replay contract");
    double upper=nav_replay_upper[nav_replay_cursor++];
    CHECK(cudaMemcpy(disk,&upper,sizeof(double),cudaMemcpyHostToDevice));
}
__device__ double nav_score(const float* a,const float* b,int d) {
    double s=0.;for(int j=0;j<d;++j) {
        double x=__dsub_rn(double(a[j]),double(b[j]));
        s=__dadd_rn(s,__dmul_rn(x,x));
    }return s;
}
__device__ void nav_count(int i,unsigned long long x=1) {
    if(nav.counts) atomicAdd(nav.counts+i,x);
}
__device__ double nav_distance(const float* data,int row,int q,int d,bool pivot) {
    nav_count(pivot?0:1);int slot=nav.slot[row];
    bool reuse=(nav.mode&1) && slot>=0 && nav.tags[slot]==nav.epoch;
    double s;
    if(reuse) {s=nav.memo[slot];nav_count(pivot?2:3);}
    else {s=nav_score(data+size_t(row)*d,data+size_t(q)*d,d);nav_count(4);nav_count(5,d);}
    nav.scores[row]=s;
    // Each level's pivot rows and all leaf object owners are distinct: checked at setup.
    // Default-stream completion separates publication, later levels, and leaf readers.
    if(pivot && (nav.mode&1) && !reuse) {nav.memo[slot]=s;nav.tags[slot]=nav.epoch;nav_count(6);}
    return __dsqrt_rn(s);
}
__device__ void nav_insert(NavKey* top,int k,NavKey x) {
    for(int i=0;i<k;++i) if(top[i].id==x.id) return;
    for(int i=0;i<k;++i) if(NavLess{}(x,top[i])) {
        for(int j=k-1;j>i;--j)top[j]=top[j-1];top[i]=x;break;
    }
}
__global__ void nav_update(TN* nodes,int offset_n,int groups,double* list,int offset_p,double* disk) {
    if(threadIdx.x||blockIdx.x)return;
    if(!(nav.mode&2)) {
        // Preserve the native O(1) current-level Kth read after its existing sort.
        int index=int(list[offset_p+nav.k-1]);
        double kth=list[offset_p+groups+index];
        if(kth<INFI_DIS)disk[0]=fmin(disk[0],kth);return;
    }
    for(int i=0;i<groups;++i) {
        if(list[offset_p+groups+i]>=INFI_DIS)continue;
        int row=nodes[offset_n+10*i].pid;
        NavKey x={nav.scores[row],row};nav_insert(nav.candidates,nav.k,x);
    }
    NavKey* top=nav.candidates;
    if(isfinite(top[nav.k-1].score))disk[0]=fmin(disk[0],__dsqrt_rn(top[nav.k-1].score));
}
__global__ void nav_keys(TN* nodes,int* ids,double* list,int offset,int cap,int slots) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<slots) {
        int nid=int(list[offset+cap+i/MAX_SIZE]);TN node=nodes[nid];int pos=i%MAX_SIZE;
        int row=pos<node.size && node.is_leaf?ids[node.lid+pos]:-1;
        bool valid=row>=0 && list[offset+cap*(3+MAX_SIZE)+i]<INFI_DIS;
        nav.keys[i]={valid?nav.scores[row]:INFINITY,valid?row:2147483647};
        if(valid && (nav.mode&2))for(int j=0;j<nav.k;++j) if(nav.candidates[j].id==row) {
            nav.keys[i]={INFINITY,2147483647};break;
        }
    }
    if(i<nav.k)nav.keys[slots+i]=(nav.mode&2)?nav.candidates[i]:NavKey{INFINITY,2147483647};
}
__global__ void nav_emit(int slots) {
    int i=threadIdx.x;if(i<nav.k) {
        bool valid=i<slots+nav.k && isfinite(nav.keys[i].score);
        nav.out_ids[i]=valid?nav.keys[i].id:-1;nav.out_scores[i]=valid?nav.keys[i].score:INFINITY;
    }
}
// Validation checks the original split intervals, widened only for correctness.
// Failed coverage disables that node's bound; it never substitutes a tighter interval.
__global__ void nav_cover(const float* data,TN* nodes,int* flags,int* ids,int count,int d) {
    int nid=blockIdx.x;if(nid==0||nid>=count||flags[nid])return;
    TN node=nodes[nid];double lo=fmax(0.,double(node.min_dis)-.01);
    double hi=nid%10?double(nodes[nid+1].min_dis)+.01:INFINITY;
    for(int i=threadIdx.x;i<node.size;i+=blockDim.x) {
        double dis=__dsqrt_rn(nav_score(data+size_t(ids[node.lid+i])*d,data+size_t(node.pid)*d,d));
        if(lo>fmax(0.,dis-1e-6)||hi<dis+1e-6)atomicExch(nav.safe+nid,0);
    }
}
static void nav_setup(TN* nodes,int* flags,int count,int n,int h,int k,int mode,bool diagnostic,
                      const float* data,int* ids,int d) {
    std::vector<TN> host(count);std::vector<int> empty(count),map(n,-1);
    CHECK(cudaMemcpy(host.data(),nodes,count*sizeof(TN),cudaMemcpyDeviceToHost));
    CHECK(cudaMemcpy(empty.data(),flags,count*sizeof(int),cudaMemcpyDeviceToHost));
    int capacity=0,start=1,width=10;
    for(int level=1;level<h;++level,start+=width,width*=10) {
        std::set<int> seen;
        for(int nid=start;nid<start+width;nid+=10)if(!empty[nid]) {
            int row=host[nid].pid;
            if(row<0||row>=n||!seen.insert(row).second)throw std::runtime_error("same-level pivot ownership");
            if(map[row]<0)map[row]=capacity++;
        }
    }
    nav={};nav.mode=mode;nav.n=n;nav.k=k;nav.capacity=capacity;
    CHECK(cudaMalloc((void**)&nav.slot,n*sizeof(int)));CHECK(cudaMemcpy(nav.slot,map.data(),n*sizeof(int),cudaMemcpyHostToDevice));
    CHECK(cudaMalloc((void**)&nav.safe,count*sizeof(int)));std::vector<int> safe(count,1);
    CHECK(cudaMemcpy(nav.safe,safe.data(),count*sizeof(int),cudaMemcpyHostToDevice));
    nav_cover<<<count,256>>>(data,nodes,flags,ids,count,d);CHECK(cudaDeviceSynchronize());
    CHECK(cudaMemcpy(safe.data(),nav.safe,count*sizeof(int),cudaMemcpyDeviceToHost));
    int disabled=0;for(int i=1;i<count;++i)if(!empty[i]&&!safe[i])++disabled;
    std::cout<<"GEOMETRY {\"coverage_disabled_nodes\":"<<disabled<<",\"split_margin\":0.01,\"distance_envelope\":0.000001}"<<std::endl;
    CHECK(cudaMalloc((void**)&nav.out_ids,k*sizeof(int)));CHECK(cudaMalloc((void**)&nav.out_scores,k*sizeof(double)));
    if(diagnostic)CHECK(cudaMalloc((void**)&nav.counts,8*sizeof(unsigned long long)));
}
static void nav_begin() {
    nav.epoch=1; // Fresh query-owned allocations: no previous query/storage can survive.
    CHECK(cudaMalloc((void**)&nav.scores,size_t(nav.n)*sizeof(double)));
    CHECK(cudaMalloc((void**)&nav.candidates,nav.k*sizeof(NavKey)));
    std::vector<NavKey> top(nav.k,{INFINITY,2147483647});
    CHECK(cudaMemcpy(nav.candidates,top.data(),nav.k*sizeof(NavKey),cudaMemcpyHostToDevice));
    if(nav.mode&1) {
        CHECK(cudaMalloc((void**)&nav.memo,nav.capacity*sizeof(double)));
        CHECK(cudaMalloc((void**)&nav.tags,nav.capacity*sizeof(int)));
        CHECK(cudaMemset(nav.tags,0,nav.capacity*sizeof(int)));
    }
    if(nav.counts)CHECK(cudaMemset(nav.counts,0,8*sizeof(unsigned long long)));
}
static void nav_end() {
    for(void* p:{(void*)nav.scores,(void*)nav.candidates,(void*)nav.keys,(void*)nav.memo,(void*)nav.tags})if(p)CHECK(cudaFree(p));
    nav.scores=nullptr;nav.candidates=nullptr;nav.keys=nullptr;nav.memo=nullptr;nav.tags=nullptr;
}
static void nav_trace(int level,int first,int width,double* list,int offset,double* disk) {
    std::vector<double> flags(width);double upper;
    CHECK(cudaMemcpy(flags.data(),list+offset+width/10*3,width*sizeof(double),cudaMemcpyDeviceToHost));
    CHECK(cudaMemcpy(&upper,disk,sizeof(double),cudaMemcpyDeviceToHost));
    // Order-sensitive deterministic visit digest; supplementary, not cryptographic.
    unsigned long long hash=1469598103934665603ULL;int visited=0;
    std::string bits((width+3)/4,'0');
    const char* hex="0123456789abcdef";
    for(int i=0;i<width;i+=4){int value=0;for(int j=0;j<4&&i+j<width;++j)if(flags[i+j]==1)value|=1<<j;bits[i/4]=hex[value];}
    for(int i=0;i<width;++i)if(flags[i]==1) {++visited;hash^=first+i;hash*=1099511628211ULL;}
    std::vector<NavKey> top(nav.k);CHECK(cudaMemcpy(top.data(),nav.candidates,nav.k*sizeof(NavKey),cudaMemcpyDeviceToHost));
    std::cout<<"TRACE {\"level\":"<<level<<",\"upper\":"<<std::setprecision(17);
    if(std::isfinite(upper))std::cout<<upper;else std::cout<<"null";
    std::cout<<",\"visited\":"<<visited<<",\"digest\":\""<<hash<<"\",\"visit_bits_hex\":\""<<bits<<"\",\"candidates\":[";
    for(int i=0;i<nav.k;++i){if(i)std::cout<<',';std::cout<<'['<<top[i].id<<',';
        if(std::isfinite(top[i].score))std::cout<<top[i].score;else std::cout<<"null";std::cout<<']';}
    std::cout<<"]}"<<std::endl;
}
