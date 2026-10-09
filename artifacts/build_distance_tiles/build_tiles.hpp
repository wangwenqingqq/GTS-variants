#pragma once
// The legacy config maps `short` to float. Do not leak it into standard headers.
#pragma push_macro("short")
#undef short
#include <filesystem>
#include <fstream>
#include <cstring>
#include <chrono>
#include <iomanip>
#include <limits>
#pragma pop_macro("short")
namespace bt {
static bool tiled=false,auditing=false;
static std::string root,folder;
static int builds=0,n=0,nn=0,layer=0,slots=0,start=0;
static std::vector<int> before_flags,before_empty;
static U10Clock::time_point scoring_begin;
inline void configure() {
    const char* v=std::getenv("BUILD_MAPPING");std::string mode=v?v:"NODE";
    uk::require(mode=="NODE"||mode=="TILED","unknown build mapping");tiled=mode=="TILED";
    const char* path=std::getenv("BUILD_AUDIT_DIR");auditing=path&&*path;
    if(auditing){root=path;uk::require(std::filesystem::is_directory(root),"missing private audit directory");}
}
inline int size_bound(int count,int depth) {
    uk::require(count>0&&depth>=0,"build geometry input");
    for(int i=0;i<depth;++i)count=count/10+9;
    return count;
}
inline int tiles(int count,int depth) {return (size_bound(count,depth)+511)/512;}
inline int grid(int nodes,int width) {
    int64_t product=int64_t(nodes)*width;
    uk::require(nodes>0&&width>0&&product<=std::numeric_limits<int>::max(),"tile grid overflow");
    return int(product);
}
template<class T> inline std::vector<T> copy(const T* source,size_t count) {
    std::vector<T> result(count);if(count)u10_ck(cudaMemcpy(result.data(),source,count*sizeof(T),cudaMemcpyDeviceToHost));return result;
}
template<class T> inline void dump(const std::string& name,const std::vector<T>& values) {
    std::string path=folder+"/"+name;uk::require(!std::filesystem::exists(path),"audit output already exists");
    std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(values.data()),values.size()*sizeof(T));
    uk::require(bool(f),"write complete build audit");
}
inline std::string label(const std::string& suffix) {return "level"+std::to_string(layer)+"."+suffix;}
inline void state(const std::string& name,const TN* nodes,const int* empty,const int* flags) {
    auto hn=copy(nodes,nn);auto he=copy(empty,nn);auto hs=copy(flags,nn);
    // Undefined empty-node storage is not part of the semantic state.
    for(int i=0;i<nn;++i)if(he[i])std::memset(&hn[i],0,sizeof(TN));
    dump(name+".nodes",hn);dump(name+".empty",he);dump(name+".split",hs);
}
inline void begin(int count,int dimension,int nodes) {
    ++builds;if(!auditing)return;n=count;nn=nodes;
    folder=root+"/build"+std::to_string(builds-1);
    uk::require(std::filesystem::create_directory(folder),"audit build already exists");
    std::ofstream f(folder+"/META.json");f<<"{\"n\":"<<n<<",\"d\":"<<dimension<<",\"nn\":"<<nn
      <<",\"mode\":\""<<(tiled?"TILED":"NODE")<<"\"}\n";uk::require(bool(f),"audit meta");
}
inline void before(int depth,int node_slots,int first,const TN* nodes,const int* empty,const int* flags,const int* order) {
    if(!auditing)return;layer=depth;slots=node_slots;start=first;
    state(label("input"),nodes,empty,flags);dump(label("input.order"),copy(order,n));
    before_flags=copy(flags,nn);before_empty=copy(empty,nn);auto hn=copy(nodes,nn);
    for(int s=0;s<slots;++s)if(!before_empty[start+s])
        uk::require(hn[start+s].size<=size_bound(n,depth),"tile node bound violated");
    std::ofstream f(folder+"/"+label("GEOMETRY.json"));f<<"{\"slots\":"<<slots<<",\"start\":"<<start
      <<",\"upper\":"<<size_bound(n,depth)<<",\"tiles\":"<<(tiled?tiles(n,depth):1)
      <<",\"grid\":"<<(tiled?grid(slots,tiles(n,depth)):slots)<<",\"threads\":512}\n";
    uk::require(bool(f),"geometry audit");scoring_begin=U10Clock::now();
}
inline void distance(const double* keys,const int* pivots) {
    if(!auditing)return;double elapsed=u10_ms(scoring_begin);
    dump(label("distance.keys"),copy(keys,n));auto p=copy(pivots,nn);
    for(int i=0;i<nn;++i)if(i<start||i>=start+slots||!before_flags[i])p[i]=std::numeric_limits<int>::min();
    dump(label("distance.pids"),p);
    std::ofstream f(folder+"/"+label("DISTANCE_DIAGNOSTIC.json"));f<<std::setprecision(17)<<"{\"launch_through_existing_fence_ms\":"<<elapsed
       <<",\"scope\":\"audited diagnostic only; not primary/kernel-event speed\"}\n";uk::require(bool(f),"distance diagnostic");
}
inline void sorted(const double* keys,const int* order) {
    if(auditing){dump(label("sorted.keys"),copy(keys,n));dump(label("sorted.order"),copy(order,n));}
}
inline void split(const TN* nodes,const int* empty,const int* flags) {
    if(auditing)state(label("after_split"),nodes,empty,flags);
}
inline void refit(const double* lo,const double* hi,const int* empty,int nodes) {
    if(!auditing)return;uk::require(nodes==nn,"refit/build mismatch");
    auto lower=copy(lo,nn),upper=copy(hi,nn);auto he=copy(empty,nn);
    for(int i=0;i<nn;++i)if(he[i])lower[i]=upper[i]=0;
    dump("refit.lo",lower);dump("refit.hi",upper);dump("refit.empty",he);
}
inline void write(const std::string& output) {
    std::ofstream f(output+".build_tiles.json");f<<"{\"mode\":\""<<(tiled?"TILED":"NODE")
      <<"\",\"audit\":"<<(auditing?"true":"false")<<",\"build_calls\":"<<builds<<",\"new_owned_GPU_bytes\":0}\n";
    uk::require(bool(f),"build mapping receipt");
}
}
