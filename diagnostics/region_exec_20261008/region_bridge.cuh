#pragma once
#include "region_plan.hpp"
#include "region_exec.cuh"
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
        else if(s=="REGION_SPLIT")mode=2;
        else if(s=="REGION_FUSED")mode=3;
        else if(s!="NATIVE")throw std::runtime_error("unknown region mode");
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
        allocate(hit,n);allocate(prefix,n);allocate(distances,n);
        u10_ck(cudaMallocManaged((void**)&error,sizeof(int)));owned_bytes+=sizeof(int);
        allocated_bytes+=sizeof(int);++allocations;*error=0;
        peak_owned_bytes=std::max(peak_owned_bytes,owned_bytes);
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
        int parity=0;const auto& offsets=mode==1?plan.level_offsets:plan.skeleton_offsets;
        const int* parent_list=mode==1?parents:skeleton;
        for(size_t l=1;l<offsets.size();l++) {
            int begin=offsets[l-1],num=offsets[l]-begin;
            if(num)parent_groups<<<num,BLOCK_THREADS>>>(view,parent_list,begin,flags[parity],flags[1-parity],active,radius,work);
            parity=1-parity;
        }
        if(mode==1) {
            materialize<<<(plan.total_leaves+BLOCK_THREADS-1)/BLOCK_THREADS,BLOCK_THREADS>>>(view,leaves,plan.total_leaves,active,leaf_list,work);
            verify_materialized<<<plan.total_leaves,BLOCK_THREADS>>>(view,leaf_list,radius,hit,distances,work);
        } else {
            uint64_t task_epoch=view.tree_epoch;
            if(u10_env("REGION_STALE"))--task_epoch;
            if(mode==2) {
                traverse_regions<false><<<view.region_count,BLOCK_THREADS>>>(view,active,task_epoch,leaf_list,leaf_counts,radius,hit,distances,error,work);
                verify_regions<<<view.region_count,BLOCK_THREADS>>>(view,leaf_list,leaf_counts,radius,hit,distances,work);
            } else traverse_regions<true><<<view.region_count,BLOCK_THREADS>>>(view,active,task_epoch,leaf_list,leaf_counts,radius,hit,distances,error,work);
        }
        u10_ck(cudaGetLastError());
        int count=thrust::reduce(thrust::device,hit,hit+view.n,0);
        u10_ck(cudaMallocManaged((void**)&counts,sizeof(int)));counts[0]=count;
        u10_ck(cudaMallocManaged((void**)&count_prefix,sizeof(int)));count_prefix[0]=0;
        u10_ck(cudaMallocManaged((void**)&ids,std::max(count,1)*sizeof(int)));
        u10_ck(cudaMallocManaged((void**)&result,std::max(count,1)*sizeof(float)));
        thrust::exclusive_scan(thrust::device,hit,hit+view.n,prefix);
        collect<<<(view.n+BLOCK_THREADS-1)/BLOCK_THREADS,BLOCK_THREADS>>>(view,hit,prefix,distances,ids,result);
        u10_ck(cudaDeviceSynchronize());
        require(!*error,"stale epoch or local capacity error; reject entire query");
#ifdef REGION_COUNTERS
        std::cout<<"REGION_WORK {\"epoch\":"<<epoch<<",\"qid\":"<<qids[0]<<",\"n\":"<<view.n;
        for(auto item:{std::pair<const char*,unsigned long long*>{"nodes",work.nodes},{"pivots",work.pivots},{"leaves",work.leaves},{"objects",work.objects}}) {
            int size=std::string(item.first)=="objects"?view.n:view.node_count;
            std::vector<unsigned long long> x(size);u10_ck(cudaMemcpy(x.data(),item.second,size*sizeof(unsigned long long),cudaMemcpyDeviceToHost));
            std::cout<<",\""<<item.first<<"\":[";
            for(int i=0;i<size;i++)std::cout<<(i?",":"")<<x[i];std::cout<<"]";
        }
        std::cout<<"}\n";
#endif
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
