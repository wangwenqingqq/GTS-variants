#pragma once
// Host observation only. Full IDs/fields and ACK fences are identical with
// U10_OBSERVE=0/1; optional timing/NVTX/memory snapshots are the paired control.
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>
#include <cuda_runtime.h>
#include <nvtx3/nvToolsExt.h>
using U10Clock = std::chrono::steady_clock;
inline double u10_ms(U10Clock::time_point t) {
    return std::chrono::duration<double,std::milli>(U10Clock::now()-t).count();
}
inline void u10_ck(cudaError_t e) {
    if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e));
}
inline bool u10_env(const char* name) {
    const char* v=std::getenv(name); return v && std::string(v)=="1";
}
struct U10Query {int step,qid,base,buffer,count; size_t offset;};
struct U10Operation {int step,flag,base_before,buffer_before,base_after,buffer_after; double ack_ms,rebuild_ms;};
struct U10Trace {
    bool observe=!std::getenv("U10_OBSERVE") || u10_env("U10_OBSERVE");
    bool tree_audit=u10_env("U10_TREE_AUDIT");
    std::vector<int> ids;
    std::vector<float> fields;
    std::vector<U10Query> queries;
    std::vector<U10Operation> operations;
    const char* names[8]={"query.tree","query.buffer","query.prefix_merge","delete.prefix_lookup",
                         "delete.buffer_merge","rebuild.compaction","rebuild.construct","rebuild.reset"};
    size_t calls[8]={}, offset=0, memory_peak=0;
    double stage_ms[8]={}, load_ms=0, buffer_setup_ms=0, cold_build_ms=0, trace_ms=0, drain_ms=0;
    U10Clock::time_point trace_start,op_start,rebuild_start;
    rusage cpu_begin{},cpu_end{};
    U10Operation current{};
    void initialize(int n,int q,int events) {
        auto start=U10Clock::now();
        if(n!=1000 || q!=10000 || events!=12000) throw std::runtime_error("outside registered U10 trace");
        ids.resize(size_t(q)*(n+10)); fields.resize(ids.size());
        queries.reserve(q); operations.reserve(events); buffer_setup_ms=u10_ms(start);
    }
    void memory_sample() {
        size_t free,total;u10_ck(cudaMemGetInfo(&free,&total));
        if(total-free>memory_peak)memory_peak=total-free;
    }
    void begin() {
        u10_ck(cudaDeviceSynchronize());getrusage(RUSAGE_SELF,&cpu_begin);
        if(observe){memory_sample();nvtxRangePushA("native.trace");}
        trace_start=U10Clock::now();
    }
    void begin_op(int step,int flag,int base,int buffer) {
        if(!observe)return;
        current={step,flag,base,buffer,0,0,0,0};
        nvtxRangePushA(flag==0?"native.insert":flag==1?"native.delete":"native.query");
        op_start=U10Clock::now();
    }
    void begin_rebuild() {if(observe){rebuild_start=U10Clock::now();nvtxRangePushA("native.rebuild");}}
    void end_rebuild() {if(observe){current.rebuild_ms=u10_ms(rebuild_start);nvtxRangePop();memory_sample();}}
    void end_op(int base,int buffer) {
        // Serialized visibility and full-output delivery before the next event.
        u10_ck(cudaDeviceSynchronize());
        if(!observe)return;
        current.ack_ms=u10_ms(op_start);current.base_after=base;current.buffer_after=buffer;
        operations.push_back(current);nvtxRangePop();
    }
    void deliver(int step,int qid,int base,int buffer,int count,const int* src,const float* dist) {
        if(count<0 || size_t(count)>ids.size()-offset)throw std::runtime_error("full-output buffer capacity");
        if(count){
            u10_ck(cudaMemcpy(ids.data()+offset,src,size_t(count)*sizeof(int),cudaMemcpyDeviceToHost));
            u10_ck(cudaMemcpy(fields.data()+offset,dist,size_t(count)*sizeof(float),cudaMemcpyDeviceToHost));
        }
        queries.push_back({step,qid,base,buffer,count,offset});offset+=count;
        if(observe && queries.size()%1000==0)memory_sample();
    }
    void finish() {
        u10_ck(cudaDeviceSynchronize());trace_ms=u10_ms(trace_start);
        if(observe){nvtxRangePop();memory_sample();}getrusage(RUSAGE_SELF,&cpu_end);
    }
    template<class T> void write_vector(const std::string& path,const std::vector<T>& v,size_t count) {
        std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<const char*>(v.data()),count*sizeof(T));
        if(!out)throw std::runtime_error("write full output");
    }
    void write(const std::string& out) {
        if(queries.size()!=10000 || (observe && operations.size()!=12000))throw std::runtime_error("incomplete trace");
        write_vector(out+".ids.i32",ids,offset);write_vector(out+".dist.f32",fields,offset);
        std::ofstream q(out+".queries.csv");q<<"step,qid,tree_size,buffer,count,offset\n";
        for(auto r:queries)q<<r.step<<','<<r.qid<<','<<r.base<<','<<r.buffer<<','<<r.count<<','<<r.offset<<'\n';
        std::ofstream op(out+".ops.csv");op<<std::setprecision(17)<<"step,flag,base_before,buffer_before,base_after,buffer_after,ack_ms,rebuild_ms\n";
        for(auto r:operations)op<<r.step<<','<<r.flag<<','<<r.base_before<<','<<r.buffer_before<<','<<r.base_after<<','<<r.buffer_after<<','<<r.ack_ms<<','<<r.rebuild_ms<<'\n';
        auto seconds=[](timeval v){return v.tv_sec+v.tv_usec/1e6;};
        std::ofstream s(out+".summary.json");s<<std::setprecision(17)
          <<"{\"observe\":"<<(observe?"true":"false")<<",\"tree_audit\":"<<(tree_audit?"true":"false")
          <<",\"load_ms\":"<<load_ms<<",\"buffer_setup_ms\":"<<buffer_setup_ms<<",\"cold_build_ms\":"<<cold_build_ms
          <<",\"trace_ms\":"<<trace_ms<<",\"final_drain_ms\":"<<drain_ms<<",\"results\":"<<offset
          <<",\"sampled_device_peak_bytes\":"<<memory_peak<<",\"host_output_capacity_bytes\":"<<ids.size()*8
          <<",\"cpu_user_s\":"<<seconds(cpu_end.ru_utime)-seconds(cpu_begin.ru_utime)
          <<",\"cpu_system_s\":"<<seconds(cpu_end.ru_stime)-seconds(cpu_begin.ru_stime)<<",\"stages\":[";
        for(int i=0;i<8;++i)s<<(i?",":"")<<"{\"name\":\""<<names[i]<<"\",\"calls\":"<<calls[i]<<",\"inclusive_host_ms\":"<<stage_ms[i]<<'}';
        s<<"]}\n";if(!q || !op || !s)throw std::runtime_error("write ledger");
    }
};
static U10Trace u10;
struct U10Stage {
    int index;U10Clock::time_point start;
    explicit U10Stage(int i):index(i){if(u10.observe){nvtxRangePushA(u10.names[i]);start=U10Clock::now();}}
    ~U10Stage(){if(u10.observe){u10.stage_ms[index]+=u10_ms(start);++u10.calls[index];nvtxRangePop();}}
};
