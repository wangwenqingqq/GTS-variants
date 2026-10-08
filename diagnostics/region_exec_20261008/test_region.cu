#include <cuda_runtime.h>
#include <cmath>
#include <iostream>
#include <numeric>
#define REGION_COUNTERS
#include "region_plan.hpp"
#include "region_exec.cuh"
using namespace rex;
void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> T* gpu(const std::vector<T>& x) {
    T* p=nullptr;ck(cudaMalloc((void**)&p,x.size()*sizeof(T)));
    ck(cudaMemcpy(p,x.data(),x.size()*sizeof(T),cudaMemcpyHostToDevice));return p;
}
template<class T> std::vector<T> cpu(T* p,int n){std::vector<T> x(n);ck(cudaMemcpy(x.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return x;}
void test(std::vector<Node> nodes,std::vector<int> empty,int n,int arity,const char* label) {
    std::vector<int> ids(n);std::iota(ids.rbegin(),ids.rend(),0);auto plan=make_plan(nodes,empty,ids,arity);
    int nn=nodes.size();auto nd=gpu(nodes);auto em=gpu(empty);auto id=gpu(ids);
    auto data=gpu(std::vector<float>(n*QUERY_DIM,0));auto deleted=gpu(std::vector<int>(n,0));auto qid=gpu(std::vector<int>{0});
    auto reg=gpu(plan.regions);auto ls=gpu(plan.leaf_slot);auto sp=gpu(plan.slot_pid);
    auto hit=gpu(std::vector<int>(n));auto dis=gpu(std::vector<float>(n));auto active=gpu(std::vector<int>(nn,1));
    auto leaf=gpu(std::vector<int>(plan.total_leaves,-1));auto countleaf=gpu(std::vector<int>(plan.regions.size(),0));auto err=gpu(std::vector<int>{0});
    Work w{gpu(std::vector<unsigned long long>(nn)),gpu(std::vector<unsigned long long>(nn)),gpu(std::vector<unsigned long long>(n)),gpu(std::vector<unsigned long long>(nn))};
    View v{nd,em,id,data,deleted,qid,reg,ls,sp,n,nn,int(plan.regions.size()),arity,7};
    for(int kind=0;kind<6;kind++) {
        // Full pass, object rejection, inactive root, deleted pivot, stale epoch,
        // visible capacity failure. Same tree/geometry/output slots in both modes.
        ck(cudaMemset(deleted,0,n*sizeof(int)));if(kind==3){int one=1;ck(cudaMemcpy(deleted,&one,4,cudaMemcpyHostToDevice));}
        std::vector<int> activity(nn,kind==2?0:1);ck(cudaMemcpy(active,activity.data(),nn*4,cudaMemcpyHostToDevice));
        auto current=plan.regions;if(kind==5)for(auto& r:current)r.leaves=0;
        ck(cudaMemcpy(reg,current.data(),current.size()*sizeof(Region),cudaMemcpyHostToDevice));
        std::vector<int> reference;std::vector<unsigned long long> refnodes,refpivots,refobjects,refleaves;
        for(int fused=0;fused<2;fused++) {
            ck(cudaMemset(hit,0,n*4));ck(cudaMemset(err,0,4));ck(cudaMemset(countleaf,0,plan.regions.size()*4));
            for(auto p:{w.nodes,w.pivots,w.leaves})ck(cudaMemset(p,0,nn*8));ck(cudaMemset(w.objects,0,n*8));
            float radius=kind==1?-1.0f:10000.0f;uint64_t epoch=kind==4?6:7;
            if(fused)traverse_regions<true><<<v.region_count,BLOCK_THREADS>>>(v,active,epoch,leaf,countleaf,radius,hit,dis,err,w);
            else {
                traverse_regions<false><<<v.region_count,BLOCK_THREADS>>>(v,active,epoch,leaf,countleaf,radius,hit,dis,err,w);
                verify_regions<<<v.region_count,BLOCK_THREADS>>>(v,leaf,countleaf,radius,hit,dis,w);
            }
            ck(cudaDeviceSynchronize());int error=cpu(err,1)[0];
            require(error==(kind==4?1:kind==5?2:0),"expected visible error");
            auto got=cpu(hit,n);auto objects=cpu(w.objects,n);auto visits=cpu(w.nodes,nn);auto pivots=cpu(w.pivots,nn);auto leaves=cpu(w.leaves,nn);
            if(kind<4)for(int s=0;s<n;s++) {
                require(got[s]==int(kind!=1 && kind!=2 && !(kind==3 && plan.slot_pid[s]==0)),"independent zero-vector integer oracle");
                require(objects[plan.slot_pid[s]]<=1,"duplicate verification writer");
            }
            if(!fused){reference=got;refnodes=visits;refpivots=pivots;refobjects=objects;refleaves=leaves;}
            else require(got==reference && visits==refnodes && pivots==refpivots && objects==refobjects && leaves==refleaves,"SPLIT/FUSED exact work sets differ");
        }
    }
    for(void* p:{(void*)nd,(void*)em,(void*)id,(void*)data,(void*)deleted,(void*)qid,(void*)reg,(void*)ls,(void*)sp,
                (void*)hit,(void*)dis,(void*)active,(void*)leaf,(void*)countleaf,(void*)err,(void*)w.nodes,(void*)w.pivots,(void*)w.objects,(void*)w.leaves})ck(cudaFree(p));
    std::cout<<label<<" PASS regions="<<plan.regions.size()<<" fallback="<<plan.fallbacks<<'\n';
}
int main() try {
    for(int n:{255,256,257}) {
        std::vector<Node> nodes(11);std::vector<int> empty(11,1);nodes[0]={-1,0,n,0,0};empty[0]=0;int pos=0;
        for(int j=1;j<=10;j++){int size=n/10+(j==10?n%10:0);nodes[j]={0,0,size,pos,1};empty[j]=0;pos+=size;}
        test(nodes,empty,n,10,('O'+std::to_string(n)).c_str());
        test({Node{-1,0,n,0,1}},{0},n,10,('L'+std::to_string(n)).c_str());
    }
    for(int target:{127,128,129}) {
        std::vector<Node> nodes(511);std::vector<int> empty(511,1);int n=(target+1)/2,used=0;
        std::function<void(int,int,int)> build=[&](int i,int lo,int size) {
            empty[i]=0;nodes[i]={0,0,size,lo,size==1};++used;
            if(size>1){int a=size/2;build(2*i+1,lo,a);build(2*i+2,lo+a,size-a);}
        };build(0,0,n);
        if(target==128){int i=0;while(!nodes[i].is_leaf)i=2*i+1;nodes[i].is_leaf=0;nodes[2*i+1]=nodes[i];nodes[2*i+1].is_leaf=1;empty[2*i+1]=0;++used;}
        require(used==target,"fixture node count");test(nodes,empty,n,2,('N'+std::to_string(target)).c_str());
    }
    std::cout<<"STRUCTURAL_PASS: 9 topologies x6 states x2 modes; integer oracle/exact work/stale/capacity\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
