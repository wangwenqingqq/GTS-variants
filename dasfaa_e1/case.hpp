#pragma once
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using Clock=std::chrono::steady_clock;
inline double elapsed(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
inline void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
struct Event {int op,id,offset,qid,snapshot;};
struct Case {
 int metric,dim,nb,na,nq,k,ne;std::vector<float>x;std::vector<char>s;std::vector<Event>events;
 explicit Case(const char*path){std::ifstream f(path,std::ios::binary);require(bool(f),"open case");char magic[8];f.read(magic,8);require(bool(f),"truncated case magic");require(!memcmp(magic,"E1CASE1",8),"case magic");
  int h[7];f.read((char*)h,sizeof h);require(bool(f),"truncated case header");metric=h[0];dim=h[1];nb=h[2];na=h[3];nq=h[4];k=h[5];ne=h[6];
  require((metric==2||metric==6||metric==8)&&dim>0&&dim<=4096&&nb>=k&&na>=0&&nq>0&&ne>=0&&k>0&&k<=32,"case header");
  size_t corpus=size_t(nb)+size_t(na);
  require(corpus<=10000000,"case corpus exceeds mandatory 10M ceiling");
  require(metric==6||corpus+1<=size_t(INT32_MAX)/size_t(dim),"native int32 payload indexing limit");
  require(metric!=6||dim<=108,"edit payload width exceeds 108 bytes");
  size_t n=corpus+size_t(nq);require(n<100000000&&ne<100000000,"case bounds");
  if(metric==6){s.resize(n*109);f.read(s.data(),s.size());for(size_t i=0;i<n;++i)require(memchr(s.data()+i*109,0,109),"string length");}
  else{x.resize(n*dim);f.read((char*)x.data(),x.size()*4);for(float v:x)require(std::isfinite(v)&&(metric!=8||v==0||v==1),"payload value");}
  events.resize(ne);f.read((char*)events.data(),ne*sizeof(Event));require(bool(f),"truncated case");char extra;require(!f.read(&extra,1),"trailing case");
 }
 const float* xp(int id)const{return x.data()+size_t(id)*dim;}
 const char* sp(int id)const{return s.data()+size_t(id)*109;}
};
// Independent CPU Myers oracle is checked against full-row DP on random boundaries.
inline int edit_cpu(const char*a,const char*b){int n=strlen(a),m=strlen(b);int prev[109],curr[109];std::iota(prev,prev+m+1,0);
 for(int i=1;i<=n;++i){curr[0]=i;for(int j=1;j<=m;++j)curr[j]=std::min({prev[j]+1,curr[j-1]+1,prev[j-1]+(a[i-1]!=b[j-1])});std::copy(curr,curr+m+1,prev);}return prev[m];}
inline int edit_myers(const char* a,const char*b){int m=strlen(a);if(!m)return strlen(b);__uint128_t peq[256]={};
 for(int i=0;i<m;++i)peq[(unsigned char)a[i]]|=__uint128_t(1)<<i;
 __uint128_t vp=~__uint128_t(0),vn=0,high=__uint128_t(1)<<(m-1);int score=m;
 for(;*b;++b){auto eq=peq[(unsigned char)*b],xv=eq|vn,xh=(((eq&vp)+vp)^vp)|eq,ph=vn|~(xh|vp),mh=vp&xh;
 score+=bool(ph&high)-bool(mh&high);ph=(ph<<1)|1;mh<<=1;vp=mh|~(xv|ph);vn=ph&xv;}return score;}
inline double cpu_distance(const Case&c,int a,int b){if(c.metric==6)return edit_myers(c.sp(a),c.sp(b));
 double total=0;unsigned inter=0,un=0;for(int j=0;j<c.dim;++j){if(c.metric==2){double d=double(c.xp(a)[j])-c.xp(b)[j];total+=d*d;}else{bool x=c.xp(a)[j]!=0,y=c.xp(b)[j]!=0;inter+=x&&y;un+=x||y;}}
 return c.metric==2?std::sqrt(total):(un?1.-double(inter)/un:0.);}
inline void oracle_selftest(){uint32_t state=234343;auto rnd=[&](){state^=state<<13;state^=state>>17;state^=state<<5;return state;};
 for(int it=0;it<2000;++it){std::string a(rnd()%109,' '),b(rnd()%109,' ');for(auto&x:a)x='a'+rnd()%9;for(auto&x:b)x='a'+rnd()%9;require(edit_cpu(a.c_str(),b.c_str())==edit_myers(a.c_str(),b.c_str()),"CPU edit oracle selftest");}}
