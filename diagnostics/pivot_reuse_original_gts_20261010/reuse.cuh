// Query-local double-distance reuse. No new bound, traversal, or distance math.
#pragma once
#include <array>
#include <set>
#ifndef PR_ENABLED
#define PR_ENABLED 0
#endif
#ifndef PR_COUNTS
#define PR_COUNTS 0
#endif
int *pr_slot=nullptr, *pr_valid=nullptr;
double *pr_distance=nullptr;
int pr_capacity=0;
double pr_mapping_ms=0;
size_t pr_mapping_bytes=0;
#if PR_COUNTS
__managed__ unsigned long long pr_count[24];
std::vector<std::array<unsigned long long,24>> pr_records;
#define PR_ADD(index,value) atomicAdd(pr_count+(index),static_cast<unsigned long long>(value))
#else
#define PR_ADD(index,value) ((void)0)
#endif

// Mapping is immutable index setup, not a per-query hash table.
void pr_setup(TN* nodes,int* flags,int count,int n,int height) {
#if PR_ENABLED || PR_COUNTS
    auto begin=std::chrono::steady_clock::now();
    std::vector<TN> host(count);std::vector<int> empty(count),map(n,-1);
    CHECK(cudaMemcpy(host.data(),nodes,count*sizeof(TN),cudaMemcpyDeviceToHost));
    CHECK(cudaMemcpy(empty.data(),flags,count*sizeof(int),cudaMemcpyDeviceToHost));
    int start=1,width=10;
    for(int level=1;level<height;++level,start+=width,width*=10) {
        std::set<int> level_ids;
        if(start+width>count) throw std::runtime_error("incomplete index level");
        for(int nid=start;nid<start+width;nid+=10) if(empty[nid]==0) {
            int id=host[nid].pid;
            if(id<0||id>=n||!level_ids.insert(id).second)
                throw std::runtime_error("unsupported same-level alias pivot identity");
            for(int j=1;j<10;++j) if(empty[nid+j]==0 && host[nid+j].pid!=id)
                throw std::runtime_error("inconsistent sibling pivot identity");
            if(map[id]<0) map[id]=pr_capacity++;
        }
    }
    if(pr_capacity<=0) throw std::runtime_error("empty pivot mapping");
    CHECK(cudaMalloc(reinterpret_cast<void**>(&pr_slot),n*sizeof(int)));
    CHECK(cudaMemcpy(pr_slot,map.data(),n*sizeof(int),cudaMemcpyHostToDevice));
    pr_mapping_bytes=n*sizeof(int);
    pr_mapping_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
#endif
}

void pr_begin() {
#if PR_ENABLED || PR_COUNTS
    // All per-query allocations, cold reset and frees remain in host-ready time.
    CHECK(cudaMalloc(reinterpret_cast<void**>(&pr_valid),pr_capacity*sizeof(int)));
    CHECK(cudaMalloc(reinterpret_cast<void**>(&pr_distance),pr_capacity*sizeof(double)));
    CHECK(cudaMemset(pr_valid,0,pr_capacity*sizeof(int)));
#endif
#if PR_COUNTS
    std::fill(pr_count,pr_count+24,0ULL);
#endif
}
void pr_end() {
#if PR_ENABLED || PR_COUNTS
    CHECK(cudaFree(pr_valid));CHECK(cudaFree(pr_distance));
    pr_valid=nullptr;pr_distance=nullptr;
#endif
}

// Diagnostic bridge duplicates work intentionally; never compile into timing.
#if PR_COUNTS
__device__ void pr_bridge(double cached,const float* data,int id,int q,int d) {
    double value=0;
    if(id!=q) {
        for(int j=0;j<d;++j) value+=pow(data[id*d+j]-data[q*d+j],2);
        value=pow(value,0.5);
    }
    PR_ADD(18,1);
    if(__double_as_longlong(value)!=__double_as_longlong(cached)) PR_ADD(19,1);
}
#endif
