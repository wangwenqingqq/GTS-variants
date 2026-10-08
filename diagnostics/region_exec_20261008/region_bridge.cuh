#pragma once
#include "region_plan.hpp"
#include "parallel_range.cuh"
#include <thrust/scan.h>
#include <thrust/reduce.h>
#include <fstream>
#include <iomanip>
#include <cstdlib>
namespace rex {
struct Bridge {
    int mode=0; uint64_t epoch=0; Plan plan; View view{};
    int *parents=nullptr,*skeleton=nullptr,*leaves=nullptr,*slot_pid=nullptr,*leaf_slot=nullptr;
    Region* regions=nullptr;
    int *flags[2]{},*active=nullptr,*leaf_list=nullptr,*leaf_counts=nullptr,*hit=nullptr,*prefix=nullptr,*error=nullptr;
    float* distances=nullptr; Work work{};
    size_t owned_bytes=0,peak_owned_bytes=0,allocated_bytes=0,transferred_bytes=0;
    int allocations=0,refreshes=0;double setup_ms=0,context_ms=0;
    std::vector<double> refresh_ms;
    struct Refresh {int n,regions,nodes,leaves,fallbacks;uint64_t epoch;size_t bytes;};
    std::vector<Refresh> refresh_rows;
    Bridge() {
        const char* p=std::getenv("REGION_MODE");std::string s=p?p:"NATIVE";
        if(s=="PAR_STRONG")mode=1;
        else if(s!="NATIVE")throw std::runtime_error("region mode not yet implemented");
    }
    template<class T> void allocate(T*& p,size_t n) {
        if(!n){p=nullptr;return;}
        u10_ck(cudaMalloc((void**)&p,n*sizeof(T)));owned_bytes+=n*sizeof(T);
        allocated_bytes+=n*sizeof(T);++allocations;peak_owned_bytes=std::max(peak_owned_bytes,owned_bytes);
    }
    template<class T> void upload(T*& p,const std::vector<T>& x) {
        allocate(p,x.size());if(!x.empty()){u10_ck(cudaMemcpy(p,x.data(),x.size()*sizeof(T),cudaMemcpyHostToDevice));transferred_bytes+=x.size()*sizeof(T);}
    }
    void release_plan() {
        for(void* p:{(void*)parents,(void*)skeleton,(void*)leaves,(void*)slot_pid,(void*)leaf_slot,
                    (void*)regions,(void*)flags[0],(void*)flags[1],(void*)active,(void*)leaf_list,
                    (void*)leaf_counts,(void*)hit,(void*)prefix,(void*)error,(void*)distances,
                    (void*)work.nodes,(void*)work.pivots,(void*)work.objects,(void*)work.leaves})if(p)u10_ck(cudaFree(p));
        parents=skeleton=leaves=slot_pid=leaf_slot=nullptr;regions=nullptr;
        flags[0]=flags[1]=active=leaf_list=leaf_counts=hit=prefix=error=nullptr;distances=nullptr;work={};owned_bytes=0;
    }
    void refresh(TN* nodes,int* empty,int* order,int nn,int n,int arity) {
        if(!mode)return;auto start=U10Clock::now();u10_ck(cudaDeviceSynchronize());
        release_plan();
        static_assert(sizeof(TN)==sizeof(Node),"native node layout");
        std::vector<Node> hn(nn);std::vector<int> he(nn),hi(n);
        u10_ck(cudaMemcpy(hn.data(),nodes,nn*sizeof(Node),cudaMemcpyDeviceToHost));
        u10_ck(cudaMemcpy(he.data(),empty,nn*sizeof(int),cudaMemcpyDeviceToHost));
        u10_ck(cudaMemcpy(hi.data(),order,n*sizeof(int),cudaMemcpyDeviceToHost));
        transferred_bytes+=nn*(sizeof(Node)+sizeof(int))+n*sizeof(int);
        require(arity==10,"prototype requires original arity10");
        plan=make_plan(hn,he,hi,arity);
        upload(parents,plan.parents);upload(skeleton,plan.skeleton);upload(leaves,plan.leaves);
        upload(slot_pid,plan.slot_pid);upload(leaf_slot,plan.leaf_slot);upload(regions,plan.regions);
        for(auto& p:flags)allocate(p,nn);allocate(active,nn);
        allocate(leaf_list,plan.total_leaves);allocate(leaf_counts,plan.regions.size());
        allocate(hit,n);allocate(prefix,n);allocate(distances,n);allocate(error,1);
#ifdef REGION_COUNTERS
        allocate(work.nodes,nn);allocate(work.pivots,nn);allocate(work.objects,n);allocate(work.leaves,nn);
#endif
        view={(Node*)nodes,empty,order,nullptr,nullptr,nullptr,regions,leaf_slot,slot_pid,n,nn,int(plan.regions.size()),arity,++epoch};
        u10_ck(cudaDeviceSynchronize());++refreshes;
        refresh_rows.push_back({n,int(plan.regions.size()),plan.nonempty_nodes,plan.total_leaves,plan.fallbacks,epoch,owned_bytes});
        refresh_ms.push_back(u10_ms(start));
    }
    void search(short* data,int* deleted,int* qids,int qnum,float radius,int* info,
                int*& counts,int*& count_prefix,int*& ids,float*& result) {
        require(qnum==1 && info[0]==QUERY_DIM && info[2]==2,"only frozen B1 D128 L2 prototype");
        view.data=data;view.deleted=deleted;view.qids=qids;
        for(auto p:flags)u10_ck(cudaMemset(p,0,view.node_count*sizeof(int)));
        u10_ck(cudaMemset(active,0,view.node_count*sizeof(int)));
        int one=1;u10_ck(cudaMemcpy(flags[0],&one,sizeof(int),cudaMemcpyHostToDevice));
        u10_ck(cudaMemcpy(active,&one,sizeof(int),cudaMemcpyHostToDevice));
        u10_ck(cudaMemset(hit,0,view.n*sizeof(int)));
#ifdef REGION_COUNTERS
        for(auto p:{work.nodes,work.pivots,work.leaves})u10_ck(cudaMemset(p,0,view.node_count*sizeof(unsigned long long)));
        u10_ck(cudaMemset(work.objects,0,view.n*sizeof(unsigned long long)));
#endif
        int parity=0;
        for(size_t l=1;l<plan.level_offsets.size();l++) {
            int begin=plan.level_offsets[l-1],num=plan.level_offsets[l]-begin;
            if(num)parent_groups<<<num,BLOCK_THREADS>>>(view,parents,begin,flags[parity],flags[1-parity],active,radius,work);
            parity=1-parity;
        }
        materialize<<<(plan.total_leaves+BLOCK_THREADS-1)/BLOCK_THREADS,BLOCK_THREADS>>>(view,leaves,plan.total_leaves,active,leaf_list,work);
        verify_materialized<<<plan.total_leaves,BLOCK_THREADS>>>(view,leaf_list,radius,hit,distances,work);
        u10_ck(cudaGetLastError());
        int count=thrust::reduce(thrust::device,hit,hit+view.n,0);
        u10_ck(cudaMallocManaged((void**)&counts,sizeof(int)));counts[0]=count;
        u10_ck(cudaMallocManaged((void**)&count_prefix,sizeof(int)));count_prefix[0]=0;
        u10_ck(cudaMallocManaged((void**)&ids,std::max(count,1)*sizeof(int)));
        u10_ck(cudaMallocManaged((void**)&result,std::max(count,1)*sizeof(float)));
        thrust::exclusive_scan(thrust::device,hit,hit+view.n,prefix);
        collect<<<(view.n+BLOCK_THREADS-1)/BLOCK_THREADS,BLOCK_THREADS>>>(view,hit,prefix,distances,ids,result);
        u10_ck(cudaDeviceSynchronize());
    }
    void finish() {if(mode)release_plan();}
    void write(const std::string& out) {
        std::ofstream s(out+".region.json");s<<std::setprecision(17)
        <<"{\"mode\":"<<mode<<",\"setup_ms\":"<<setup_ms<<",\"context_ms\":"<<context_ms
        <<",\"setup_plus_trace_ms\":"<<setup_ms+u10.trace_ms<<",\"refreshes\":"<<refreshes
        <<",\"peak_owned_bytes\":"<<peak_owned_bytes<<",\"allocated_bytes\":"<<allocated_bytes
        <<",\"transferred_bytes\":"<<transferred_bytes<<",\"allocations\":"<<allocations
        <<",\"final_owned_bytes\":"<<owned_bytes<<",\"refresh_rows\":[";
        for(size_t i=0;i<refresh_rows.size();i++) {auto r=refresh_rows[i];s<<(i?",":"")
          <<"{\"n\":"<<r.n<<",\"regions\":"<<r.regions<<",\"nodes\":"<<r.nodes<<",\"leaves\":"<<r.leaves
          <<",\"fallbacks\":"<<r.fallbacks<<",\"epoch\":"<<r.epoch<<",\"owned_bytes\":"<<r.bytes<<",\"ms\":"<<refresh_ms[i]<<'}';}
        s<<"]}\n";
    }
};
static Bridge bridge;
}
