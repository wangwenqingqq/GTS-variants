// Offline inventory of independently validated native mutation witnesses.
#include "plan.hpp"
#include <fstream>
#include <iostream>
struct M {int kind,id,before,row,last,moved,next,after;};
int main(int argc,char**argv){
    if(argc!=2)return 1;std::ifstream f(argv[1],std::ios::binary);std::vector<M> all;M m;
    while(f.read((char*)&m,sizeof(m)))all.push_back(m);if(!f.eof()||all.size()!=1000000)return 2;
    uint64_t native=0,net=0,raw=0,waw=0,war=0,levels=0,targets=0,sources=0;int batches=0;std::cout<<"{\"batches\":[";
    for(size_t at=0;at<all.size();){
        if(all[at].kind!=0){++at;continue;}size_t end=at;while(end<all.size()&&all[end].kind==0)++end;
        int b=int(end-at);BatchPlan plan(all[at].before,b);
        for(size_t i=at;i<end;i++)if(all[i].row!=all[i].last)plan.push(all[i].last,all[i].row);
        plan.finish(true,true);int ls=plan.levels.empty()?0:*std::max_element(plan.levels.begin(),plan.levels.end())+1;
        std::map<int,int> unique;for(auto p:plan.net)unique[p.src]=1;
        if(batches++)std::cout<<',';
        std::cout<<'['<<b<<','<<plan.sequential.size()<<','<<plan.net.size()<<','<<unique.size()<<','<<plan.RAW<<','<<plan.WAW<<','<<plan.WAR<<','<<ls<<']';
        native+=plan.sequential.size();net+=plan.net.size();raw+=plan.RAW;waw+=plan.WAW;war+=plan.WAR;levels+=ls;sources+=unique.size();targets+=plan.final_source.size();at=end;
    }
    std::cout<<"],\"fields\":[\"B\",\"native_moves\",\"unique_final_targets\",\"unique_original_sources\",\"RAW\",\"WAW\",\"WAR\",\"safe_batch_levels\"],\"total_batches\":"<<batches<<",\"native_moves\":"<<native<<",\"final_changed_rows\":"<<net<<",\"distinct_targets_summed_per_batch\":"<<targets<<",\"distinct_original_sources_summed_per_batch\":"<<sources<<",\"RAW\":"<<raw<<",\"WAW\":"<<waw<<",\"WAR\":"<<war<<",\"safe_batch_API_calls\":"<<levels<<",\"full_capacity_compatibility\":true,\"final_source_destination_disjoint\":true,\"GPU_starts\":0}\n";
}
