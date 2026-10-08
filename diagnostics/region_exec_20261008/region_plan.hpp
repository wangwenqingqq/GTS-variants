#pragma once
#include "region_types.hpp"
#include <algorithm>
#include <functional>
#include <stdexcept>
#include <vector>
namespace rex {
struct Plan {
    std::vector<Region> regions;
    std::vector<int> leaf_slot,slot_pid,leaves,owners,parents,skeleton;
    std::vector<int> level_offsets,skeleton_offsets;
    int total_leaves=0,nonempty_nodes=0,fallbacks=0;
};
inline void require(bool p,const char* msg) {if(!p) throw std::runtime_error(msg);}
// Pure CPU reference; invoked on paid D2H topology after every actual build.
inline Plan make_plan(const std::vector<Node>& nodes,const std::vector<int>& empty,
                      const std::vector<int>& order,int arity,
                      int object_budget=MAX_REGION_OBJECTS,int node_budget=MAX_REGION_NODES) {
    const int nn=nodes.size(),n=order.size(); Plan p;
    require(nn>0 && int(empty.size())==nn && arity>1,"invalid topology");
    auto live=[&](int i){return i<nn && !empty[i] && nodes[i].size>0;};
    require(live(0) && nodes[0].size==n && nodes[0].lid==0,"invalid root");
    std::vector<int> seen(n),position_seen(n),subnodes(nn),subleaves(nn),depth(nn),root_owner(nn,-1);
    p.leaf_slot.assign(nn,-1);p.owners.assign(n,-1);
    for(int id:order) {require(id>=0 && id<n && ++seen[id]==1,"invalid physical IDs");}
    for(int i=nn-1;i>=0;--i) if(live(i)) {
        const auto v=nodes[i]; ++p.nonempty_nodes;
        require(v.lid>=0 && v.size<=n-v.lid,"invalid object interval");
        if(i) {int par=(i-1)/arity; require(live(par) && !nodes[par].is_leaf,"orphan node");}
        subnodes[i]=1;
        if(v.is_leaf) subleaves[i]=1;
        else {
            int covered=0,next=v.lid;
            for(int k=1;k<=arity;k++) {
                int c=i*arity+k;
                if(!live(c))continue;
                require(nodes[c].lid==next,"children do not partition parent");
                next+=nodes[c].size;covered+=nodes[c].size;
                subnodes[i]+=subnodes[c];subleaves[i]+=subleaves[c];
            }
            require(covered==v.size,"internal subtree missing objects");
        }
    }
    for(int i=0;i<nn;i++) if(live(i)) {
        if(i) depth[i]=depth[(i-1)/arity]+1;
        if(nodes[i].is_leaf) {
            p.leaves.push_back(i);p.leaf_slot[i]=p.slot_pid.size();
            for(int j=0;j<nodes[i].size;j++) {
                int pos=nodes[i].lid+j;
                require(++position_seen[pos]==1,"overlapping canonical leaves");
                p.slot_pid.push_back(order[pos]);
            }
        }
    }
    require(int(p.slot_pid.size())==n && std::all_of(position_seen.begin(),position_seen.end(),[](int x){return x==1;}),"canonical coverage");
    std::function<void(int)> visit=[&](int i) {
        if(!live(i))return;
        auto v=nodes[i];
        if((v.size<=object_budget && subnodes[i]<=node_budget) || v.is_leaf) {
            int rid=p.regions.size(),fallback=v.size>object_budget || subnodes[i]>node_budget;
            p.regions.push_back({i,v.size,subnodes[i],subleaves[i],p.total_leaves,fallback});
            p.total_leaves+=subleaves[i];p.fallbacks+=fallback;root_owner[i]=rid;
            for(int j=0;j<v.size;j++) {int pos=v.lid+j; require(p.owners[pos]==-1,"overlapping regions");p.owners[pos]=rid;}
        } else for(int k=1;k<=arity;k++)visit(i*arity+k);
    }; visit(0);
    require(std::all_of(p.owners.begin(),p.owners.end(),[](int x){return x>=0;}),"region coverage");
    int md=*std::max_element(depth.begin(),depth.end());
    p.level_offsets.push_back(0);p.skeleton_offsets.push_back(0);
    for(int d=0;d<=md;d++) {
        for(int i=0;i<nn;i++) if(live(i) && depth[i]==d && !nodes[i].is_leaf) {
            p.parents.push_back(i);
            bool inside=false;
            for(int a=i;;a=(a-1)/arity) {if(root_owner[a]>=0){inside=true;break;}if(!a)break;}
            if(!inside)p.skeleton.push_back(i);
        }
        p.level_offsets.push_back(p.parents.size());p.skeleton_offsets.push_back(p.skeleton.size());
    }
    while(p.level_offsets.size()>1 && p.level_offsets.back()==p.level_offsets[p.level_offsets.size()-2])p.level_offsets.pop_back();
    while(p.skeleton_offsets.size()>1 && p.skeleton_offsets.back()==p.skeleton_offsets[p.skeleton_offsets.size()-2])p.skeleton_offsets.pop_back();
    return p;
}
}
