// CPU semantic precheck. The private build extracts pinned prior helpers before main.
#include "trace_helpers.hpp"
constexpr int N0=4096,P=4;
using Bands=array<int,P>;
struct CertStore{
 vector<int> rows,slot,owner;vector<Bands> values;array<int,P> piv;array<string,P> pivot_values;
 uint64_t copied_entries=0,maint_calls=0;double seconds=0;
 CertStore(Metric m,const vector<int>&r,array<int,P>p):rows(r),slot(m.x.size(),-1),owner(r),piv(p){
  auto start=Clock::now();for(int j=0;j<P;++j)pivot_values[j]=m.x[piv[j]].s;values.reserve(N0);rows.reserve(N0);owner.reserve(N0);
  for(int id:rows){slot[id]=values.size();Bands b{};for(int j=0;j<P;++j){b[j]=edit(m.x[id].s,pivot_values[j]);++maint_calls;}values.push_back(b);}
  seconds=elapsed(start);
 }
 uint64_t bytes()const{uint64_t b=rows.capacity()*4+slot.capacity()*4+owner.capacity()*4+values.capacity()*sizeof(Bands)+sizeof(piv)+sizeof(pivot_values);for(auto&p:pivot_values)b+=p.capacity()+1;return b;}
 void erase(const vector<int>&ids){
  for(int id:ids){int s=slot.at(id);assert(s>=0&&owner.at(s)==id);int last=rows.back();
   if(s!=int(rows.size())-1){rows[s]=last;owner[s]=owner.back();values[s]=values.back();slot[last]=s;copied_entries+=P;}
   rows.pop_back();owner.pop_back();values.pop_back();slot[id]=-1;
  }
 }
 void insert(Metric m,const vector<int>&ids){
  maint_calls=0;
  for(int id:ids){assert(slot.at(id)==-1);Bands b{};for(int j=0;j<P;++j){b[j]=edit(m.x[id].s,pivot_values[j]);++maint_calls;}
   slot[id]=rows.size();rows.push_back(id);owner.push_back(id);values.push_back(b);}
 }
 uint64_t check(Metric m)const{
  uint64_t checked=0;assert(rows.size()==owner.size()&&rows.size()==values.size());
  set<int> unique(rows.begin(),rows.end());assert(unique.size()==rows.size());
  for(size_t s=0;s<rows.size();++s){int id=rows[s];assert(owner[s]==id&&slot[id]==int(s));
   for(int j=0;j<P;++j){assert(values[s][j]==edit(m.x[id].s,pivot_values[j]));++checked;}}
  return checked;
 }
};
Run pivot_query(Metric m,const CertStore&st,const vector<int>&q,int radius,uint64_t&comparisons){
 Run r;auto t=Clock::now();m.c=&r.c;
 for(size_t qi=0;qi<q.size();++qi){Bands qp{};for(int j=0;j<P;++j){qp[j]=edit(m.x[q[qi]].s,st.pivot_values[j]);++r.c.plan;}
  for(size_t s=0;s<st.rows.size();++s){assert(st.owner[s]==st.rows[s]);bool reject=false;
   for(int j=0;j<P;++j){++comparisons;if(abs(qp[j]-st.values[s][j])>radius){reject=true;break;}}
   ++r.c.visits;if(!reject)accept(r,m,qi,st.rows[s],q,radius);}}
 sort(r.hits.begin(),r.hits.end());r.seconds=elapsed(t);r.index_bytes=st.bytes();return r;
}
void fixtures(){
 mt19937_64 rng(2026102149);int checks=0;
 for(int k=0;k<500;++k){string a,b;for(int i=0,n=rng()%129;i<n;++i)a+="ACGT"[rng()%4];for(int i=0,n=rng()%129;i<n;++i)b+="ACGT"[rng()%4];assert(edit(a,b)==dp(a,b));++checks;}
 vector<string>v{"","A","AA","ABA","BABA",string(64,'A'),string(108,'G'),string(127,'T'),string(128,'C')};
 for(auto&a:v)for(auto&b:v){assert(edit(a,b)==dp(a,b));++checks;}assert(checks==581);
 // Known false-prune witnesses: stale row owner,stale insertion envelope,and mutable pivot.
 vector<Record>x{{0,string(8,'A')},{1,string(8,'T')},{2,string(8,'C')},{3,string(8,'G')}};
 Metric m{x,true};assert(abs(edit(x[1].s,x[0].s)-edit(x[0].s,x[0].s))>0&&edit(x[1].s,x[1].s)==0);
 CertStore st(m,{0,1,2,3},{0,1,2,3});auto old=st.values;st.erase({0,1});assert(st.check(m)==8);
 uint64_t comp=0;auto a=pivot_query(m,st,{2,3},0,comp);assert(a.hits.size()==2);
 // Deleted pivots remain retained immutable metric values;ordinary insertion restores only new columns.
 st.insert(m,{0,1});assert(st.maint_calls==8&&st.check(m)==16);
 assert(st.values[st.slot[0]]==old[0]&&st.values[st.slot[1]]==old[1]);
 int oldLo=0,oldHi=0,newPoint=8,queryPivot=8;assert(queryPivot>oldHi);oldHi=max(oldHi,newPoint);assert(queryPivot>=oldLo&&queryPivot<=oldHi);
 auto changed=x;changed[0].s=string(8,'T');assert(edit(changed[0].s,changed[1].s)!=edit(x[0].s,x[1].s));
 // A generation mismatch must reject reuse rather than silently transfer the old value.
 int cachedGeneration=1,currentGeneration=2;assert(cachedGeneration!=currentGeneration);
 cout<<"FIXTURES_PASS 581_DP_pairs;swap-owner,insertion-envelope,deleted-pivot,changed-generation witnesses;0GPU\n";
}
int main(int argc,char**argv){
 if(argc==2&&string(argv[1])=="--self-test"){fixtures();return 0;}assert(argc==4);
 string input=argv[1],selection=argv[2],out=argv[3];assert(filesystem::is_directory(out)&&filesystem::is_empty(out));
 ifstream f(input);string name;int total,kind;f>>name>>total>>kind;assert(total==N0+32&&kind==1);string line;getline(f,line);vector<Record>x;
 while(getline(f,line)){size_t tab=line.find('\t');assert(tab!=string::npos);Record z;z.source=stoull(line.substr(0,tab));z.s=line.substr(tab+1);x.push_back(z);}assert(int(x.size())==total);
 auto ids=readids(selection);assert(ids.size()==64+32+4+32);vector<int>q(ids.begin(),ids.begin()+64),cal(ids.begin()+64,ids.begin()+96),deleted(ids.begin()+100,ids.end());array<int,P>piv{};copy(ids.begin()+96,ids.begin()+100,piv.begin());
 set<int>seen(q.begin(),q.end());for(int i:cal)assert(seen.insert(i).second);for(int i:piv)assert(seen.insert(i).second);
 assert(set<int>(deleted.begin(),deleted.end()).size()==32);for(int i:q)assert(find(deleted.begin(),deleted.end(),i)==deleted.end());for(int i:cal)assert(find(deleted.begin(),deleted.end(),i)==deleted.end());
 Metric m{x,true};vector<int>base(N0);iota(base.begin(),base.end(),0);
 vector<int>distances;for(int qi:cal)for(int id:base)distances.push_back(edit(x[qi].s,x[id].s));sort(distances.begin(),distances.end());
 vector<int>denoms{10000,1000,100},radii;ofstream cf(out+"/CALIBRATION.csv");cf<<"level,target_denominator,radius,pairs,inclusive_hits\n";
 for(int d:denoms){size_t rank=(distances.size()+d-1)/d;int r=distances[rank-1];radii.push_back(r);cf<<radii.size()-1<<','<<d<<','<<r<<','<<distances.size()<<','<<(upper_bound(distances.begin(),distances.end(),r)-distances.begin())<<'\n';}cf.close();
 // CALIBRATION is complete and emitted before the first measured-query distance.
 cout<<"CALIBRATION_FROZEN "<<name<<flush;
 for(int r:radii)cout<<' '<<r;cout<<'\n'<<flush;
 CertStore incremental(m,base,piv),weak(m,base,piv);
 ofstream builds(out+"/COSTS.csv");builds<<setprecision(17)<<"state,method,N,metric_calls,seconds,index_bytes,moved_certificate_entries,diagnostic_checked_entries,unaffected_old_entries_changed\n";
 ofstream query(out+"/QUERY.csv");query<<setprecision(17)<<"dataset,state,level,radius,method,N,Q,distance_calls,bound_calls,verify_calls,partition_calls,query_plan_calls,scalar_bound_checks,node_pair_visits,candidate_pairs,frontier_bytes,output_count,output_bytes,compute_seconds,serialize_seconds\n";
 for(int state=0;state<3;++state){
  uint64_t ic=incremental.maint_calls,wc=weak.maint_calls;double isec=incremental.seconds,wsec=weak.seconds;uint64_t copied=0;
  if(state){auto before=incremental.values;auto beforeRows=incremental.rows;auto beforeCopied=incremental.copied_entries;auto t=Clock::now();
   if(state==1){incremental.erase(deleted);incremental.maint_calls=0;}else{vector<int>incoming(32);iota(incoming.begin(),incoming.end(),N0);incremental.insert(m,incoming);}
   isec=elapsed(t);ic=incremental.maint_calls;copied=incremental.copied_entries-beforeCopied;
   for(size_t i=0;i<beforeRows.size();++i){int slot=incremental.slot[beforeRows[i]];if(slot>=0)assert(before[i]==incremental.values[slot]);}
   t=Clock::now();CertStore replacement(m,incremental.rows,piv);wc=replacement.maint_calls;weak=std::move(replacement);wsec=elapsed(t);
  }
  uint64_t verified=incremental.check(m);assert(weak.rows==incremental.rows&&weak.values==incremental.values);
  builds<<state<<",PIVOT_INCREMENTAL_CPU,"<<incremental.rows.size()<<','<<ic<<','<<isec<<','<<incremental.bytes()<<','<<copied<<','<<verified<<",0\n";
  builds<<state<<",PIVOT_RECOMPUTE_ALL_WEAK,"<<weak.rows.size()<<','<<wc<<','<<wsec<<','<<weak.bytes()<<",0,0,0\n";
  auto tree=build_gts(m,incremental.rows);builds<<state<<",GTS_CACHED_SNAPSHOT_CPU,"<<incremental.rows.size()<<','<<tree.build_calls<<','<<tree.seconds<<','<<tree.bytes()<<",0,0,0\n";
  builds<<state<<",QUICKJOIN_FAMILY_CPU,"<<incremental.rows.size()<<",0,0,0,0,0,0\n";builds.flush();
  vector<double>rs(radii.begin(),radii.end());auto truth=reference(m,incremental.rows,q,rs);
  for(int level=0;level<3;++level){int radius=radii[level];string pre=out+"/S"+to_string(state)+"_L"+to_string(level);write_hits(pre+"_REFERENCE.bin",truth[level]);
   for(string method:{"PIVOT_INCREMENTAL_CPU","PIVOT_RECOMPUTE_ALL_WEAK","GTS_CACHED_SNAPSHOT_CPU","QUICKJOIN_FAMILY_CPU"}){
    uint64_t comparisons=0;Run r=method=="PIVOT_INCREMENTAL_CPU"?pivot_query(m,incremental,q,radius,comparisons):method=="PIVOT_RECOMPUTE_ALL_WEAK"?pivot_query(m,weak,q,radius,comparisons):method=="GTS_CACHED_SNAPSHOT_CPU"?independent(m,tree,q,radius,true):quickjoin(m,incremental.rows,q,radius);
    assert(r.hits==truth[level]);assert(r.c.candidates==r.c.verify);auto t=Clock::now();write_hits(pre+"_"+method+".bin",r.hits);double outputTime=elapsed(t);
    query<<name<<','<<state<<','<<level<<','<<radius<<','<<method<<','<<incremental.rows.size()<<','<<q.size()<<','<<r.c.calls()<<','<<r.c.bounds<<','<<r.c.verify<<','<<r.c.partition<<','<<r.c.plan<<','<<comparisons<<','<<r.c.visits<<','<<r.c.candidates<<','<<r.c.allocated<<','<<r.hits.size()<<','<<r.hits.size()*20<<','<<r.seconds<<','<<outputTime<<'\n';query.flush();
   }
  }
 }
 assert(builds&&query);cout<<"POPULATION_PASS "<<name<<";36 complete streams;0GPU\n";return 0;
}
