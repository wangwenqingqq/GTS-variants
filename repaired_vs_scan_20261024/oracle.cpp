// Independent CPU reference; no GTS/CUDA code or GPU arithmetic is reused.
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <thread>
#include <vector>
struct Hit { int id; double d; };
struct Data {
  int n=0,dim=0; bool words; std::vector<std::string> s; std::vector<float> x;
  Data(std::string kind,const char* path):words(kind=="words") {
    std::ifstream f(path,words?std::ios::in:std::ios::binary); assert(f);
    int metric;
    if(words) { f>>dim>>n>>metric; assert(metric==6);std::string line;std::getline(f,line);
      while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();assert(line.size()<=40);s.push_back(line);} assert(int(s.size())==n);
    } else {int h[3];f.read((char*)h,12);dim=h[0];n=h[1];assert(h[2]==2&&dim==2);x.resize(size_t(n)*dim);f.read((char*)x.data(),x.size()*4);assert(f);}
  }
  double distance(int a,int b) const {
    if(!words){double sum=0;for(int j=0;j<dim;++j){double d=double(x[size_t(a)*dim+j])-double(x[size_t(b)*dim+j]);sum+=d*d;}return std::sqrt(sum);}
    const auto& u=s[a];const auto& v=s[b];int tab[41][41];
    for(int i=0;i<=int(u.size());++i)tab[i][0]=i;
    for(int j=0;j<=int(v.size());++j)tab[0][j]=j;
    for(int i=1;i<=int(u.size());++i)for(int j=1;j<=int(v.size());++j)
      tab[i][j]=std::min({tab[i-1][j]+1,tab[i][j-1]+1,tab[i-1][j-1]+(u[i-1]!=v[j-1])});
    return tab[u.size()][v.size()];
  }
};
template<class T> void put(std::ofstream& f,const T& x){f.write((const char*)&x,sizeof(x));assert(f);}
int main(int argc,char**argv){
  assert(argc==6||argc==9);std::string mode=argv[1];Data d(argv[2],argv[3]);
  std::ifstream qf(argv[4]);int nq;qf>>nq;assert(nq>0&&nq<=1024);std::vector<int> qs(nq);for(int& q:qs){qf>>q;assert(q>=0&&q<d.n);}assert(qf);
  std::vector<std::vector<double>> cal(nq);std::vector<std::vector<Hit>> hits(nq);
  float rs[3]={};if(mode=="test"){assert(argc==9);for(int k=0;k<3;++k)rs[k]=std::stof(argv[6+k]);assert(rs[0]<=rs[1]&&rs[1]<=rs[2]);}
  std::atomic<int> next{0};std::vector<std::thread> threads;
  for(int t=0;t<4;++t)threads.emplace_back([&]{for(int qi;(qi=next++)<nq;){
    if(mode=="cal")cal[qi].resize(d.n);
    for(int id=0;id<d.n;++id){double z=d.distance(qs[qi],id);if(mode=="cal")cal[qi][id]=z;else if(z<=rs[2])hits[qi].push_back({id,z});}
    if(mode=="cal")std::sort(cal[qi].begin(),cal[qi].end());
    if(qi%32==0)std::cerr<<"CPU oracle "<<mode<<" "<<qi<<"/"<<nq<<"\n";
  }});
  for(auto& t:threads)t.join();std::ofstream out(argv[5],mode=="cal"?std::ios::out:std::ios::binary);assert(out);
  if(mode=="cal"){
    out.precision(17);out<<"{\"n\":"<<d.n<<",\"qids\":[";
    for(int qi=0;qi<nq;++qi){if(qi)out<<',';out<<qs[qi];}out<<"],\"kth\":[";
    for(int qi=0;qi<nq;++qi){if(qi)out<<',';out<<'['<<cal[qi][9]<<','<<cal[qi][99]<<','<<cal[qi][999]<<']';}out<<']';
    if(d.words){out<<",\"histograms\":[";for(int qi=0;qi<nq;++qi){if(qi)out<<',';out<<'[';for(int r=0;r<=40;++r){if(r)out<<',';out<<std::upper_bound(cal[qi].begin(),cal[qi].end(),r)-cal[qi].begin();}out<<']';}out<<']';}out<<"}\n";
  }else{
    put(out,d.n);put(out,nq);int nr=3;put(out,nr);for(float r:rs)put(out,r);
    for(int qi=0;qi<nq;++qi){put(out,qs[qi]);for(float r:rs){int count=std::count_if(hits[qi].begin(),hits[qi].end(),[&](Hit h){return h.d<=r;});put(out,count);for(auto h:hits[qi])if(h.d<=r){put(out,h.id);put(out,h.d);}}}
  }
  std::cout<<"PASS CPU "<<mode<<" n="<<d.n<<" Q="<<nq<<"\n";
}
