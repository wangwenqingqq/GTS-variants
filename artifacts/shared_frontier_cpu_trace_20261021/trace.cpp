// CPU-only structural reimplementations. Not a native CUDA/JZ execution trace.
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>
#ifdef NDEBUG
#error Assertions are mandatory
#endif
using namespace std;
using Clock=chrono::steady_clock;
double elapsed(Clock::time_point t){return chrono::duration<double>(Clock::now()-t).count();}
template<class U> int myers(const string&a,const string&b){
 if(a.empty())return b.size();assert(a.size()<=sizeof(U)*8);
 array<U,256>eq{};for(size_t i=0;i<a.size();++i)eq[(unsigned char)a[i]]|=U(1)<<i;
 U pv=~U(0),mv=0,top=U(1)<<(a.size()-1);int score=a.size();
 for(unsigned char c:b){U e=eq[c],xv=e|mv,xh=(((e&pv)+pv)^pv)|e,ph=mv|~(xh|pv),mh=pv&xh;
  if(ph&top)++score;if(mh&top)--score;ph=(ph<<1)|1;mh<<=1;pv=mh|~(xv|ph);mv=ph&xv;}
 return score;
}
int edit(const string&a,const string&b){return a.size()<=64?myers<uint64_t>(a,b):myers<__uint128_t>(a,b);}
int dp(const string&a,const string&b){vector<int>x(b.size()+1),y(x.size());iota(x.begin(),x.end(),0);for(size_t i=1;i<=a.size();++i){y[0]=i;for(size_t j=1;j<=b.size();++j)y[j]=min({x[j]+1,y[j-1]+1,x[j-1]+int(a[i-1]!=b[j-1])});x.swap(y);}return x.back();}
struct Record{uint64_t source;string s;double x=0,y=0;};
struct Counts{
 uint64_t bounds=0,verify=0,partition=0,plan=0,visits=0,candidates=0,frontier=0,allocated=0,logical=0,scratch=0;
 uint64_t calls()const{return bounds+verify+partition+plan;}
};
struct Value{double distance,score;};
struct Metric{
 const vector<Record>&x;bool strings;Counts*c=nullptr;int role=0;
 Value eval(int a,int b){if(c){if(role==0)++c->bounds;else if(role==1)++c->verify;else if(role==2)++c->partition;else ++c->plan;}
  if(strings){double v=edit(x[a].s,x[b].s);return {v,v};}
  double dx=x[a].x-x[b].x,dy=x[a].y-x[b].y;double score=dx*dx+dy*dy;return {sqrt(score),score};}
 double lower(double d)const{return strings?d:max(0.0,nextafter(d*(1-64*numeric_limits<double>::epsilon()),-INFINITY));}
 double upper(double d)const{return strings?d:nextafter(d/(1-64*numeric_limits<double>::epsilon()),INFINITY);}
 double ru(double r)const{return upper(r);}
 bool hit(Value v,double r)const{return v.score<=(strings?r:r*r);}
};
struct Node{int parent=-1,pivot=-1,begin=0,count=0;double lo=0,hi=INFINITY;vector<int>kids;};
struct Tree{
 vector<Node>nodes;vector<int>perm;uint64_t build_calls=0;double seconds=0;
 uint64_t bytes()const{uint64_t z=nodes.capacity()*sizeof(Node)+perm.capacity()*sizeof(int);for(auto&n:nodes)z+=n.kids.capacity()*sizeof(int);return z;}
};
Tree build_gts(Metric m,const vector<int>&input){
 auto t=Clock::now();Counts count;m.c=&count;m.role=3;Tree tr;
 auto build=[&](auto&&self,vector<int>ids,int parent,double lo,double hi)->int{
  int index=tr.nodes.size();tr.nodes.emplace_back();tr.nodes[index].parent=parent;tr.nodes[index].begin=tr.perm.size();tr.nodes[index].count=ids.size();tr.nodes[index].lo=lo;tr.nodes[index].hi=hi;
  if(ids.size()<=20){tr.perm.insert(tr.perm.end(),ids.begin(),ids.end());return index;}
  int pivot=ids[(ids.size()-1)/2];tr.nodes[index].pivot=pivot;vector<pair<double,int>>order;order.reserve(ids.size());
  for(int id:ids)order.emplace_back(m.eval(pivot,id).distance,id);
  sort(order.begin(),order.end());int step=ids.size()/10;
  for(int k=0;k<10;++k){int a=k*step,b=k==9?ids.size():(k+1)*step;assert(a<b);
   // The released splitter recomputes each child lower-bound distance.
   double child_lo=m.eval(pivot,order[a].second).distance;double child_hi=k==9?INFINITY:order[b].first;
   vector<int>part;for(int i=a;i<b;++i)part.push_back(order[i].second);
   int child=self(self,std::move(part),index,child_lo,child_hi);tr.nodes[index].kids.push_back(child);}
  return index;
 };build(build,input,-1,0,INFINITY);tr.build_calls=count.calls();tr.seconds=elapsed(t);assert(tr.perm.size()==input.size());
 for(auto&n:tr.nodes){assert(n.count>0);if(!n.kids.empty()){int sum=0;for(int i:n.kids){assert(tr.nodes[i].parent==&n-tr.nodes.data());sum+=tr.nodes[i].count;}assert(sum==n.count);}}
 return tr;
}
struct QNode{int center=0,begin=0,count=0,left=-1,right=-1;double radius=0;};
struct QTree{vector<QNode>nodes;vector<int>perm;uint64_t bytes()const{return nodes.capacity()*sizeof(QNode)+perm.capacity()*4;}};
QTree build_queries(Metric m,const vector<int>&q,Counts&c){
 QTree tr;m.c=&c;m.role=3;
 auto build=[&](auto&&self,vector<int>ids)->int{
  int index=tr.nodes.size();tr.nodes.emplace_back();int center=ids[(ids.size()-1)/2];tr.nodes[index].center=center;tr.nodes[index].count=ids.size();tr.nodes[index].begin=tr.perm.size();
  if(ids.size()==1){tr.perm.push_back(ids[0]);return index;}
  vector<pair<double,int>>order;for(int i:ids)order.emplace_back(m.eval(q[center],q[i]).distance,i);
  sort(order.begin(),order.end());tr.nodes[index].radius=m.upper(order.back().first);
  vector<int>a,b;for(size_t i=0;i<order.size();++i)(i<order.size()/2?a:b).push_back(order[i].second);
  int l=self(self,std::move(a)),r=self(self,std::move(b));tr.nodes[index].left=l;tr.nodes[index].right=r;return index;
 };vector<int>ids(q.size());iota(ids.begin(),ids.end(),0);build(build,ids);return tr;
}
struct Task{int q,d;};
using Hit=tuple<int,uint64_t,double>;
struct Run{Counts c;vector<Hit>hits;uint64_t query_bytes=0,index_bytes=0,index_calls=0,index_nodes=0;double seconds=0,index_seconds=0;};
void accept(Run&r,Metric&m,int qi,int id,const vector<int>&q,double radius){++r.c.candidates;m.role=1;auto v=m.eval(q[qi],id);if(m.hit(v,radius))r.hits.emplace_back(qi,m.x[id].source,v.score);}
bool shell(Metric&m,const Node&n,double d,double R,double radius){
 double low=max(0.0,nextafter(m.lower(d)-R,-INFINITY)),high=nextafter(m.upper(d)+R,INFINITY);
 return !(high<nextafter(m.lower(n.lo)-m.ru(radius),-INFINITY)||low>nextafter(m.upper(n.hi)+m.ru(radius),INFINITY));
}
void queue_stats(Counts&c,const vector<Task>&cur,const vector<Task>&next,uint64_t logical){
 c.frontier=max<uint64_t>(c.frontier,cur.size()+next.size());c.allocated=max<uint64_t>(c.allocated,(cur.capacity()+next.capacity())*sizeof(Task));c.logical=max(c.logical,logical);
}
Run independent(Metric m,const Tree&tr,const vector<int>&q,double radius,bool cached){
 Run r;auto t=Clock::now();m.c=&r.c;vector<Task>cur,next;for(size_t i=0;i<q.size();++i)cur.push_back({int(i),0});r.c.visits=q.size();
 while(!cur.empty()){
  queue_stats(r.c,cur,next,cur.size());uint64_t rem=cur.size();
  for(auto task:cur){--rem;auto&n=tr.nodes[task.d];if(n.kids.empty()){for(int i=n.begin;i<n.begin+n.count;++i)accept(r,m,task.q,tr.perm[i],q,radius);}
   else{m.role=0;double d=cached?m.eval(q[task.q],n.pivot).distance:0;
    for(int child:n.kids){++r.c.visits;double v=cached?d:m.eval(q[task.q],n.pivot).distance;if(shell(m,tr.nodes[child],v,0,radius))next.push_back({task.q,child});}}
   queue_stats(r.c,cur,next,rem+next.size());}
  cur.clear();cur.swap(next);
 }
 sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);r.index_bytes=tr.bytes();return r;
}
Run shared(Metric m,const Tree&tr,const vector<int>&q,double radius){
 Run r;auto t=Clock::now();m.c=&r.c;QTree qt=build_queries(m,q,r.c);r.query_bytes=qt.bytes();vector<Task>cur{{0,0}},next;r.c.visits=1;uint64_t nextLogical=0;
 auto push=[&](int qi,int di,double d,double R){++r.c.visits;if(shell(m,tr.nodes[di],d,R,radius)){next.push_back({qi,di});nextLogical+=qt.nodes[qi].count;}};
 while(!cur.empty()){
  nextLogical=0;uint64_t rem=0;for(auto a:cur)rem+=qt.nodes[a.q].count;queue_stats(r.c,cur,next,rem);
  for(auto task:cur){auto&qn=qt.nodes[task.q];auto&dn=tr.nodes[task.d];rem-=qn.count;m.role=0;
   if(qn.count==1&&dn.kids.empty()){for(int i=dn.begin;i<dn.begin+dn.count;++i)accept(r,m,qn.center,tr.perm[i],q,radius);}
   else if(qn.count>1&&(dn.kids.empty()||qn.count>=dn.count)){
    for(int i:{qn.left,qn.right}){assert(i>=0);auto&ch=qt.nodes[i];if(dn.parent<0){next.push_back({i,task.d});nextLogical+=ch.count;}else{m.role=0;auto&parent=tr.nodes[dn.parent];double d=m.eval(q[ch.center],parent.pivot).distance;push(i,task.d,d,ch.radius);}}}
   else{m.role=0;double d=m.eval(q[qn.center],dn.pivot).distance;for(int child:dn.kids)push(task.q,child,d,qn.radius);}
   queue_stats(r.c,cur,next,rem+nextLogical);
  }cur.clear();cur.swap(next);
 }
 sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);r.index_bytes=tr.bytes();return r;
}
struct Block{vector<int>a,b;int depth=0;};
uint64_t block_bytes(const vector<Block>&v){uint64_t z=v.capacity()*sizeof(Block);for(auto&b:v)z+=(b.a.capacity()+b.b.capacity())*4;return z;}
Run quickjoin(Metric m,const vector<int>&data,const vector<int>&q,double radius){
 Run r;auto t=Clock::now();m.c=&r.c;mt19937_64 rng(2026102120);vector<int>qi(q.size());iota(qi.begin(),qi.end(),0);vector<Block>cur{{data,qi,0}},next;
 uint64_t currentBytes=0,nextOwned=0;auto stat=[&](){r.c.frontier=max<uint64_t>(r.c.frontier,cur.size()+next.size());r.c.allocated=max(r.c.allocated,currentBytes+next.capacity()*sizeof(Block)+nextOwned);};
 while(!cur.empty()){
  currentBytes=block_bytes(cur);nextOwned=0;stat();for(auto&b:cur){++r.c.visits;int na=b.a.size(),nb=b.b.size();
   auto brute=[&](){for(int qi:b.b)for(int id:b.a)accept(r,m,qi,id,q,radius);};
   if(uint64_t(na)*nb<=400||b.depth>=64){brute();continue;}
   auto endpoint=[&](int i){return i<na?b.a[i]:q[b.b[i-na]];};
   int x=rng()%(na+nb),y=rng()%(na+nb-1);if(y>=x)++y;m.role=2;int pivot=endpoint(x);double rho=m.eval(pivot,endpoint(y)).distance;
   vector<int>al,ar,bl,br,awl,awr,bwl,bwr;
   for(int id:b.a){double d=m.eval(pivot,id).distance;if(d<rho){al.push_back(id);if(m.upper(d)>=m.lower(rho)-m.ru(radius))awl.push_back(id);}else{ar.push_back(id);if(m.lower(d)<=m.upper(rho)+m.ru(radius))awr.push_back(id);}}
   for(int qi:b.b){double d=m.eval(pivot,q[qi]).distance;if(d<rho){bl.push_back(qi);if(m.upper(d)>=m.lower(rho)-m.ru(radius))bwl.push_back(qi);}else{br.push_back(qi);if(m.lower(d)<=m.upper(rho)+m.ru(radius))bwr.push_back(qi);}}
   vector<pair<vector<int>*,vector<int>*>>parts{{&al,&bl},{&ar,&br},{&awl,&bwr},{&awr,&bwl}};
   bool progress=true;for(auto z:parts)if(z.first->size()==b.a.size()&&z.second->size()==b.b.size())progress=false;
   if(!progress){brute();continue;}
   for(auto z:parts)if(!z.first->empty()&&!z.second->empty()){next.push_back({*z.first,*z.second,b.depth+1});nextOwned+=(next.back().a.capacity()+next.back().b.capacity())*4;}
   stat();
  }cur.clear();cur.swap(next);
 }
 sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);return r;
}
struct BoxNode{int begin=0,count=0,left=-1,right=-1;double lx=0,ly=0,hx=0,hy=0;};
struct Boxes{vector<BoxNode>nodes;vector<int>perm;uint64_t bytes()const{return nodes.capacity()*sizeof(BoxNode)+perm.capacity()*4;}};
Boxes boxes(const vector<Record>&x,const vector<int>&ids){
 Boxes t;
 auto build=[&](auto&&self,vector<int>v)->int{int i=t.nodes.size();t.nodes.emplace_back();BoxNode n;n.begin=t.perm.size();n.count=v.size();n.lx=n.ly=INFINITY;n.hx=n.hy=-INFINITY;
  for(int k:v){n.lx=min(n.lx,x[k].x);n.hx=max(n.hx,x[k].x);n.ly=min(n.ly,x[k].y);n.hy=max(n.hy,x[k].y);}
  if(v.size()<=20)t.perm.insert(t.perm.end(),v.begin(),v.end());
  else{bool axis=n.hx-n.lx>=n.hy-n.ly;sort(v.begin(),v.end(),[&](int a,int b){return pair<double,int>{axis?x[a].x:x[a].y,a}<pair<double,int>{axis?x[b].x:x[b].y,b};});int cut=v.size()/2;
   n.left=self(self,vector<int>(v.begin(),v.begin()+cut));n.right=self(self,vector<int>(v.begin()+cut,v.end()));}t.nodes[i]=n;return i;};build(build,ids);return t;
}
Run spatial(Metric m,const vector<int>&data,const vector<int>&q,double radius){
 Run r;auto start=Clock::now();auto dt=boxes(m.x,data);r.index_seconds=elapsed(start);auto t=Clock::now();auto qt=boxes(m.x,q);r.query_bytes=qt.bytes();r.index_bytes=dt.bytes();r.index_nodes=dt.nodes.size();m.c=&r.c;vector<Task>cur{{0,0}},next;
 while(!cur.empty()){
  uint64_t logical=0,nextMass=0;for(auto a:cur)logical+=qt.nodes[a.q].count;queue_stats(r.c,cur,next,logical);
  for(auto a:cur){auto&u=qt.nodes[a.q];auto&v=dt.nodes[a.d];logical-=u.count;++r.c.visits;
   double dx=max({0.0,u.lx-v.hx,v.lx-u.hx}),dy=max({0.0,u.ly-v.hy,v.ly-u.hy});if(m.lower(sqrt(dx*dx+dy*dy))>m.ru(radius))continue;
   if(u.left<0&&v.left<0){for(int j=u.begin;j<u.begin+u.count;++j){int qi=find(q.begin(),q.end(),qt.perm[j])-q.begin();assert(qi<int(q.size()));for(int i=v.begin;i<v.begin+v.count;++i)accept(r,m,qi,dt.perm[i],q,radius);}}
   else if(u.left>=0&&(v.left<0||u.count>=v.count)){next.push_back({u.left,a.d});next.push_back({u.right,a.d});nextMass+=u.count;}
   else{next.push_back({a.q,v.left});next.push_back({a.q,v.right});nextMass+=2*u.count;}
   queue_stats(r.c,cur,next,logical+nextMass);
  }cur.clear();cur.swap(next);
 }
 sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);return r;
}
Run grid(Metric m,const vector<int>&data,const vector<int>&q,double radius){
 Run r;auto t=Clock::now();map<pair<int64_t,int64_t>,vector<int>>cells;for(int i:data)cells[{int64_t(floor(m.x[i].x/radius)),int64_t(floor(m.x[i].y/radius))}].push_back(i);
 r.index_seconds=elapsed(t);r.index_nodes=cells.size();r.index_bytes=cells.size()*(sizeof(pair<int64_t,int64_t>)+sizeof(vector<int>));for(auto&c:cells)r.index_bytes+=c.second.capacity()*4;
 t=Clock::now();m.c=&r.c;for(size_t qi=0;qi<q.size();++qi){auto&x=m.x[q[qi]];int64_t a=floor(x.x/radius),b=floor(x.y/radius);
  // Enumerate only cells intersecting the outward query interval (usually3x3).
  auto lowerCell=[&](double v){return int64_t(floor(nextafter(nextafter((v-m.ru(radius))/radius,-INFINITY),-INFINITY)));};
  auto upperCell=[&](double v){return int64_t(floor(nextafter(nextafter((v+m.ru(radius))/radius,INFINITY),INFINITY)));};
  (void)a;(void)b;
  for(int64_t cx=lowerCell(x.x);cx<=upperCell(x.x);++cx)for(int64_t cy=lowerCell(x.y);cy<=upperCell(x.y);++cy){++r.c.visits;auto it=cells.find({cx,cy});if(it!=cells.end())for(int id:it->second)accept(r,m,qi,id,q,radius);}}
 r.c.frontier=1;r.c.allocated=sizeof(Task);r.c.logical=1;sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);return r;
}
void write_hits(const string&p,const vector<Hit>&h){assert(!filesystem::exists(p));ofstream out(p,ios::binary);assert(out);for(auto&[q,i,d]:h){uint32_t qi=q;out.write((char*)&qi,4);out.write((char*)&i,8);out.write((char*)&d,8);}assert(out.good());}
vector<vector<Hit>> reference(Metric m,const vector<int>&data,const vector<int>&q,const vector<double>&radii){
 vector<vector<Hit>>out(radii.size());for(size_t qi=0;qi<q.size();++qi)for(int id:data){auto d=m.eval(q[qi],id);for(size_t j=0;j<radii.size();++j)if(m.hit(d,radii[j]))out[j].emplace_back(qi,m.x[id].source,d.score);}
 for(auto&h:out)sort(h.begin(),h.end());return out;
}
void self_test(){
 mt19937_64 rng(2026102122);vector<string>strings{"","a","aa","aba","baba",string(64,'A'),string(108,'G'),string(127,'T'),string(128,'C')};
 for(int k=0;k<500;++k){string a,b;for(int i=0,n=rng()%129;i<n;++i)a.push_back("ACGT"[rng()%4]);for(int i=0,n=rng()%129;i<n;++i)b.push_back("ACGT"[rng()%4]);assert(edit(a,b)==dp(a,b));assert(edit(a,b)==edit(b,a));}
 for(auto&a:strings)for(auto&b:strings)assert(edit(a,b)==dp(a,b));
 for(bool s:{true,false}){
  vector<Record>x;for(int i=0;i<96;++i){Record a;a.source=i;if(s){for(int j=0,n=rng()%16+1;j<n;++j)a.s.push_back("abcd"[rng()%4]);}else{a.x=float(int(rng()%9)/4.0);a.y=float(int(rng()%9)/4.0);}x.push_back(a);}
  vector<int>data(96),q{0,11,25,31,45,67,71,95};iota(data.begin(),data.end(),0);Metric m{x,s};Tree tr=build_gts(m,data);
  vector<double>radii=s?vector<double>{0,1,4,16}:vector<double>{.25,.5,1,4};auto ref=reference(m,data,q,radii);
  for(size_t ri=0;ri<radii.size();++ri){double radius=radii[ri];vector<Run>runs{independent(m,tr,q,radius,false),independent(m,tr,q,radius,true),shared(m,tr,q,radius),quickjoin(m,data,q,radius)};if(!s){runs.push_back(spatial(m,data,q,radius));runs.push_back(grid(m,data,q,radius));}
   for(auto&r:runs)assert(r.hits==ref[ri]);}
 }
 cout<<"SELF_TEST_PASS:581 independent DP score pairs;string and L2 complete-output fixtures;0GPU\n";
}
vector<int> readids(const string&p){ifstream f(p);assert(f);vector<int>ids;int v;while(f>>v)ids.push_back(v);assert(f.eof());return ids;}
int main(int argc,char**argv){
 if(argc==2&&string(argv[1])=="--self-test"){self_test();return 0;}assert(argc==6);
 string input=argv[1],qidfile=argv[2],deletes=argv[3],out=argv[4],phase=argv[5];assert(phase=="static"||phase=="updates");assert(filesystem::is_directory(out)&&filesystem::is_empty(out));
 ifstream f(input);assert(f);string name;int total,kind;f>>name>>total>>kind;string line;getline(f,line);vector<Record>x;
 while(getline(f,line)){size_t tab=line.find('\t');assert(tab!=string::npos);Record a;a.source=stoull(line.substr(0,tab));if(kind){a.s=line.substr(tab+1);assert(a.s.size()<=128);}else{istringstream v(line.substr(tab+1));float a0,b0;v>>a0>>b0;assert(v&&isfinite(a0)&&isfinite(b0));a.x=a0;a.y=b0;}x.push_back(std::move(a));}assert(int(x.size())==total);
 int N=total-32;auto q=readids(qidfile);assert(q.size()==256&&set<int>(q.begin(),q.end()).size()==256);for(int i:q)assert(i>=0&&i<N);
 Metric m{x,bool(kind)};vector<int>active(N);iota(active.begin(),active.end(),0);vector<double>radii=name=="Words"?vector<double>{1,2,3}:name=="TLoc"?vector<double>{.01,.05}:vector<double>{2,4,8};
 ofstream csv(out+"/COUNTERS.csv");assert(csv);csv<<"dataset,state,radius,method,N,Q,node_pair_visits,bound_calls,verify_calls,partition_calls,query_plan_calls,distance_calls,candidate_pairs,max_frontier_records,max_frontier_alloc_bytes,max_logical_query_node_frontier,query_tree_bytes,output_count,index_build_calls,index_build_seconds,index_nodes,index_bytes,wall_seconds\n";csv<<setprecision(17);
 auto emit=[&](int state,double radius,const string&method,Run&r,const Tree&tr){csv<<name<<','<<state<<','<<radius<<','<<method<<','<<active.size()<<','<<q.size()<<','<<r.c.visits<<','<<r.c.bounds<<','<<r.c.verify<<','<<r.c.partition<<','<<r.c.plan<<','<<r.c.calls()<<','<<r.c.candidates<<','<<r.c.frontier<<','<<r.c.allocated<<','<<r.c.logical<<','<<r.query_bytes<<','<<r.hits.size()<<','<<(method=="QUICKJOIN_FAMILY_CPU"?0:method=="GRID_2D_CPU"||method=="SPATIAL_DUAL_AABB_CPU"?r.index_calls:tr.build_calls)<<','<<(method=="QUICKJOIN_FAMILY_CPU"?0:method=="GRID_2D_CPU"||method=="SPATIAL_DUAL_AABB_CPU"?r.index_seconds:tr.seconds)<<','<<(method=="QUICKJOIN_FAMILY_CPU"?0:method=="GRID_2D_CPU"||method=="SPATIAL_DUAL_AABB_CPU"?r.index_nodes:tr.nodes.size())<<','<<r.index_bytes<<','<<r.seconds<<'\n';csv.flush();assert(csv.good());};
 ofstream builds(out+"/BUILDS.csv");assert(builds);builds<<"state,N,nodes,calls,seconds,bytes,mutation_seconds,old_index_release_seconds,ack_seconds\n"<<setprecision(17);
 Tree live;bool live_present=false;
 auto execute=[&](int state,bool full,double mutation=0,Clock::time_point ack_start=Clock::now()){
  auto release_start=Clock::now();if(live_present)live=Tree{};double release=elapsed(release_start);live=build_gts(m,active);live_present=true;Tree&tr=live;double ack=state?elapsed(ack_start):0;builds<<state<<','<<active.size()<<','<<tr.nodes.size()<<','<<tr.build_calls<<','<<tr.seconds<<','<<tr.bytes()<<','<<mutation<<','<<release<<','<<ack<<'\n';builds.flush();
  vector<double>rs=full?radii:vector<double>{radii[radii.size()/2]};auto ref=reference(m,active,q,rs);
  for(size_t ri=0;ri<rs.size();++ri){double radius=rs[ri];string prefix=out+"/S"+to_string(state)+"_R"+to_string(ri);write_hits(prefix+"_REFERENCE.bin",ref[ri]);
   vector<string>methods=full?vector<string>{"GTS_LITERAL_CPU","GTS_PARENT_CACHE_CPU","SHARED_ANNULUS_CPU","QUICKJOIN_FAMILY_CPU"}:vector<string>{"GTS_PARENT_CACHE_CPU","SHARED_ANNULUS_CPU"};
   if(full&&!kind){methods.push_back("GRID_2D_CPU");methods.push_back("SPATIAL_DUAL_AABB_CPU");}
   for(auto&method:methods){Run r=method=="GTS_LITERAL_CPU"?independent(m,tr,q,radius,false):method=="GTS_PARENT_CACHE_CPU"?independent(m,tr,q,radius,true):method=="SHARED_ANNULUS_CPU"?shared(m,tr,q,radius):method=="QUICKJOIN_FAMILY_CPU"?quickjoin(m,active,q,radius):method=="GRID_2D_CPU"?grid(m,active,q,radius):spatial(m,active,q,radius);
    assert(r.hits==ref[ri]);assert(r.c.candidates==r.c.verify);write_hits(prefix+"_"+method+".bin",r.hits);emit(state,radius,method,r,tr);cout<<"TRACE_PASS "<<name<<" S"<<state<<" r"<<radius<<' '<<method<<" calls="<<r.c.calls()<<" output="<<r.hits.size()<<'\n'<<flush;
   }
  }
 };
 if(phase=="static")execute(0,true);
 else{execute(0,false);auto remove=readids(deletes);assert(remove.size()==32);for(int i:remove)assert(find(q.begin(),q.end(),i)==q.end());set<int>removed(remove.begin(),remove.end());auto ack_start=Clock::now();active.erase(remove_if(active.begin(),active.end(),[&](int id){return removed.count(id);}),active.end());assert(active.size()==size_t(N-32));double mutation=elapsed(ack_start);execute(1,false,mutation,ack_start);ack_start=Clock::now();for(int id=N;id<total;++id)active.push_back(id);assert(active.size()==size_t(N));mutation=elapsed(ack_start);execute(2,false,mutation,ack_start);}
 cout<<"CAMPAIGN_PROCESS_PASS "<<name<<' '<<phase<<" 0GPU\n";
}
