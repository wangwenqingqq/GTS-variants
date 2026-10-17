// Full allocated capacity is the authority,including all subsequently retired rows.
#include "generic.hpp"
#include <numeric>
#include <random>
#include <iostream>
static uint64_t cases=0;
static void check(int n,const std::vector<int>& ids){
    std::vector<int> owners(n),pos(n),sequential(n);std::iota(owners.begin(),owners.end(),0);pos=owners;sequential=owners;
    BatchPlan tp(n,int(ids.size()));
    for(int id:ids){int row=pos[id],last=int(owners.size())-1;
        if(row!=last){tp.push(last,row);sequential[row]=sequential[last];int moved=owners.back();owners[row]=moved;pos[moved]=row;}
        owners.pop_back();pos[id]=-1;
    }
    auto generic=generic_compile(tp.sequential);tp.finish(false);
    if(generic.size()!=tp.net.size())throw std::runtime_error("plan length mismatch");
    std::vector<int> actual(n);std::iota(actual.begin(),actual.end(),0);
    for(size_t i=0;i<generic.size();i++){
        if(generic[i].src!=tp.net[i].src||generic[i].dst!=tp.net[i].dst)throw std::runtime_error("plan assignment mismatch");
        actual[generic[i].dst]=generic[i].src;
    }
    if(actual!=sequential)throw std::runtime_error("full capacity mismatch");++cases;
}
static void visit(int n,std::vector<int>& ids,std::vector<bool>& used){
    if(!ids.empty())check(n,ids);
    for(int i=0;i<n;i++)if(!used[i]){ids.push_back(i);used[i]=true;visit(n,ids,used);used[i]=false;ids.pop_back();}
}
int main(){
    for(int n=1;n<=8;n++){std::vector<int> ids;std::vector<bool> used(n);visit(n,ids,used);}
    if(cases!=125664)return 1;
    std::mt19937 rng(2026101703);
    for(int n:{65,513,4096})for(int b:{1,32,512})for(int t=0;t<64;t++){
        std::vector<int> ids(n);std::iota(ids.begin(),ids.end(),0);std::shuffle(ids.begin(),ids.end(),rng);ids.resize(std::min(n,b));check(n,ids);
    }
    std::cout<<"{\"passed\":true,\"exhaustive\":125664,\"random\":576,\"generic_equals_tail\":true,\"all_allocated_capacity\":true,\"GPU_starts\":0}\n";
}
