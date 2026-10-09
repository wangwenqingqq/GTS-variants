#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace uk {
inline void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
inline size_t checked_product(size_t a,size_t b) {
    require(b==0||a<=std::numeric_limits<size_t>::max()/b,"byte product overflow");return a*b;
}
inline size_t data_bytes(int n,int d) {
    require(n>=0&&d>0,"negative shape");return checked_product(checked_product(size_t(n),size_t(d)),sizeof(float));
}
inline int tree_height(int n) {
    require(n>0,"tree physical size");int height=1;
    while(n>20){n-=9*(n/10);++height;}
    return std::max(3,height);
}
struct RankTree {
    std::vector<int> t;int live=0;
    void reset(int n){t.resize(size_t(n)+1);for(int i=1;i<=n;++i)t[i]=i&-i;live=n;}
    int erase(int rank) {
        require(rank>=0&&rank<live,"delete live rank");int p=0,bit=1;
        while(bit<=int(t.size())/2)bit*=2;
        for(;bit;bit/=2){int q=p+bit;if(q<int(t.size())&&t[q]<=rank){p=q;rank-=t[q];}}
        for(size_t q=size_t(p)+1;q<t.size();q+=q&-q)--t[q];--live;return p;
    }
};
struct Input {std::vector<float> data;std::vector<std::pair<int,int>> events;
    int queries=0,n=0,d=0,capacity=0;};
inline std::istringstream row(std::ifstream& f) {
    std::string s;require(bool(std::getline(f,s)),"truncated input");return std::istringstream(s);
}
inline void end(std::istringstream& s) {s>>std::ws;require(s.eof(),"extra or malformed input token");}
inline Input parse(const char* data_path,const char* event_path,int k,float radius) {
    require((k==8||k==32)&&std::isfinite(radius)&&radius>=0,"unsupported K/radius");
    Input x;std::ifstream f(data_path,std::ios::binary);require(bool(f),"cannot open data");
    int metric=0;std::string name=data_path;
    bool binary=name.size()>=7&&name.substr(name.size()-7)==".f32bin";
    if(binary){int32_t h[3];f.read(reinterpret_cast<char*>(h),sizeof(h));require(bool(f),"binary header");
        x.d=h[0];x.n=h[1];metric=h[2];}
    else {auto h=row(f);require(bool(h>>x.d>>x.n>>metric),"data header");end(h);}
    require((x.d==128||x.d==960)&&x.n>0&&x.n<=1000000&&metric==2,"requires D128/D960 N<=1M metric2");
    size_t bytes=data_bytes(x.n,x.d);
    if(binary){f.seekg(0,std::ios::end);require(f.tellg()==std::streamoff(bytes+12),"binary payload size");
        f.seekg(12);x.data.resize(bytes/sizeof(float));f.read(reinterpret_cast<char*>(x.data.data()),bytes);require(bool(f),"binary payload");}
    else {x.data.resize(bytes/sizeof(float));for(int i=0;i<x.n;i++){auto s=row(f);for(int j=0;j<x.d;j++)
        require(bool(s>>x.data[size_t(i)*x.d+j]),"coordinate token");end(s);}
        std::string extra;require(!std::getline(f,extra),"extra data row");}
    for(float v:x.data)require(std::isfinite(v),"nonfinite coordinate");
    std::ifstream e(event_path);require(bool(e),"cannot open events");auto h=row(e);int count=0;
    require(bool(h>>count),"event header");end(h);require(count>0&&count<=12000,"event count");
    RankTree alive;alive.reset(x.n);int physical=x.n,buffer=0,maximum=x.n;
    for(int step=0;step<count;++step){auto s=row(e);int flag=-1,index=-1;
        require(bool(s>>flag>>index),"event row");end(s);require(flag>=0&&flag<=3&&index>=0,"event flag/index");
        if(flag==1){require(index<alive.live+buffer,"delete live rank");
            if(index>=alive.live)--buffer;else alive.erase(index);}
        else {require(index<physical,"physical query/reinsertion index");
            if(flag==0){++buffer;maximum=std::max(maximum,physical+buffer);
                if(buffer==10){physical=alive.live+buffer;alive.reset(physical);buffer=0;}}
            else ++x.queries;}
        maximum=std::max(maximum,physical+buffer);require(maximum<=1001000,"physical plus buffer capacity bound");
        x.events.emplace_back(flag,index);}
    std::string extra;require(!std::getline(e,extra),"extra event row");require(x.queries>0&&x.queries<=10000,"query count");
    require(maximum<=std::numeric_limits<int>::max()-31,"rounded capacity overflow");
    x.capacity=(maximum+31)/32*32;data_bytes(x.capacity,x.d);return x;
}
}
