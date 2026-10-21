// Own CPU top-k adapters;reuse pinned metric,ten-way layout,and rectangular Quickjoin only.
#include "trace_helpers.hpp"
#include <queue>
#include <unordered_map>
using Key=tuple<int,uint64_t,int>;
using Entry=pair<int,int>;
constexpr int INF=1000000;
struct Work {
 uint64_t metric=0,bound_metric=0,verify_metric=0,cache_hits=0,bound_checks=0,node_pops=0,point_visits=0,known_scans=0,heap_peak=0,intermediate_hits=0;
 Work& operator+=(const Work&b){metric+=b.metric;bound_metric+=b.bound_metric;verify_metric+=b.verify_metric;cache_hits+=b.cache_hits;bound_checks+=b.bound_checks;node_pops+=b.node_pops;point_visits+=b.point_visits;known_scans+=b.known_scans;heap_peak=max(heap_peak,b.heap_peak);intermediate_hits+=b.intermediate_hits;return *this;}
};
struct Search {
 vector<int>score,known;vector<Entry>frontier;vector<Key>answer,ranking;
 uint64_t bytes()const{return sizeof(Search)+(score.capacity()+known.capacity())*sizeof(int)+frontier.capacity()*sizeof(Entry)+(answer.capacity()+ranking.capacity())*sizeof(Key);}
};
int tau(const vector<Key>&a){assert(!a.empty());return get<0>(a.back());}
vector<Key> rank_known(const vector<Record>&x,const Search&s,const vector<char>&live,int k,Work&w){
 vector<Key>a;for(int id:s.known){++w.known_scans;assert(s.score[id]>=0);if(live[id])a.emplace_back(s.score[id],x[id].source,id);}
 sort(a.begin(),a.end());if(int(a.size())>k)a.resize(k);return a;
}
Search fresh(int n){Search s;s.score.assign(n,-1);s.frontier={{0,0}};return s;}
void remember(Search&s,int id,int distance){assert(s.score[id]<0);s.score[id]=distance;s.known.push_back(id);}
void continue_search(const vector<Record>&x,const Tree&t,int qi,int k,const vector<char>&live,Search&s,Work&w,int oracle_tau=-1){
 assert(int(s.score.size())==int(live.size())&&k>0);vector<Key>best;
 auto add=[&](int id,int d){if(!live[id])return;Key key{d,x[id].source,id};if(int(best.size())<k){best.push_back(key);push_heap(best.begin(),best.end());}else if(key<best.front()){pop_heap(best.begin(),best.end());best.back()=key;push_heap(best.begin(),best.end());}};
 for(int id:s.known){++w.known_scans;add(id,s.score[id]);}
 auto score=[&](int id,bool bound){
  if(s.score[id]>=0){++w.cache_hits;return s.score[id];}
  int d=edit(x[qi].s,x[id].s);remember(s,id,d);++w.metric;if(bound)++w.bound_metric;else ++w.verify_metric;add(id,d);return d;
 };
 make_heap(s.frontier.begin(),s.frontier.end(),greater<Entry>());w.heap_peak=s.frontier.size();
 while(!s.frontier.empty()){
  int limit=oracle_tau>=0?oracle_tau:int(best.size())==k?get<0>(best.front()):INF;
  if(s.frontier.front().first>limit)break;
  pop_heap(s.frontier.begin(),s.frontier.end(),greater<Entry>());auto [parentlb,ni]=s.frontier.back();s.frontier.pop_back();++w.node_pops;const auto&n=t.nodes[ni];
  if(n.kids.empty()){
   for(int j=n.begin;j<n.begin+n.count;++j){int id=t.perm[j];++w.point_visits;if(live[id])score(id,false);}
  }else{
   int d=score(n.pivot,true);
   for(int child:n.kids){++w.bound_checks;const auto&v=t.nodes[child];int lb=max(parentlb,max(0,int(v.lo)-d));if(isfinite(v.hi))lb=max(lb,d-int(v.hi));
    s.frontier.emplace_back(lb,child);push_heap(s.frontier.begin(),s.frontier.end(),greater<Entry>());}
  }
  w.heap_peak=max<uint64_t>(w.heap_peak,s.frontier.size());
 }
 assert(int(best.size())==k);sort(best.begin(),best.end());s.answer=std::move(best);
 if(oracle_tau>=0)assert(tau(s.answer)==oracle_tau);
 assert(s.frontier.empty()||s.frontier.front().first>tau(s.answer));assert(w.metric==w.bound_metric+w.verify_metric);
}
vector<Key> truth_one(const vector<Record>&x,int qi,int n,int k,const vector<char>&live){
 vector<Key>a;for(int id=0;id<n;++id)if(live[id])a.emplace_back(edit(x[qi].s,x[id].s),x[id].source,id);sort(a.begin(),a.end());a.resize(k);return a;
}
vector<Search> qjoin_topk(const vector<Record>&x,const vector<int>&q,const vector<int>&ks,const vector<char>&live,const vector<char>&affected,const vector<Search>*old,Work&w){
 int n=live.size();vector<int>data;for(int i=0;i<n;++i)if(live[i])data.push_back(i);vector<Search>out(q.size());if(old)out=*old;
 unordered_map<uint64_t,int>source;for(int i=0;i<n;++i)assert(source.emplace(x[i].source,i).second);
 for(int k:{1,4,16,64}){
  vector<int>group,groupq;int radius=0;
  for(size_t j=0;j<q.size();++j)if(affected[j]&&ks[j]==k){group.push_back(j);groupq.push_back(q[j]);int limit=0;
   for(int z=0;z<k;++z){int d=edit(x[q[j]].s,x[data[z]].s);++w.metric;++w.verify_metric;limit=max(limit,d);}radius=max(radius,limit);}
  if(group.empty())continue;
  Metric m{x,true};Run r=quickjoin(m,data,groupq,radius);w.metric+=r.c.calls();w.bound_metric+=r.c.bounds+r.c.partition+r.c.plan;w.verify_metric+=r.c.verify;
  w.node_pops+=r.c.visits;w.point_visits+=r.c.candidates;w.heap_peak=max(w.heap_peak,r.c.frontier);w.intermediate_hits+=r.hits.size();
  vector<vector<Key>>hits(group.size());for(auto [j,id,d]:r.hits){assert(source.count(id));hits.at(j).emplace_back(int(d),id,source.at(id));}
  for(size_t j=0;j<group.size();++j){sort(hits[j].begin(),hits[j].end());assert(int(hits[j].size())>=k);hits[j].resize(k);Search s;s.score.assign(n,-1);s.answer=hits[j];for(auto [d,src,id]:s.answer)remember(s,id,d);out[group[j]]=std::move(s);}
 }
 assert(w.metric==w.bound_metric+w.verify_metric);return out;
}
vector<Hit> flattened(const vector<Search>&s){vector<Hit>h;for(size_t i=0;i<s.size();++i)for(auto [d,src,id]:s[i].answer)h.emplace_back(i,src,d);return h;}
struct Diag {uint64_t affected=0,tau_up=0,removed=0,replacements=0,stale_nodes=0,stale_live=0,stale_unknown=0,unique_nodes=0,shared_nodes=0,unique_candidates=0;};
Diag diagnose(const vector<Record>&x,const Tree&t,const vector<int>&ks,const vector<Search>&old,const vector<Search>&now,const vector<char>&live,ofstream&detail,const string&episode){
 Diag total;map<int,int>node_counts;set<int>candidate_union;
 for(size_t qi=0;qi<old.size();++qi){uint64_t removed=0,replaced=0,sn=0,sl=0,su=0;set<int>oldIDs;for(auto [d,src,id]:old[qi].answer){oldIDs.insert(id);removed+=!live[id];}
  for(auto [d,src,id]:now[qi].answer)replaced+=!oldIDs.count(id);assert(removed==replaced);int a=tau(old[qi].answer),b=tau(now[qi].answer);assert(b>=a);
  for(auto [lb,node]:old[qi].frontier){assert(lb>a);if(lb>b)continue;++sn;++node_counts[node];const auto&nd=t.nodes[node];
   for(int z=nd.begin;z<nd.begin+nd.count;++z){int id=t.perm[z];if(live[id]){++sl;if(old[qi].score[id]<0){++su;candidate_union.insert(id);}}}}
  total.affected+=removed>0;total.tau_up+=b>a;total.removed+=removed;total.replacements+=replaced;total.stale_nodes+=sn;total.stale_live+=sl;total.stale_unknown+=su;
  detail<<episode<<','<<qi<<','<<ks[qi]<<','<<a<<','<<b<<','<<removed<<','<<replaced<<','<<old[qi].frontier.size()<<','<<sn<<','<<sl<<','<<su<<'\n';
 }
 total.unique_nodes=node_counts.size();for(auto [id,count]:node_counts)total.shared_nodes+=count>1;total.unique_candidates=candidate_union.size();return total;
}
void fixtures(){
 mt19937_64 rng(2026102159);int pairs=0;
 for(int z=0;z<500;++z){string a,b;for(int j=0,n=rng()%129;j<n;++j)a+="ACGT"[rng()%4];for(int j=0,n=rng()%129;j<n;++j)b+="ACGT"[rng()%4];assert(edit(a,b)==dp(a,b));++pairs;}
 vector<string>v{"","a","aa","aba","baba",string(64,'A'),string(108,'G'),string(127,'T'),string(128,'C')};for(auto&a:v)for(auto&b:v){assert(edit(a,b)==dp(a,b));++pairs;}assert(pairs==581);
 // Explicit witness:valid LB=2 was pruned at tau=1;deleting rank2 raises tau to2.
 vector<Record>x{{9,""},{5,"A"},{7,"AA"},{1,"AAA"},{99,""}};Tree t;t.perm={0,1,2,3};t.nodes.resize(3);t.nodes[0].pivot=0;t.nodes[0].kids={1,2};t.nodes[0].count=4;
 t.nodes[1].parent=t.nodes[2].parent=0;t.nodes[1].count=2;t.nodes[1].lo=0;t.nodes[1].hi=1;t.nodes[2].begin=2;t.nodes[2].count=2;t.nodes[2].lo=2;
 vector<char>live(4,1);Search initial=fresh(4);Work wi;continue_search(x,t,4,2,live,initial,wi);assert(tau(initial.answer)==1&&initial.frontier.size()==1&&initial.frontier[0].first==2);
 live[1]=0;Search online=initial,oracle=initial;Work wo,wr;continue_search(x,t,4,2,live,online,wo);continue_search(x,t,4,2,live,oracle,wr,2);
 assert(online.answer==truth_one(x,4,4,2,live)&&online.answer==oracle.answer&&wo.metric==wr.metric&&wo.metric>0&&tau(online.answer)==2);
 // A deleted result can change ID while leaving the kth distance unchanged.
 vector<Record>tied{{50,"A"},{10,"T"},{30,"C"},{90,"G"},{100,""}};vector<int>ids{0,1,2,3};auto tt=build_gts(Metric{tied,true},ids);live.assign(4,1);Search st=fresh(4);Work tw;continue_search(tied,tt,4,1,live,st,tw);assert(get<1>(st.answer[0])==10);live[1]=0;Work tr;continue_search(tied,tt,4,1,live,st,tr);assert(get<1>(st.answer[0])==30&&tau(st.answer)==1&&tr.metric==0);
 for(int round=0;round<8;++round){
  vector<Record>r;for(int i=0;i<112;++i){string a;for(int j=0,n=rng()%25;j<n;++j)a+="abcd"[rng()%4];r.push_back({uint64_t(1000-i*3),a});}
  vector<int>base(96),q{96,97,98,99,100,101,102,103},ks{1,4,16,64,1,4,16,64};iota(base.begin(),base.end(),0);Tree tree=build_gts(Metric{r,true},base);vector<char>alive(96,1),all(q.size(),1);vector<Search>before;
  for(size_t i=0;i<q.size();++i){Search s=fresh(96);Work w;continue_search(r,tree,q[i],ks[i],alive,s,w);assert(s.answer==truth_one(r,q[i],96,ks[i],alive));
   for(auto [lb,node]:s.frontier)for(int j=tree.nodes[node].begin;j<tree.nodes[node].begin+tree.nodes[node].count;++j)assert(lb<=edit(r[q[i]].s,r[tree.perm[j]].s));before.push_back(s);}
  for(int i=0;i<20;++i)alive[i]=0;
  for(size_t i=0;i<q.size();++i){auto ref=truth_one(r,q[i],96,ks[i],alive);Search s=before[i],o=s;Work w,ow;continue_search(r,tree,q[i],ks[i],alive,s,w);continue_search(r,tree,q[i],ks[i],alive,o,ow,get<0>(ref.back()));assert(s.answer==ref&&o.answer==ref&&w.metric==ow.metric&&w.node_pops==ow.node_pops);
   Search root=fresh(96);for(auto [d,src,id]:before[i].answer)if(alive[id])remember(root,id,d);Work rw;continue_search(r,tree,q[i],ks[i],alive,root,rw);assert(root.answer==ref);
   Search reserve=fresh(96);vector<char>initialLive(96,1);Work sw;continue_search(r,tree,q[i],ks[i]+32,initialLive,reserve,sw);reserve.answer.resize(ks[i]);Work post;continue_search(r,tree,q[i],ks[i],alive,reserve,post);assert(reserve.answer==ref);
   Search full;full.score.assign(96,-1);for(int id=0;id<96;++id)remember(full,id,edit(r[q[i]].s,r[id].s));Work fw;full.ranking=rank_known(r,full,initialLive,96,fw);vector<Key>filtered;for(auto key:full.ranking){if(alive[get<2>(key)])filtered.push_back(key);if(int(filtered.size())==ks[i])break;}assert(filtered==ref);
  }
  Work qw;auto qs=qjoin_topk(r,q,ks,alive,all,nullptr,qw);for(size_t i=0;i<q.size();++i)assert(qs[i].answer==truth_one(r,q[i],96,ks[i],alive));
 }
 cout<<"FIXTURES_PASS 581 independent DP pairs;threshold-reopening and tie-only witnesses;8 random fixtures;future-blind/oracle parity;Quickjoin top-k;0GPU\n";
}
int main(int argc,char**argv){
 if(argc==2&&string(argv[1])=="--self-test"){fixtures();return 0;}assert(argc==4);string input=argv[1],selection=argv[2],out=argv[3];assert(filesystem::is_directory(out)&&filesystem::is_empty(out));
 ifstream f(input);string name,line;int total,kind;f>>name>>total>>kind;getline(f,line);assert(total==4160&&kind==1);vector<Record>x;
 while(getline(f,line)){size_t tab=line.find('\t');assert(tab!=string::npos);Record r{stoull(line.substr(0,tab)),line.substr(tab+1)};assert(r.s.size()<=128);x.push_back(r);}assert(int(x.size())==total);
 set<uint64_t>source;for(auto&r:x)assert(source.insert(r.source).second);auto qs=readids(selection);assert(qs.size()==64);for(size_t i=0;i<qs.size();++i)assert(qs[i]==4096+int(i));
 const int n=4096;vector<int>base(n),ks; iota(base.begin(),base.end(),0);for(size_t i=0;i<qs.size();++i)ks.push_back(array<int,4>{1,4,16,64}[i%4]);vector<char>alive(n,1),all(qs.size(),1);
 Tree tree=build_gts(Metric{x,true},base);ofstream build(out+"/BUILD.csv");build<<setprecision(17)<<"N,Q,index_metric_calls,index_seconds,index_bytes,index_nodes\n"<<n<<','<<qs.size()<<','<<tree.build_calls<<','<<tree.seconds<<','<<tree.bytes()<<','<<tree.nodes.size()<<'\n';build.close();
 vector<string>methods{"GTS_CACHED_ROOT_RESTART","RETAIN_FRONTIER","RESERVE_K32","FULL_RANK_CACHE","QUICKJOIN_TOPK_SEEDED","FIXED_TREE_THRESHOLD_ORACLE"};
 map<string,vector<Search>>initial;map<string,Work>initial_work;map<string,double>initial_seconds;vector<Search>reference;
 ofstream costs(out+"/COSTS.csv"),work(out+"/QUERY_WORK.csv"),diag(out+"/FRONTIER.csv"),episodes(out+"/EPISODES.csv");
 costs<<setprecision(17)<<"dataset,episode,method,N,Q,affected_queries,metric_calls,bound_metric,verify_metric,cache_hits,scalar_bounds,node_pops,point_visits,known_scans,heap_peak,intermediate_hits,cache_payload_bytes,compute_seconds,serialize_seconds,output_count,output_bytes,mutation_seconds,posting_visits\n";
 work<<"episode,method,qi,k,metric_calls,bound_metric,verify_metric,node_pops,point_visits,known_scans,missing_output_pair_floor\n";
 diag<<"episode,qi,k,old_tau,new_tau,removed_answers,true_replacements,old_frontier_nodes,reopened_nodes,reopened_live_pairs,reopened_unknown_pairs\n";
 episodes<<"episode,deletes,affected_queries,tau_up_queries,removed_answers,true_replacements,reopened_nodes,reopened_live_pairs,reopened_unknown_pairs,unique_reopened_node_ids,shared_reopened_node_ids,unique_reopened_candidate_ids\n";
 auto emit=[&](const string&episode,const string&method,const vector<Search>&s,const Work&w,double seconds,int liveN,int affected,double mutation,uint64_t posting){
  uint64_t bytes=0;for(auto&z:s)bytes+=z.bytes();auto hits=flattened(s);auto start=Clock::now();write_hits(out+"/"+episode+"_"+method+".bin",hits);double serial=elapsed(start);
  assert(hits.size()==1360);costs<<name<<','<<episode<<','<<method<<','<<liveN<<",64,"<<affected<<','<<w.metric<<','<<w.bound_metric<<','<<w.verify_metric<<','<<w.cache_hits<<','<<w.bound_checks<<','<<w.node_pops<<','<<w.point_visits<<','<<w.known_scans<<','<<w.heap_peak<<','<<w.intermediate_hits<<','<<bytes<<','<<seconds<<','<<serial<<','<<hits.size()<<','<<hits.size()*20<<','<<mutation<<','<<posting<<'\n';costs.flush();assert(costs);
 };
 for(const auto&method:methods){
  if(method=="FIXED_TREE_THRESHOLD_ORACLE"){initial[method]=initial.at("RETAIN_FRONTIER");initial_work[method]=initial_work.at("RETAIN_FRONTIER");initial_seconds[method]=initial_seconds.at("RETAIN_FRONTIER");emit("INITIAL",method,initial[method],initial_work[method],initial_seconds[method],n,64,0,0);continue;}
  auto start=Clock::now();Work sum;vector<Search>states;
  if(method=="QUICKJOIN_TOPK_SEEDED")states=qjoin_topk(x,qs,ks,alive,all,nullptr,sum);
  else for(size_t i=0;i<qs.size();++i){Search s=fresh(n);Work w;
   if(method=="FULL_RANK_CACHE"){s.frontier.clear();for(int id=0;id<n;++id){remember(s,id,edit(x[qs[i]].s,x[id].s));++w.metric;++w.verify_metric;}s.ranking=rank_known(x,s,alive,n,w);s.answer.assign(s.ranking.begin(),s.ranking.begin()+ks[i]);}
   else{int target=ks[i]+(method=="RESERVE_K32"?32:0);continue_search(x,tree,qs[i],target,alive,s,w);s.answer.resize(ks[i]);}
   if(method=="GTS_CACHED_ROOT_RESTART"){Search retained;retained.score.assign(n,-1);retained.answer=s.answer;for(auto [d,src,id]:s.answer)remember(retained,id,d);s=std::move(retained);}
   sum+=w;work<<"INITIAL,"<<method<<','<<i<<','<<ks[i]<<','<<w.metric<<','<<w.bound_metric<<','<<w.verify_metric<<','<<w.node_pops<<','<<w.point_visits<<','<<w.known_scans<<",0\n";states.push_back(std::move(s));}
  double seconds=elapsed(start);initial[method]=std::move(states);initial_work[method]=sum;initial_seconds[method]=seconds;emit("INITIAL",method,initial[method],sum,seconds,n,64,0,0);
 }
 // Reference is isolated from every online search state and is computed after initial outputs.
 for(size_t i=0;i<qs.size();++i){Search s;s.answer=truth_one(x,qs[i],n,ks[i],alive);reference.push_back(s);}
 for(auto&m:methods)assert(flattened(initial[m])==flattened(reference));write_hits(out+"/INITIAL_REFERENCE.bin",flattened(reference));
 vector<vector<int>>postings(n);auto postStart=Clock::now();for(size_t i=0;i<reference.size();++i)for(auto [d,src,id]:initial.at("RETAIN_FRONTIER")[i].answer)postings[id].push_back(i);
 uint64_t postBytes=postings.capacity()*sizeof(vector<int>);for(auto&p:postings)postBytes+=p.capacity()*sizeof(int);ofstream pf(out+"/POSTINGS.csv");pf<<setprecision(17)<<"entries,bytes,seconds\n1360,"<<postBytes<<','<<elapsed(postStart)<<'\n';pf.close();
 vector<int>permutation=base;mt19937_64 rng(2026102151);shuffle(permutation.begin(),permutation.end(),rng);map<string,vector<int>>deletions;
 deletions["RANDOM256"]=vector<int>(permutation.begin(),permutation.begin()+256);set<int>chosen;vector<int>target;
 for(int rank=0;rank<64;++rank)for(size_t i=0;i<qs.size();++i)if(rank<int(reference[i].answer.size())){int id=get<2>(reference[i].answer[rank]);if(chosen.insert(id).second)target.push_back(id);}
 deletions["DRAIN_OLD_TOPK"]=target;for(int id:permutation)if(target.size()<256&&chosen.insert(id).second)target.push_back(id);assert(target.size()>=256);deletions["TARGET256"]=vector<int>(target.begin(),target.begin()+256);
 shuffle(permutation.begin(),permutation.end(),rng);deletions["RANDOM_MATCHED"]=vector<int>(permutation.begin(),permutation.begin()+deletions["DRAIN_OLD_TOPK"].size());
 for(auto&[episode,ids]:deletions){assert(set<int>(ids.begin(),ids.end()).size()==ids.size());ofstream df(out+"/"+episode+".delete");for(int id:ids)df<<id<<'\n';assert(df);}
 cout<<"DELETE_PLANS_FROZEN "<<name<<" before post-update work\n"<<flush;
 for(const string&episode:{"RANDOM256","TARGET256","DRAIN_OLD_TOPK","RANDOM_MATCHED"}){
  const auto&del=deletions[episode];map<string,vector<Search>>after;map<string,Work>after_work;
  for(const auto&method:methods){if(method=="FIXED_TREE_THRESHOLD_ORACLE")continue;
   vector<Search>states=initial.at(method);vector<char>live(n,1),affected(qs.size(),0);auto start=Clock::now();uint64_t visits=0;
   for(int id:del){live[id]=0;for(int qi:postings[id]){affected[qi]=1;++visits;}}double mutation=elapsed(start);Work sum;
   if(method=="QUICKJOIN_TOPK_SEEDED")states=qjoin_topk(x,qs,ks,live,affected,&states,sum);
   else for(size_t i=0;i<qs.size();++i){if(!affected[i])continue;Work w;Search s=states[i];
    if(method=="GTS_CACHED_ROOT_RESTART"){s=fresh(n);for(auto [d,src,id]:states[i].answer)if(live[id])remember(s,id,d);}
    if(method=="FULL_RANK_CACHE"){s.answer.clear();for(auto key:s.ranking){++w.known_scans;if(live[get<2>(key)])s.answer.push_back(key);if(int(s.answer.size())==ks[i])break;}assert(int(s.answer.size())==ks[i]);}else continue_search(x,tree,qs[i],ks[i],live,s,w);
    uint64_t floor=0;for(auto [d,src,id]:s.answer)floor+=initial.at(method)[i].score[id]<0;
    work<<episode<<','<<method<<','<<i<<','<<ks[i]<<','<<w.metric<<','<<w.bound_metric<<','<<w.verify_metric<<','<<w.node_pops<<','<<w.point_visits<<','<<w.known_scans<<','<<floor<<'\n';sum+=w;states[i]=std::move(s);}
   double seconds=elapsed(start);after_work[method]=sum;after[method]=std::move(states);emit(episode,method,after[method],sum,seconds,n-del.size(),count(affected.begin(),affected.end(),1),mutation,visits);
  }
  // Future truth becomes visible only to posthoc verification and the explicitly labeled oracle.
  vector<char>live(n,1),affected(qs.size(),0);for(int id:del){live[id]=0;for(int qi:postings[id])affected[qi]=1;}
  vector<Search>truth;for(size_t i=0;i<qs.size();++i){Search s;s.answer=truth_one(x,qs[i],n,ks[i],live);truth.push_back(s);}
  for(auto&[method,states]:after)assert(flattened(states)==flattened(truth));write_hits(out+"/"+episode+"_REFERENCE.bin",flattened(truth));
  auto states=initial.at("RETAIN_FRONTIER");auto start=Clock::now();Work sum;
  for(size_t i=0;i<qs.size();++i)if(affected[i]){Work w;continue_search(x,tree,qs[i],ks[i],live,states[i],w,tau(truth[i].answer));sum+=w;
   uint64_t floor=0;for(auto [d,src,id]:truth[i].answer)floor+=initial.at("RETAIN_FRONTIER")[i].score[id]<0;
   work<<episode<<",FIXED_TREE_THRESHOLD_ORACLE,"<<i<<','<<ks[i]<<','<<w.metric<<','<<w.bound_metric<<','<<w.verify_metric<<','<<w.node_pops<<','<<w.point_visits<<','<<w.known_scans<<','<<floor<<'\n';}
  double seconds=elapsed(start);assert(flattened(states)==flattened(truth));emit(episode,"FIXED_TREE_THRESHOLD_ORACLE",states,sum,seconds,n-del.size(),count(affected.begin(),affected.end(),1),0,0);
  Diag d=diagnose(x,tree,ks,initial.at("RETAIN_FRONTIER"),truth,live,diag,episode);assert(d.affected==uint64_t(count(affected.begin(),affected.end(),1)));
  episodes<<episode<<','<<del.size()<<','<<d.affected<<','<<d.tau_up<<','<<d.removed<<','<<d.replacements<<','<<d.stale_nodes<<','<<d.stale_live<<','<<d.stale_unknown<<','<<d.unique_nodes<<','<<d.shared_nodes<<','<<d.unique_candidates<<'\n';episodes.flush();
  cout<<"EPISODE_PASS "<<name<<' '<<episode<<" affected="<<d.affected<<" tau_up="<<d.tau_up<<" reopened="<<d.stale_nodes<<" unknown_pairs="<<d.stale_unknown<<" online="<<after_work.at("RETAIN_FRONTIER").metric<<" oracle="<<sum.metric<<'\n'<<flush;
 }
 assert(costs&&work&&diag&&episodes);cout<<"POPULATION_PASS "<<name<<";30 complete method streams;0GPU\n";return 0;
}
