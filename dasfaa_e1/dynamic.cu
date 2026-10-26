#include "case.hpp"
#include <cuda_runtime.h>
#include <unistd.h>
#include <climits>
#include <thrust/device_ptr.h>
#include <thrust/sort.h>
#include <thrust/sequence.h>
inline void ck(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T>void alloc(T*&p,size_t n){ck(cudaMalloc(&p,std::max(size_t(1),n)*sizeof(T)));}
__device__ float e1_tanimoto(const float*a,const float*b,int n){int inter=0,un=0;for(int j=0;j<n;++j){bool x=a[j]!=0,y=b[j]!=0;inter+=x&&y;un+=x||y;}return un?1.f-float(inter)/un:0.f;}
#if BACKEND == 1
#include "native_g/update.cuh"
#include "native_g/search_v2.cuh"
#elif BACKEND == 2
#include "native_p/update.cuh"
#include "native_p/search_v2.cuh"
#endif
#ifdef short
#undef short
#endif
__device__ int rolling_edit_e1(const char*a,const char*b){int n=0,m=0;while(a[n])++n;while(b[m])++m;
 if(m>n){auto t=a;a=b;b=t;int v=n;n=m;m=v;}uint16_t rows[2][109];uint16_t*p=rows[0],*q=rows[1];
 for(int j=0;j<=m;++j)p[j]=j;for(int i=1;i<=n;++i){q[0]=i;for(int j=1;j<=m;++j)q[j]=min(min(int(p[j])+1,int(q[j-1])+1),int(p[j-1])+(a[i-1]!=b[j-1]));auto t=p;p=q;q=t;}return p[m];}
__global__ void scan_e1(int first,int n,int metric,int dim,const float*x,const char*s,const int*dead,
                        const float*qx,const char*qs,float*dist,int*ids){
 int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=n)return;int id=first+j;ids[j]=id;float d=INFINITY;
 if(!dead[id]){d=0;if(metric==6)d=rolling_edit_e1(s+size_t(id)*109,qs);else if(metric==8)d=e1_tanimoto(x+size_t(id)*dim,qx,dim);
 else{for(int k=0;k<dim;++k){float z=x[size_t(id)*dim+k]-qx[k];d+=z*z;}d=sqrtf(d);}}
 dist[j]=d;
}
struct Store {
 const Case&c;float*x=nullptr,*qx=nullptr,*dist=nullptr;char*s=nullptr,*qs=nullptr;int*ids=nullptr;
 int*dead=nullptr;int next=0,cap;std::vector<unsigned char>hdead,seen;std::vector<float>last_distances;
 explicit Store(const Case&c_):c(c_),cap(c.nb+c.na),hdead(cap,1),seen(cap,0){
  if(c.metric==6){alloc(s,size_t(cap)*109);alloc(qs,109);}else{alloc(x,size_t(cap)*c.dim);alloc(qx,c.dim);}
  alloc(dist,cap);alloc(ids,cap);alloc(dead,cap);ck(cudaMemset(dead,1,cap*4));
  for(int i=0;i<c.nb;++i)append(i,i);
 }
 void append(int uid,int payload){require(uid==next&&uid<cap&&!seen[uid],"fresh unique ID/append order");
  if(c.metric==6)ck(cudaMemcpy(s+size_t(uid)*109,c.sp(payload),109,cudaMemcpyHostToDevice));
  else ck(cudaMemcpy(x+size_t(uid)*c.dim,c.xp(payload),c.dim*4,cudaMemcpyHostToDevice));
  int zero=0;ck(cudaMemcpy(dead+uid,&zero,4,cudaMemcpyHostToDevice));hdead[uid]=0;seen[uid]=1;++next;
 }
 void erase(int uid){require(uid>=0&&uid<next&&!hdead[uid],"delete active ID");int one=1;
  ck(cudaMemcpy(dead+uid,&one,4,cudaMemcpyHostToDevice));hdead[uid]=1;
 }
 void input_query(int qid){int row=c.nb+c.na+qid;require(qid>=0&&qid<c.nq,"query ID");
  if(c.metric==6)ck(cudaMemcpy(qs,c.sp(row),109,cudaMemcpyHostToDevice));else ck(cudaMemcpy(qx,c.xp(row),c.dim*4,cudaMemcpyHostToDevice));
 }
 std::vector<int>scan(int first){int n=next-first;std::vector<int>out;last_distances.clear();if(!n)return out;
  scan_e1<<<(n+127)/128,128>>>(first,n,c.metric,c.dim,x,s,dead,qx,qs,dist,ids);ck(cudaGetLastError());
  thrust::sort_by_key(thrust::device_pointer_cast(dist),thrust::device_pointer_cast(dist)+n,thrust::device_pointer_cast(ids));
  int count=std::min(n,c.k);std::vector<float>d(count);out.resize(count);ck(cudaMemcpy(out.data(),ids,count*4,cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(d.data(),dist,count*4,cudaMemcpyDeviceToHost));while(!d.empty()&&!std::isfinite(d.back())){d.pop_back();out.pop_back();}last_distances=d;ck(cudaDeviceSynchronize());return out;
 }
 ~Store(){for(void*p:{(void*)x,(void*)qx,(void*)s,(void*)qs,(void*)dist,(void*)ids,(void*)dead})if(p)cudaFree(p);}
};
#if BACKEND
__global__ void gather_e1(int n,int dim,int metric,const int*map,const float*x,const char*s,
                           float*tx,char*ts,int*lens){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;int src=map[i];
 if(metric==6){int len=0;for(int j=0;j<109;++j){char z=s[size_t(src)*109+j];ts[size_t(i)*109+j]=z;if(z)++len;}lens[i]=len;}
 else for(int j=0;j<dim;++j)tx[size_t(i)*dim+j]=x[size_t(src)*dim+j];}
struct NativeTree {
 Store&store;const Case&c;float*tx=nullptr;char*ts=nullptr;int*lens=nullptr,*info=nullptr,*labels=nullptr;
 int*index=nullptr,*nodes_count=nullptr,*empty=nullptr,*qid=nullptr,*count=nullptr,*prefix=nullptr,*rid=nullptr,*knn_ids=nullptr;float*rdis=nullptr;
 TN*nodes=nullptr;int h=0,n=0,consolidated=0,live_delta=0,deleted_tree=0,last_native_k=0;std::vector<int>mapping,last_tree_ids;std::vector<float>last_tree_distances,last_distances;float last_radius=0;double stall=0;int rebuilds=0;
 explicit NativeTree(Store&s):store(s),c(s.c){ck(cudaMallocManaged(&info,12));info[0]=c.dim;info[2]=c.metric;ck(cudaMallocManaged(&qid,4));rebuild(false);}
 void release_tree(){for(void*p:{(void*)tx,(void*)ts,(void*)lens,(void*)labels,(void*)index,(void*)nodes_count,(void*)empty,(void*)nodes,(void*)knn_ids})if(p)ck(cudaFree(p));tx=nullptr;ts=nullptr;lens=nullptr;labels=nullptr;index=nullptr;nodes_count=nullptr;empty=nullptr;nodes=nullptr;knn_ids=nullptr;}
 void rebuild(bool triggered){auto start=Clock::now();release_tree();mapping.clear();for(int i=0;i<store.next;++i)if(!store.hdead[i])mapping.push_back(i);
  n=mapping.size();require(n>0,"native empty tree is not supported");info[1]=n;alloc(knn_ids,n);alloc(labels,n);ck(cudaMemcpy(labels,mapping.data(),n*4,cudaMemcpyHostToDevice));
  ck(cudaMemcpyToSymbol(e1_stable_ids,&labels,sizeof labels));
  if(c.metric==6){alloc(ts,size_t(n+1)*109);alloc(lens,n+1);}else alloc(tx,size_t(n+1)*c.dim);
  gather_e1<<<(n+127)/128,128>>>(n,c.dim,c.metric,labels,store.x,store.s,tx,ts,lens);ck(cudaGetLastError());ck(cudaDeviceSynchronize());
  MAX_H=1;for(int worst=n;worst>MAX_SIZE;worst-=(TREE_ORDER-1)*(worst/TREE_ORDER))++MAX_H;
  indexConstru(tx,ts,lens,info,index,nodes,nodes_count,h,empty);ck(cudaDeviceSynchronize());
  std::vector<TN>hn(nodes_count[0]);std::vector<int>he(nodes_count[0]);ck(cudaMemcpy(hn.data(),nodes,hn.size()*sizeof(TN),cudaMemcpyDeviceToHost));ck(cudaMemcpy(he.data(),empty,he.size()*4,cudaMemcpyDeviceToHost));
  for(size_t i=0;i<hn.size();++i)if(!he[i]&&hn[i].is_leaf)require(hn[i].size<=MAX_SIZE,"native leaf exceeds query stride");
  consolidated=store.next;live_delta=0;deleted_tree=0;if(triggered){stall+=elapsed(start);++rebuilds;}
 }
 void input_tree_query(int query_id){int src=c.nb+c.na+query_id;
  if(c.metric==6){ck(cudaMemcpy(ts+size_t(n)*109,c.sp(src),109,cudaMemcpyHostToDevice));int len=strlen(c.sp(src));ck(cudaMemcpy(lens+n,&len,4,cudaMemcpyHostToDevice));}
  else ck(cudaMemcpy(tx+size_t(n)*c.dim,c.xp(src),c.dim*4,cudaMemcpyHostToDevice));
 }
 std::vector<int>range_tree(int query_id,float radius){
  input_tree_query(query_id);
  qid[0]=n;is_delete=store.dead;
  qnum_leaf=1;
  searchIndexRnnUpdate(tx,nodes,index,nodes_count,qid,1,radius,h,info,empty,count,prefix,rid,rdis,ts,lens);ck(cudaDeviceSynchronize());
  int nr=count[0];require(nr>=0&&nr<=n,"native result count");std::vector<int>phys(nr);if(nr)ck(cudaMemcpy(phys.data(),rid,nr*4,cudaMemcpyDeviceToHost));
  std::vector<int>out;for(int id:phys){require(id>=0&&id<n,"native physical result ID");out.push_back(mapping[id]);}
  last_tree_ids=out;last_radius=radius;
#if BACKEND == 1
  for(void*p:{(void*)rid,(void*)rdis,(void*)count,(void*)prefix})if(p)ck(cudaFree(p));rid=nullptr;rdis=nullptr;count=nullptr;prefix=nullptr;
#endif
  return out;
 }
 std::vector<int>query(int query_id){
#if BACKEND == 1
  input_tree_query(query_id);
#else
  if(c.metric==6)input_tree_query(query_id);
#endif
  // Overfetch every tombstone so unchanged native pruning still bounds live k.
  last_native_k=std::min(n,c.k+deleted_tree);
  ck(cudaMemset(knn_ids,0xff,size_t(last_native_k)*sizeof(int)));
#if BACKEND == 2
  if(c.metric!=6)searchIndexKnnV2(tx,nodes,index,nodes_count,store.qx,knn_ids,1,last_native_k,h,info,empty,ts,lens);
  else
#endif
  {qid[0]=n;searchIndexKnnV2(tx,nodes,index,nodes_count,qid,knn_ids,1,last_native_k,h,info,empty,ts,lens);}
  ck(cudaGetLastError());ck(cudaDeviceSynchronize());
  std::vector<int>physical(last_native_k);std::vector<float>distance(last_native_k);
  ck(cudaMemcpy(physical.data(),knn_ids,size_t(last_native_k)*sizeof(int),cudaMemcpyDeviceToHost));
  ck(cudaMemcpy(distance.data(),res_dis,size_t(last_native_k)*sizeof(float),cudaMemcpyDeviceToHost));
  ck(cudaFree(res_dis));res_dis=nullptr;
  last_tree_ids.clear();last_tree_distances.clear();std::vector<std::pair<float,int>>scored;
  for(int j=0;j<last_native_k;++j){int id=physical[j];require(id>=0&&id<n,"native physical kNN result ID");
   int stable=mapping[id];last_tree_ids.push_back(stable);last_tree_distances.push_back(distance[j]);
   if(!store.hdead[stable]){require(std::isfinite(distance[j])&&distance[j]>=0&&distance[j]<INFI_DIS,"native live kNN distance");scored.push_back({distance[j],stable});}}
  auto delta=store.scan(consolidated);
  for(size_t j=0;j<delta.size();++j)scored.push_back({store.last_distances[j],delta[j]});
  int keep=std::min(size_t(c.k),scored.size());std::partial_sort(scored.begin(),scored.begin()+keep,scored.end());
  std::vector<int>out(keep);last_distances.resize(keep);
  for(int j=0;j<keep;++j){out[j]=scored[j].second;last_distances[j]=scored[j].first;}return out;
 }

};
#endif
int main(int argc,char**argv){try{require(argc==6,"usage: binary case.bin arm B output-prefix max-events(0=all)");oracle_selftest();Case c(argv[1]);std::string arm=argv[2],out=argv[4];int B=std::stoi(argv[3]),limit=std::stoi(argv[5]);require(B>0,"B positive");
 {std::ofstream pid(out+".pid");require(bool(pid),"PID output file");pid<<getpid()<<'\n';}
 std::cout<<std::unitbuf;std::cerr<<std::unitbuf;
 require(size_t(c.nb)+size_t(c.na)<=10000000,"N exceeds frozen 10M resource cap");
 require(c.metric==6||(size_t(c.nb)+size_t(c.na)+1)*size_t(c.dim)<=size_t(INT_MAX),"native int32 row-dimension indexing overflow");
 require((BACKEND==0&&arm=="D")||(BACKEND==1&&(arm=="G"||arm=="GB"))||(BACKEND==2&&arm=="P"),"arm/backend mismatch");
 Store store(c);double build=0;
#if BACKEND
 auto bt=Clock::now();NativeTree tree(store);build=elapsed(bt);
#endif
 std::ofstream queries(out+".queries.jsonl"),events(out+".events.csv");require(bool(queries)&&bool(events),"output files");events<<"seq,op,snapshot,active,delta,wall_s,stall_s\n";
 int invalid=0,misses=0,nqueries=0,snapshot=0;double recall=0;std::vector<double>lat[3];std::vector<unsigned char>active(c.nb+c.na,0);std::fill(active.begin(),active.begin()+c.nb,1);
 for(int seq=0;seq<c.ne&&(!limit||seq<limit);++seq){auto e=c.events[seq];require(e.op>=0&&e.op<3,"event op");std::vector<int>result;std::vector<float>result_distances;auto t=Clock::now();double stall=0;
 if(e.op==0){require(e.id>=c.nb&&e.id<c.nb+c.na&&e.offset==e.id-c.nb,"arrival payload/ID");store.append(e.id,c.nb+e.offset);active[e.id]=1;++snapshot;
#if BACKEND
 if(++tree.live_delta>=B){double before=tree.stall;tree.rebuild(true);stall=tree.stall-before;}
#endif
 }else if(e.op==1){
#if BACKEND
 if(e.id>=tree.consolidated)--tree.live_delta;else ++tree.deleted_tree;
#endif
 store.erase(e.id);active[e.id]=0;++snapshot;}else{
 store.input_query(e.qid);
#if BACKEND
 result=tree.query(e.qid);result_distances=tree.last_distances;
#else
 result=store.scan(0);result_distances=store.last_distances;
#endif
 }
 ck(cudaDeviceSynchronize());double duration=elapsed(t);lat[e.op].push_back(duration);require(snapshot==e.snapshot,"required snapshot");
 int active_count=std::accumulate(active.begin(),active.end(),0);
 events<<seq<<','<<e.op<<','<<snapshot<<','<<active_count<<',';
#if BACKEND
 events<<tree.live_delta;
#else
 events<<store.next-c.nb;
#endif
 events<<','<<std::setprecision(12)<<duration<<','<<stall<<'\n';
 if(e.op==2){++nqueries;int q=c.nb+c.na+e.qid;std::vector<std::pair<double,int>>oracle;oracle.reserve(active_count);
 for(int id=0;id<store.next;++id)if(active[id])oracle.push_back({cpu_distance(c,id,q),id});require(oracle.size()>=size_t(c.k),"oracle active k");
 std::partial_sort(oracle.begin(),oracle.begin()+c.k,oracle.end());double kth=oracle[c.k-1].first;std::set<int>unique;int hits=0,bad=0;
 for(int id:result){if(id<0||id>=store.next||!active[id]||!unique.insert(id).second){++bad;continue;}if(cpu_distance(c,id,q)<=kth*(1+1e-5))++hits;}
 if(result.size()!=size_t(c.k))bad+=abs(int(result.size())-c.k);invalid+=bad;misses+=c.k-hits;recall+=double(hits)/c.k;
 queries<<"{\"seq\":"<<seq<<",\"requested_snapshot\":"<<snapshot<<",\"served_snapshot\":"<<snapshot<<",\"active\":"<<active_count<<",\"ids\":[";
 for(size_t i=0;i<result.size();++i){if(i)queries<<',';queries<<result[i];}queries<<"],\"distances\":[";for(size_t i=0;i<result_distances.size();++i){if(i)queries<<',';queries<<std::setprecision(12)<<result_distances[i];}queries<<"]";
#if BACKEND
 queries<<",\"native_tree_k\":"<<tree.last_native_k<<",\"native_tree_ids\":[";
 for(size_t i=0;i<tree.last_tree_ids.size();++i){if(i)queries<<',';queries<<tree.last_tree_ids[i];}
 queries<<"],\"native_tree_distances\":[";for(size_t i=0;i<tree.last_tree_distances.size();++i){if(i)queries<<',';queries<<std::setprecision(12)<<tree.last_tree_distances[i];}
 queries<<"],\"native_tree_consolidated_before_slot\":"<<tree.consolidated;
#endif
 queries<<",\"oracle_topk_ids\":[";for(int j=0;j<c.k;++j){if(j)queries<<',';queries<<oracle[j].second;}queries<<"],\"oracle_kth\":"<<std::setprecision(17)<<kth<<",\"tie_recall\":"<<double(hits)/c.k<<",\"invalid\":"<<bad<<"}\n";
 }
 }
 std::ofstream summary(out+".json");summary<<"{\"arm\":\""<<arm<<"\",\"timing_eligible\":false,\"scope\":\"smoke_correctness_only\",\"native_static_knn_executed\":"<<((BACKEND&&nqueries)?"true":"false")<<",\"queries\":"<<nqueries<<",\"invalid_ids\":"<<invalid<<",\"missing\":"<<misses<<",\"tie_recall\":"<<std::setprecision(12)<<(nqueries?recall/nqueries:1)<<",\"build_s\":"<<build;
#if BACKEND
 summary<<",\"rebuilds\":"<<tree.rebuilds<<",\"stall_s\":"<<tree.stall;
#endif
 summary<<",\"valid_ids\":"<<(invalid?"false":"true")<<",\"correct\":"<<((invalid==0&&misses==0)?"true":"false")<<"}\n";
 std::cout<<"COMPLETE "<<arm<<" queries="<<nqueries<<" invalid="<<invalid<<" missing="<<misses<<"\n";return invalid?3:0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 2;}}
