#pragma once
#include "build_counts.hpp"
#include <filesystem>
#include <numeric>
namespace rca {
inline std::vector<int> base,pending,next_base,ins,del;
inline int rebuild=0,last_step=-1,current_step=-1;
inline bool enabled(){return std::getenv("RCA_DIR") && pe::trace==&pe::measured;}
template<class T> inline std::vector<T> copy(const T* p,size_t n) {
    std::vector<T> h(n);if(n)u10_ck(cudaMemcpy(h.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return h;
}
template<class T> inline void host_file(const std::filesystem::path& p,const std::vector<T>& h) {
    std::ofstream f(p,std::ios::binary);if(!h.empty())f.write((const char*)h.data(),h.size()*sizeof(T));
    pe::require(bool(f),"RCA host snapshot write");
}
inline void device_file(const std::filesystem::path& path,const void* p,size_t bytes) {
    std::ofstream f(path,std::ios::binary);std::vector<char> h(8*1024*1024);
    for(size_t at=0;at<bytes;at+=h.size()){
        size_t take=std::min(h.size(),bytes-at);
        u10_ck(cudaMemcpy(h.data(),(const char*)p+at,take,cudaMemcpyDeviceToHost));f.write(h.data(),take);
        pe::require(bool(f),"RCA device snapshot write");
    }
    pe::require(bool(f),"RCA device snapshot open");
}
inline void json_ids(std::ostream& f,const std::vector<int>& v) {
    f<<'[';for(size_t j=0;j<v.size();j++)f<<(j?",":"")<<v[j];f<<']';
}
inline void event(int step,int flag) {
    if(!enabled())return;current_step=step;
    if(step==0){base.resize(pe::measured.n);std::iota(base.begin(),base.end(),0);
        pending.clear();ins.clear();del.clear();rebuild=0;last_step=-1;}
    int oid=pe::trace->occ.at(step);
    if(flag==0){pending.push_back(oid);ins.push_back(oid);}
    if(flag==1){del.push_back(oid);auto it=std::find(pending.begin(),pending.end(),oid);if(it!=pending.end())pending.erase(it);}
}
inline void snapshot(bool pre,TN* nodes,int* empty,int* order,int nn,int n,int d,
                     int* deleted,int* insertion,int buffer) {
    if(!enabled())return;u10_ck(cudaDeviceSynchronize());
    pe::require(size_t(n)==base.size()&&size_t(buffer)==pending.size(),"RCA row/buffer mapping");
    auto hd=copy(deleted,n),hb=copy(insertion,buffer),he=copy(empty,nn);auto hn=copy(nodes,nn);
    std::vector<int> expected;
    for(int j=0;j<n;j++){
        pe::require(bool(pe::ranks.alive.at(base[j]))==!hd[j],"RCA tombstone/live map");
        if(!hd[j])expected.push_back(base[j]);
    }
    for(int oid:pending){pe::require(pe::ranks.alive.at(oid),"RCA pending alive");expected.push_back(oid);}
    std::sort(expected.begin(),expected.end());auto live=pe::ranks.final();
    pe::require(expected==live,"RCA complete occurrence map");
    auto root=std::filesystem::path(std::getenv("RCA_DIR"))/(std::string(pre?"PRE_R":"POST_R")+std::to_string(rebuild));
    pe::require(std::filesystem::create_directories(root),"RCA snapshot exists");
    host_file(root/"base.i32",base);host_file(root/"deleted.i32",hd);host_file(root/"buffer.i32",pending);
    host_file(root/"buffer_positions.i32",hb);host_file(root/"live.i32",live);
    host_file(root/"nodes.bin",hn);host_file(root/"empty.i32",he);
    device_file(root/"order.i32",order,size_t(n)*4);
    device_file(root/"lo.f64",target::bounds.lo,size_t(nn)*8);
    device_file(root/"hi.f64",target::bounds.hi,size_t(nn)*8);
    pe::require(n%32==0&&uk::live.n==n&&uk::live.d==d,"RCA frozen pack shape");
    device_file(root/"packed.f32",uk::live.packed,size_t(n)*d*4);
    const auto& p=rex::bridge.plan;
    host_file(root/"plan_regions.i32",p.regions);host_file(root/"plan_leaf_slot.i32",p.leaf_slot);
    host_file(root/"plan_slot_pid.i32",p.slot_pid);host_file(root/"plan_leaves.i32",p.leaves);
    host_file(root/"plan_owners.i32",p.owners);host_file(root/"plan_parents.i32",p.parents);
    host_file(root/"plan_skeleton.i32",p.skeleton);host_file(root/"plan_level_offsets.i32",p.level_offsets);
    host_file(root/"plan_skeleton_offsets.i32",p.skeleton_offsets);
    long long distance_tasks=0,active_nodes=0,refit_tasks=0;int valid=0,leaf_count=0;
    for(auto l:levels){distance_tasks+=l.distance_tasks;active_nodes+=l.active_nodes;}
    for(int j=0;j<nn;j++)if(!he[j]&&hn[j].size>0){++valid;leaf_count+=hn[j].is_leaf;
        if(hn[j].pid>=0)refit_tasks+=hn[j].size;}
    size_t plan_entries=6*p.regions.size()+p.leaf_slot.size()+p.slot_pid.size()+p.leaves.size()+p.owners.size()+p.parents.size()+p.skeleton.size()+p.level_offsets.size()+p.skeleton_offsets.size();
    std::ofstream f(root/"meta.json");f<<"{\"schema\":1,\"pre\":"<<(pre?"true":"false")<<",\"rebuild\":"<<rebuild
        <<",\"step\":"<<current_step<<",\"last_rebuild_step\":"<<last_step<<",\"n\":"<<n<<",\"d\":"<<d
        <<",\"nn\":"<<nn<<",\"buffer\":"<<buffer<<",\"live\":"<<live.size()<<",\"epoch\":"<<target::bounds.epoch
        <<",\"insert_ids\":";json_ids(f,ins);f<<",\"delete_ids\":";json_ids(f,del);
    f<<",\"valid_nodes\":"<<valid<<",\"leaves\":"<<leaf_count<<",\"refit_distance_tasks\":"<<refit_tasks
        <<",\"plan_entries\":"<<plan_entries<<",\"build_distance_tasks\":"<<distance_tasks
        <<",\"build_active_split_nodes\":"<<active_nodes<<",\"build_created_children\":"<<active_nodes*10
        <<",\"sort_api_input_slots\":"<<size_t(n)*levels.size()<<",\"build_levels\":[";
    for(size_t j=0;j<levels.size();j++){auto l=levels[j];f<<(j?",":"")<<"{\"level\":"<<l.level<<",\"slots\":"<<l.slots<<",\"active_nodes\":"<<l.active_nodes<<",\"distance_tasks\":"<<l.distance_tasks<<'}';}
    f<<"]}\n";pe::require(bool(f),"RCA metadata write");
    if(pre){next_base.clear();for(int j=0;j<n;j++)if(!hd[j])next_base.push_back(base[j]);
        next_base.insert(next_base.end(),pending.begin(),pending.end());}
}
inline void pre(TN* nodes,int* empty,int* order,int nn,int n,int d,int* deleted,int* insertion,int buffer) {
    if(!enabled())return;++rebuild;levels.clear();
    snapshot(true,nodes,empty,order,nn,n,d,deleted,insertion,buffer);active=true;
}
inline void post(TN* nodes,int* empty,int* order,int nn,int n,int d,int* deleted,int* insertion,int buffer) {
    if(!enabled())return;base=next_base;pending.clear();
    snapshot(false,nodes,empty,order,nn,n,d,deleted,insertion,buffer);
    active=false;last_step=current_step;ins.clear();del.clear();
}
}
