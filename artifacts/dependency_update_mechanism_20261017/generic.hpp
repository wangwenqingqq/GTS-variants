// Generic sparse copy propagation and overwritten-store elimination;no tail geometry.
#pragma once
#include "plan.hpp"
#include <unordered_map>
static std::vector<RowMove> generic_compile(const std::vector<RowMove>& commands){
    std::unordered_map<int,int> original;original.reserve(2*commands.size());
    for(auto m:commands){auto it=original.find(m.src);int value=it==original.end()?m.src:it->second;original[m.dst]=value;}
    std::vector<RowMove> out;out.reserve(original.size());
    for(auto [dst,src]:original)if(src!=dst)out.push_back({src,dst});
    std::sort(out.begin(),out.end(),[](auto a,auto b){return a.dst<b.dst;});return out;
}
