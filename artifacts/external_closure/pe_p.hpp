#pragma once
#include "pe_common.hpp"
namespace pe {
inline Trace measured,warmup;inline const Trace* trace=nullptr;inline Ranks ranks;
inline std::vector<int> final_ids;inline size_t upload_bytes=0;inline int original_index=0;
inline void load(){const char* p=std::getenv("PE_TRACE");require(p,"PE_TRACE required");measured.load(p);warmup.load(std::string(p)+".warmup");}
inline void begin(bool warm,int n,int d,int count) {
    trace=warm?&warmup:&measured;require(trace->n==n&&trace->d==d&&int(trace->flags.size())==count,"P trace shape");
    ranks.init(n,count);final_ids.clear();upload_bytes=0;
}
inline void submit(int step,int flag,float* data,int n,int buffer,const int* insertion,int& index) {
    require(trace->flags.at(step)==flag,"P event flag");original_index=index;
    if(flag==1){index=ranks.erase(trace->occ[step]);require(index==original_index,"P replay delete rank differs");return;}
    int slot=10;
    if(flag==0){
        for(slot=0;slot<10;slot++){bool used=false;for(int b=0;b<buffer;b++)used|=insertion[b]==n+slot;if(!used)break;}
        require(slot<10,"P insertion request slots");ranks.insert(trace->occ[step]);
    }
    index=n+slot;u10_ck(cudaMemcpy(data+size_t(index)*trace->d,trace->vector(step),size_t(trace->d)*4,cudaMemcpyHostToDevice));upload_bytes+=size_t(trace->d)*4;
}
inline void delivered() {
    const auto& q=u10.queries.back();for(size_t j=q.offset;j<q.offset+q.count;j++)if(u10.ids[j]>=0)u10.ids[j]=ranks.select(u10.ids[j]);
}
inline void finish(){final_ids=ranks.final();ranks.release();}
inline void write(const std::string& out){
    u10.write_vector(out+".final.i32",final_ids,final_ids.size());
    std::ofstream f(out+".pe.json");f<<"{\"method\":\"P\",\"host_vector_upload_bytes\":"<<upload_bytes<<",\"extra_nonindexed_rows\":11,\"final_live\":"<<final_ids.size()<<"}\n";require(bool(f),"P PE receipt");
}
}
