#pragma once
#include <unistd.h>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>
using WallClock=std::chrono::steady_clock;
inline double millis(WallClock::time_point t){return std::chrono::duration<double,std::milli>(WallClock::now()-t).count();}
struct Hit {int id;float d;};
static_assert(sizeof(Hit)==8);
struct Reference {int id;double d;};
struct Case {
 int n=0,nq=0,k=0;float radius=0;std::vector<int> qs;std::vector<std::vector<Reference>> expected;
 template<class T> static T get(std::ifstream& f){T x;f.read((char*)&x,sizeof(x));assert(f);return x;}
 Case(const char* path,int q,int target):nq(q),k(target){
  std::ifstream f(path,std::ios::binary);assert(f);n=get<int>(f);int total=get<int>(f),nr=get<int>(f);assert(q>0&&q<=total&&nr==3&&k>=0&&k<3);
  float rs[3];for(auto& r:rs)r=get<float>(f);radius=rs[k];expected.resize(q);qs.resize(q);
  for(int qi=0;qi<q;++qi){qs[qi]=get<int>(f);assert(qs[qi]>=0&&qs[qi]<n);for(int j=0;j<3;++j){int count=get<int>(f);assert(count>=0&&count<=n);if(j!=k){f.seekg(size_t(count)*12,std::ios::cur);assert(f);}else{auto& v=expected[qi];v.resize(count);for(auto& h:v){h.id=get<int>(f);h.d=get<double>(f);}}}}
 }
};
using Outputs=std::vector<std::vector<Hit>>;
inline void canonicalize(Outputs& out){for(auto& v:out)if(!std::is_sorted(v.begin(),v.end(),[](Hit a,Hit b){return a.id<b.id;}))std::sort(v.begin(),v.end(),[](Hit a,Hit b){return a.id<b.id;});}
inline void check(const Outputs& out,const Case& c){
 assert(int(out.size())==c.nq);
 for(int qi=0;qi<c.nq;++qi){const auto& a=out[qi];const auto& e=c.expected[qi];if(a.size()!=e.size()){std::cerr<<"COUNT mismatch q="<<qi<<" got="<<a.size()<<" want="<<e.size()<<'\n';std::exit(20);}for(size_t i=0;i<a.size();++i)if(a[i].id!=e[i].id||!std::isfinite(a[i].d)||std::abs(double(a[i].d)-e[i].d)>4e-6+4e-6*std::abs(e[i].d)){std::cerr<<"OUTPUT mismatch q="<<qi<<" index="<<i<<" got="<<a[i].id<<':'<<std::setprecision(17)<<a[i].d<<" want="<<e[i].id<<':'<<e[i].d<<'\n';std::exit(21);}}
}
inline void dump_output(const std::string& p,const Outputs& out){std::ofstream f(p,std::ios::binary);assert(f);for(auto& v:out){int count=v.size();f.write((char*)&count,4);f.write((char*)v.data(),size_t(count)*8);}assert(f);}
struct RunLog {
 std::ofstream samples;std::string prefix;double build=0,setup=0,capture=0,first=0,warm=0;
 RunLog(std::string p):samples(p+".csv"),prefix(p){assert(samples);samples<<"iteration,batch_ms\n"<<std::setprecision(12);}
 void finish(const std::string& arm,const Case& c){std::ofstream f(prefix+".json");f<<std::setprecision(12)<<"{\"arm\":\""<<arm<<"\",\"n\":"<<c.n<<",\"Q\":"<<c.nq<<",\"radius\":"<<c.radius<<",\"build_ms\":"<<build<<",\"setup_ms\":"<<setup<<",\"capture_ms\":"<<capture<<",\"first_ms\":"<<first<<",\"warmup_ms\":"<<warm<<",\"correct\":true}\n";}
};
template<class Call> void run_case(Call call,const Case& c,RunLog& log,int reps,int warm,bool dump){
 auto t=WallClock::now();auto first=call(dump);log.first=millis(t);check(first,c);
 t=WallClock::now();for(int i=0;i<warm;++i){auto out=call(false);check(out,c);}log.warm=millis(t);
 for(int i=0;i<reps;++i){t=WallClock::now();auto out=call(false);double ms=millis(t);check(out,c);log.samples<<i<<','<<ms<<'\n';log.samples.flush();}
}
