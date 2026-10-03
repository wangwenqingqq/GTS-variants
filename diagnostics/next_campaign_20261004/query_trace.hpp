#pragma once
#include <sys/resource.h>
#include <unistd.h>
#include <fstream>
#include <vector>
#include <chrono>
#include <iomanip>
#include <stdexcept>

// Coarse snapshots only, after complete Host-ready batch boundaries.
struct QueryTrace {
    struct Point {int q;double wall,cpu;size_t device;long rss;};
    std::string out;std::vector<Point> points;
    std::chrono::steady_clock::time_point start;double cpu_start=0;int next=1000;
    explicit QueryTrace(std::string p):out(std::move(p)){}
    static double cpu(){rusage r{};getrusage(RUSAGE_SELF,&r);return r.ru_utime.tv_sec+r.ru_utime.tv_usec*1e-6+r.ru_stime.tv_sec+r.ru_stime.tv_usec*1e-6;}
    Point point(int q) {
        size_t free,total;if(cudaMemGetInfo(&free,&total)!=cudaSuccess)throw std::runtime_error("trace mem info");
        std::ifstream stat("/proc/self/statm");long size,rss;stat>>size>>rss;
        return {q,std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count(),cpu()-cpu_start,total-free,rss*sysconf(_SC_PAGESIZE)};
    }
    void begin(){cpu_start=cpu();start=std::chrono::steady_clock::now();points.push_back(point(0));start=std::chrono::steady_clock::now();cpu_start=cpu();}
    void sample(int q,int total){if(q>=next||q==total){points.push_back(point(q));next=((q/1000)+1)*1000;}}
    void finish(double total_ms){
        double query_cpu=cpu()-cpu_start;
        std::ofstream f(out+".windows.csv");f<<"processed,wall_s,cpu_s,device_used_bytes,rss_bytes\n"<<std::setprecision(12);
        for(auto p:points)f<<p.q<<","<<p.wall<<","<<p.cpu<<","<<p.device<<","<<p.rss<<"\n";
        std::ofstream j(out+".cpu.json");j<<std::setprecision(12)<<"{\"query_cpu_s\":"<<query_cpu<<",\"query_wall_s\":"<<total_ms/1000<<",\"busy_core_equivalents\":"<<query_cpu/(total_ms/1000)<<",\"scope\":\"all-thread CPU delta in warm query pass\",\"window_hook\":\"one post-delivery snapshot near each 1k boundary; included in timer\"}\n";
    }
};
