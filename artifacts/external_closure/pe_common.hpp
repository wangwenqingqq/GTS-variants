#pragma once
// Immutable Host-ready requests. Initial IDs and every inserted occurrence are distinct.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace pe {
inline void require(bool p,const char* s){if(!p)throw std::runtime_error(s);}
struct Trace {
    int n=0,d=0;std::vector<int> flags,occ;std::vector<float> vectors;
    void load(const std::string& p) {
        std::ifstream f(p+".logical");int count=0;f>>count>>n>>d;
        require(bool(f)&&count>0&&count<=12000&&n>=0&&n<=1000000&&(d==128||d==960),"logical header");
        flags.resize(count);occ.resize(count);
        for(int i=0;i<count;i++){f>>flags[i]>>occ[i];require(bool(f)&&flags[i]>=0&&flags[i]<=3,"logical event");}
        std::string extra;require(!(f>>extra),"trailing logical data");
        std::ifstream v(p+".vectors.f32",std::ios::binary);vectors.resize(size_t(count)*d);
        v.read((char*)vectors.data(),vectors.size()*4);require(bool(v)&&v.peek()==EOF,"vector request bytes");
        for(float x:vectors)require(std::isfinite(x),"nonfinite request");
        std::vector<bool> live(n+count,false);std::fill(live.begin(),live.begin()+n,true);int next=n;
        for(int i=0;i<count;i++) {
            if(flags[i]==0){require(occ[i]==next,"insert occurrence sequence");live[next++]=true;}
            else if(flags[i]==1){require(occ[i]>=0&&occ[i]<next&&live[occ[i]],"invalid deleted occurrence");live[occ[i]]=false;}
            else require(occ[i]==-1,"query occurrence token");
        }
    }
    const float* vector(int i)const{return vectors.data()+size_t(i)*d;}
};
// P emits stable live rank, not physical row. A Fenwick map avoids whole-N reindexing per update.
struct Ranks {
    std::vector<int> tree;std::vector<unsigned char> alive;int next=0,total=0;
    int sum(int end)const{int v=0;for(int i=end;i;i-=i&-i)v+=tree[i];return v;}
    void add(int id,int delta){for(size_t i=size_t(id)+1;i<tree.size();i+=i&-i)tree[i]+=delta;total+=delta;}
    void init(int n,int events){tree.assign(n+events+1,0);alive.assign(n+events,0);next=n;total=0;
        for(int i=0;i<n;i++){alive[i]=1;tree[i+1]=1;}for(size_t i=1;i<tree.size();i++){size_t j=i+(i&-i);if(j<tree.size())tree[j]+=tree[i];}total=n;}
    void insert(int id){require(id==next&&id<int(alive.size()),"insert ID map");alive[id]=1;add(id,1);next++;}
    int erase(int id){require(id>=0&&id<next&&alive[id],"delete ID map");int rank=sum(id);alive[id]=0;add(id,-1);return rank;}
    int select(int rank)const {
        require(rank>=0&&rank<total,"result live rank");int p=0,bit=1;while(bit<int(tree.size()))bit<<=1;
        for(;bit;bit>>=1){int q=p+bit;if(q<int(tree.size())&&tree[q]<=rank){p=q;rank-=tree[q];}}return p;
    }
    std::vector<int> final()const{std::vector<int> ids;ids.reserve(total);for(int i=0;i<next;i++)if(alive[i])ids.push_back(i);return ids;}
    void release(){std::vector<int>().swap(tree);std::vector<unsigned char>().swap(alive);}
};
}
