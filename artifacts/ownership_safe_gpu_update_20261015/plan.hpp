// Tail-provenance composition;no CUDA dependency and no N-sized per-batch scan.
#pragma once
#include <array>
#include <vector>
#include <map>
#include <algorithm>
#include <stdexcept>
#include <cstdint>
struct RowMove {int src,dst;};
static_assert(sizeof(RowMove)==8,"two32-bit row indices");
struct BatchPlan {
    int end=0,count=0;bool compose=true;
    std::array<int,512> tail;
    std::map<int,int> final_source;
    std::vector<RowMove> sequential,net;
    std::vector<int> levels;
    uint64_t RAW=0,WAW=0,WAR=0;
    explicit BatchPlan(int n,int b,bool materialize=true):end(n-b),count(b),compose(materialize){
        if(b<1||b>512||n<b)throw std::runtime_error("plan envelope");
        if(compose)for(int i=0;i<b;i++)tail[i]=end+i;
        sequential.reserve(b);if(compose)net.reserve(b);else levels.reserve(b);
    }
    void push(int src,int dst){
        if(src<end||src>=end+count||dst<0||dst>=src||(!sequential.empty()&&src>=sequential.back().src))throw std::runtime_error("monotone swap envelope");
        sequential.push_back({src,dst});if(!compose)return;int original=tail[src-end];
        if(dst>=end)tail[dst-end]=original;else final_source[dst]=original;
    }
    void finish(bool waves,bool count_edges=false){
        if(compose)for(int i=0;i<count;i++)if(tail[i]!=end+i)final_source[end+i]=tail[i];
        for(auto [dst,src]:final_source){
            if(src<end||src>=end+count||final_source.count(src))throw std::runtime_error("nonalias certificate failed");
            net.push_back({src,dst});
        }
        if(waves){
            std::map<int,int> writes,write_count;
            auto previous=[](const auto& m,int i){auto t=m.find(i);return t==m.end()?-1:t->second;};
            for(auto m:sequential){
                int level=1+std::max(previous(writes,m.src),previous(writes,m.dst));
                levels.push_back(level);if(count_edges){RAW+=write_count[m.src];WAW+=write_count[m.dst];++write_count[m.dst];}
                writes[m.dst]=level;
            }
        }
    }
};
