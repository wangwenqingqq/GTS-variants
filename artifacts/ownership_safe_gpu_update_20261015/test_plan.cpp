// Independent full-capacity row replay versus composed and wave schedules.
#include "plan.hpp"
#include <numeric>
#include <iostream>
#include <random>
static uint64_t cases=0;
static void test(int n,const std::vector<int>& ids){
    std::vector<int> owners(n),pos(n),native(n);std::iota(owners.begin(),owners.end(),0);pos=owners;native=owners;
    BatchPlan final(n,int(ids.size())),wave(n,int(ids.size()),false);
    for(int id:ids){int row=pos[id],last=int(owners.size())-1;if(row!=last){native[row]=native[last];final.push(last,row);wave.push(last,row);int moved=owners.back();owners[row]=moved;pos[moved]=row;}owners.pop_back();pos[id]=-1;}
    final.finish(false);wave.finish(true);std::vector<int> a(n),b(n);std::iota(a.begin(),a.end(),0);b=a;
    for(auto m:final.net)a[m.dst]=a[m.src];
    int levels=wave.levels.empty()?0:*std::max_element(wave.levels.begin(),wave.levels.end())+1;
    // Reverse every independent level,adversarially changing all permitted copy orders.
    for(int l=0;l<levels;l++)for(int i=int(wave.sequential.size())-1;i>=0;i--)if(wave.levels[i]==l){auto m=wave.sequential[i];b[m.dst]=b[m.src];}
    if(a!=native||b!=native)throw std::runtime_error("capacity disagreement");++cases;
}
static void visit(int n,std::vector<int>& ids,std::vector<bool>& used){
    if(!ids.empty())test(n,ids);
    for(int i=0;i<n;i++)if(!used[i]){used[i]=true;ids.push_back(i);visit(n,ids,used);ids.pop_back();used[i]=false;}
}
int main(){
    for(int n=1;n<=8;n++){std::vector<int> ids;std::vector<bool> used(n);visit(n,ids,used);}
    if(cases!=125664)return 1;
    std::mt19937 g(2026101518);
    for(int n:{65,513,4096})for(int b:{1,32,512})for(int t=0;t<64;t++){std::vector<int> ids(n);std::iota(ids.begin(),ids.end(),0);std::shuffle(ids.begin(),ids.end(),g);ids.resize(std::min(n,b));test(n,ids);}
    std::cout<<"{\"passed\":true,\"exhaustive\":125664,\"random\":576,\"all_capacity\":true,\"reversed_wave_order\":true,\"GPU_starts\":0}\n";
}
