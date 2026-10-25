#include "bench_io.hpp"
#include <thrust/iterator/counting_iterator.h>

void load_case_data(const char* path,bool words){
 if(words){load(const_cast<char*>(path),data_info,data_d,data_s,size_s);assert(data_info[2]==6);}
 else{std::ifstream f(path,std::ios::binary);assert(f);int h[3];f.read((char*)h,12);assert(f&&h[2]==2&&h[0]==2&&h[1]>0);ck(cudaMallocManaged(&data_info,12));std::copy(h,h+3,data_info);ck(cudaMallocManaged(&data_d,size_t(h[0])*h[1]*4));f.read((char*)data_d,size_t(h[0])*h[1]*4);assert(f);data_s=nullptr;size_s=nullptr;}
}
__device__ int rolling_edit(const char* a,int n,const char* b,int m){
 if(m>n){const char* t=a;a=b;b=t;int z=n;n=m;m=z;}uint16_t row0[41],row1[41];uint16_t* p=row0;uint16_t* c=row1;
 for(int j=0;j<=m;++j)p[j]=j;for(int i=1;i<=n;++i){c[0]=i;for(int j=1;j<=m;++j)c[j]=min(min(p[j]+1,c[j-1]+1),p[j-1]+(a[i-1]!=b[j-1]));auto t=p;p=c;c=t;}return p[m];
}
__global__ void scan_batch(int n,int nq,const int* qs,float radius,const float* x,const char* strings,const int* lens,Hit* raw,unsigned char* flags){
 const int k=blockIdx.x*blockDim.x+threadIdx.x;
 if(threadIdx.x==0)COUNT(9,blockDim.x);
 if(k>=n*nq)return;COUNT(8,1);int qi=k/n,id=k%n,q=qs[qi];float d=0;
 if(strings){COUNT(7,1);COUNT(2,size_t(lens[id])*lens[q]);d=rolling_edit(strings+size_t(id)*M,lens[id],strings+size_t(q)*M,lens[q]);}
 else if(id!=q){COUNT(7,1);COUNT(3,2);for(int j=0;j<2;++j)d+=pow(x[size_t(id)*2+j]-x[size_t(q)*2+j],2);d=pow(d,0.5);}
 flags[k]=d<=radius;if(flags[k])raw[k]={k,d};
}
struct Scan {
 int n,nq,*qs,*hc,*count;int* hqs;Hit *raw,*selected;unsigned char* flags;void* temp;size_t bytes=0;cudaStream_t stream;
 Scan(int n_,int q_):n(n_),nq(q_){assert(int64_t(n)*nq<INT32_MAX);size_t total=size_t(n)*nq;ck(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));alloc(qs,nq);alloc(count,1);alloc(raw,total);alloc(selected,total);alloc(flags,total);ck(cudaMallocHost(&hc,4));ck(cudaMallocHost(&hqs,nq*4));ck(cub::DeviceSelect::Flagged(nullptr,bytes,raw,flags,selected,count,int(total),stream));ck(cudaMalloc(&temp,bytes));}
 Outputs query(const Case& c){std::copy(c.qs.begin(),c.qs.end(),hqs);ck(cudaMemcpyAsync(qs,hqs,nq*4,cudaMemcpyHostToDevice,stream));int total=n*nq;
 scan_batch<<<(total+127)/128,128,0,stream>>>(n,nq,qs,c.radius,data_d,data_s,size_s,raw,flags);ck(cudaGetLastError());ck(cub::DeviceSelect::Flagged(temp,bytes,raw,flags,selected,count,total,stream));ck(cudaMemcpyAsync(hc,count,4,cudaMemcpyDeviceToHost,stream));ck(cudaStreamSynchronize(stream));assert(*hc>=0&&*hc<=total);
 std::vector<Hit> flat(*hc);if(*hc)ck(cudaMemcpy(flat.data(),selected,size_t(*hc)*8,cudaMemcpyDeviceToHost));Outputs out(nq);auto begin=flat.begin();
 for(int qi=0;qi<nq;++qi){auto end=std::lower_bound(begin,flat.end(),int64_t(qi+1)*n,[](Hit h,int64_t key){return h.id<key;});out[qi].assign(begin,end);for(auto& h:out[qi])h.id-=qi*n;begin=end;}assert(begin==flat.end());return out;}
 ~Scan(){for(void* p:{(void*)qs,(void*)count,(void*)raw,(void*)selected,(void*)flags,temp})ck(cudaFree(p));ck(cudaFreeHost(hc));ck(cudaFreeHost(hqs));ck(cudaStreamDestroy(stream));}
};
int main(int argc,char**argv){
 assert(argc==11);std::string kind=argv[1],arm=argv[5],prefix=argv[9];int q=std::stoi(argv[4]),k=std::stoi(argv[6]),reps=std::stoi(argv[7]),warm=std::stoi(argv[8]);bool dump=std::stoi(argv[10]);
 assert((kind=="words"||kind=="tloc")&&(arm=="A"||arm=="R"||arm=="S")&&reps>=0&&warm>=0);{std::ofstream pf(prefix+".pid");pf<<getpid()<<'\n';}
 Case c(argv[3],q,k);RunLog log(prefix);ck(cudaSetDevice(0));load_case_data(argv[2],kind=="words");assert(data_info[1]==c.n);
 Fixed* fixed=nullptr;Scan* scan=nullptr;std::vector<int> hi;std::vector<float> hd;
 if(arm!="S"){
  MAX_H=1;for(int worst=c.n;worst>20;worst-=9*(worst/10))++MAX_H;auto t=WallClock::now();indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);ck(cudaDeviceSynchronize());log.build=millis(t);assert(tree_h==MAX_H);
  query_slots=max_node_num[0]*MAX_SIZE;tree_size=c.n;qnum_leaf=1;alloc(is_delete,c.n);alloc(is_delete_prefix,c.n);ck(cudaMemset(is_delete,0,c.n*4));ck(cudaMallocManaged(&qid_list,4));hi.resize(query_slots);hd.resize(query_slots);
  // Tree structure is audited separately from the unchanged original builder.
  std::vector<TN> nodes(max_node_num[0]);ck(cudaMemcpy(nodes.data(),node_list,nodes.size()*sizeof(TN),cudaMemcpyDeviceToHost));std::vector<int> empty(nodes.size());ck(cudaMemcpy(empty.data(),empty_list,empty.size()*4,cudaMemcpyDeviceToHost));int leaves=0;for(size_t i=0;i<nodes.size();++i)if(!empty[i]&&nodes[i].is_leaf){assert(nodes[i].size<=MAX_SIZE);++leaves;}assert(leaves>0);
 }
 auto t=WallClock::now();if(arm=="R"){fixed=new Fixed(c.n,tree_h,true);*fixed->hq=c.qs[0];log.capture=fixed->capture(c.radius)*1000;}if(arm=="S")scan=new Scan(c.n,c.nq);log.setup=millis(t);
 auto call=[&](bool native){
#if INSTRUMENT
  unsigned long long zero[10]={};ck(cudaMemcpyToSymbol(work,zero,sizeof(zero)));
#endif
  Outputs out(c.nq);
  if(scan)out=scan->query(c);else for(int qi=0;qi<c.nq;++qi){int count;const int* ids;const float* ds;if(fixed){fixed->query(c.qs[qi],c.radius,true);count=*fixed->hc;ids=fixed->hi;ds=fixed->hd;}else{original_query(c.qs[qi],c.radius,count,hi,hd);ids=hi.data();ds=hd.data();}out[qi].resize(count);for(int j=0;j<count;++j)out[qi][j]={ids[j],ds[j]};}
  if(native)dump_output(prefix+".native.bin",out);
  canonicalize(out);return out;};
 run_case(call,c,log,reps,warm,dump);log.finish(arm,c);
#if INSTRUMENT
 unsigned long long counts[10];ck(cudaMemcpyFromSymbol(counts,work,sizeof(counts)));std::ofstream wf(prefix+".work.json");const char* names[]={"node_distance_calls","leaf_distance_calls","dp_cells","coordinates","candidate_leaves","active_leaf_threads","launched_leaf_threads","scan_distance_calls","active_scan_threads","launched_scan_threads"};wf<<'{';for(int i=0;i<10;++i){if(i)wf<<',';wf<<'"'<<names[i]<<"\":"<<counts[i];}wf<<"}\n";
#endif
 delete fixed;delete scan;std::cout<<"PASS "<<arm<<" Q="<<q<<" r="<<c.radius<<" instrument="<<INSTRUMENT<<"\n";return 0;
}
