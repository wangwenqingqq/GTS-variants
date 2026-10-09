// B1 full-delivery adapter; native author partitioning, kernels and pruning remain.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>
struct BPlusNode;
void closure_capture_nodes(BPlusNode**,int);
#include "search.cuh"
#undef short
static std::vector<BPlusNode*> allocation_owners;
void closure_capture_nodes(BPlusNode** p,int n){allocation_owners.assign(p,p+n);}
using Clock=std::chrono::steady_clock;
static void checked(cudaError_t e,const char* call,int line){if(e!=cudaSuccess)throw std::runtime_error(std::string(call)+" at "+std::to_string(line)+": "+cudaGetErrorString(e));}
#define ck(e) checked(e,#e,__LINE__)
static double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
template<class T> void alloc(T*& p,size_t n,bool managed=false){
    if(!n)throw std::runtime_error("zero native allocation: unsupported source path");
    if(managed)ck(cudaMallocManaged(&p,n*sizeof(T)));else ck(cudaMalloc(&p,n*sizeof(T)));
}
template<class T> void drop(T*& p){if(p){ck(cudaFree(p));p=nullptr;}}
struct Delivered {std::vector<int> ids;std::vector<float> fields;int selected_trees;};
struct TreeService {
    int n,d,*info=nullptr,*pid=nullptr,*part=nullptr,*qid=nullptr,*satisfied=nullptr;
    int *trees=nullptr,*tree_prefix=nullptr,*nodes=nullptr,*node_prefix=nullptr;
    int total_trees=0,total_nodes=0;
    float *data=nullptr,*radius=nullptr,*pivot_distance=nullptr;
    Obj object{}; BPlusNode** root=nullptr;
    bool native_called=false;
    void build(const std::vector<float>& host,int count,int dim){
        n=count;d=dim;if(n<8)throw std::runtime_error("native PNUM8 requires N>=8; small-N capability not admitted");
        PNUM=8;ck(cudaDeviceSetLimit(cudaLimitMallocHeapSize,size_t(1)<<30));
        alloc(info,3,true);info[0]=d;info[1]=n;info[2]=2;
        alloc(data,host.size());ck(cudaMemcpy(data,host.data(),host.size()*4,cudaMemcpyHostToDevice));
        alloc(qid,1,true);alloc(pid,PNUM,true);alloc(part,PNUM);
        alloc(object.dis,n);alloc(object.res_id,n);alloc(radius,PNUM);
        alloc(pivot_distance,PNUM);alloc(satisfied,PNUM);
        Obj temporary{};alloc(temporary.dis,n);alloc(temporary.res_id,n);alloc(temporary.flag,n);
        getPivot(data,info,pid,PNUM,temporary,nullptr,nullptr);ck(cudaDeviceSynchronize());
        getPartition(n,object,temporary,PNUM,part,radius);ck(cudaDeviceSynchronize());
        drop(temporary.dis);drop(temporary.res_id);drop(temporary.flag);
        getIndex(root,part,object,total_nodes,trees,tree_prefix,total_trees,nodes,node_prefix);ck(cudaDeviceSynchronize());
    }
    Delivered query(int row,int task,float r,int k){
        if(row<0||row>=n||k<1||k>PNUM||!std::isfinite(r))throw std::runtime_error("invalid query");
#ifndef CLOSURE_REUSE
        if(native_called)throw std::runtime_error("native mode permits only one call");
#endif
        qid[0]=row;int *counts=nullptr,*prefix=nullptr,*results=nullptr,*ids=nullptr;
        float* dist=nullptr;Obj found{};
        search(data,pid,qid,1,pivot_distance,info,r,radius,satisfied,trees,root,tree_prefix,node_prefix,
               counts,prefix,results,found,task,k,dist,ids,nullptr,nullptr);
        ck(cudaDeviceSynchronize());ck(cudaGetLastError());native_called=true;
        int c=counts[0];if(prefix[0]!=0||c<0||c>total_trees)throw std::runtime_error("invalid candidate tree capacity");
        Delivered out;out.selected_trees=c;
        if(task==0){
            if(c*k<k)throw std::runtime_error("native kNN produced insufficient candidates");
            out.ids.resize(k);out.fields.resize(k);
            ck(cudaMemcpy(out.ids.data(),ids,k*4,cudaMemcpyDeviceToHost));
            ck(cudaMemcpy(out.fields.data(),dist,k*4,cudaMemcpyDeviceToHost));
            for(int id:out.ids)if(id<0||id>=n)throw std::runtime_error("missing native kNN member");
        }else{
            std::vector<int> sizes(c);if(c)ck(cudaMemcpy(sizes.data(),results,c*4,cudaMemcpyDeviceToHost));
            size_t total=0;for(int z:sizes){if(z<0||z>DNUM)throw std::runtime_error("range capacity");total+=z;}
            if(total>size_t(n))throw std::runtime_error("range output exceeds snapshot");
            out.ids.resize(total);out.fields.resize(total);size_t at=0;
            for(int i=0;i<c;++i){if(sizes[i]){
                ck(cudaMemcpy(out.ids.data()+at,found.res_id+i*DNUM,sizes[i]*4,cudaMemcpyDeviceToHost));
                ck(cudaMemcpy(out.fields.data()+at,found.dis+i*DNUM,sizes[i]*4,cudaMemcpyDeviceToHost));
            }at+=sizes[i];}
        }
        drop(counts);drop(prefix);drop(results);drop(found.dis);drop(found.res_id);drop(dist);drop(ids);
        ck(cudaDeviceSynchronize());return out;
    }
    void release(){
#ifndef CLOSURE_REUSE
        if(native_called){satisfied=nullptr;trees=nullptr;tree_prefix=nullptr;node_prefix=nullptr;}
#endif
        for(auto& p:allocation_owners)drop(p);allocation_owners.clear();drop(root);
        drop(data);drop(info);drop(pid);drop(part);drop(qid);drop(satisfied);drop(trees);drop(tree_prefix);
        drop(nodes);drop(node_prefix);drop(object.dis);drop(object.res_id);drop(radius);drop(pivot_distance);
        ck(cudaDeviceSynchronize());
    }
};
int main(int argc,char** argv){try{
    if(argc!=4)throw std::runtime_error("usage: service data.f32bin requests.txt output_prefix");
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);
    if(!f||h[0]<1||h[0]>960||h[1]<0||h[1]>1000000||h[2]!=2)throw std::runtime_error("header");
    std::vector<float> host(size_t(h[0])*h[1]);f.read((char*)host.data(),host.size()*4);
    if(!f||f.peek()!=EOF)throw std::runtime_error("data length");for(float x:host)if(!std::isfinite(x))throw std::runtime_error("nonfinite");
    std::string out=argv[3];std::ifstream requests(argv[2]);int count;requests>>count;if(!requests||count<1||count>80)throw std::runtime_error("request count");
    std::ofstream ids(out+".ids.i32",std::ios::binary),fields(out+".dist.f32",std::ios::binary),rows(out+".queries.csv"),meta(out+".native.json");
    if(!ids||!fields||!rows||!meta)throw std::runtime_error("output open");
    rows<<"task,query,qid,count,offset,ack_ms,selected_trees\n"<<std::setprecision(14);
    TreeService t;auto start=Clock::now();t.build(host,h[1],h[0]);double build_ms=ms(start);size_t offset=0;
    for(int i=0;i<count;++i){int task,row,k;float r;requests>>task>>row>>r>>k;if(!requests||(task!=0&&task!=1))throw std::runtime_error("request");
        start=Clock::now();auto x=t.query(row,task,r,k);double ack=ms(start);
        ids.write((char*)x.ids.data(),x.ids.size()*4);fields.write((char*)x.fields.data(),x.fields.size()*4);
        rows<<(task==0?"knn":"range")<<','<<i<<','<<row<<','<<x.ids.size()<<','<<offset<<','<<ack<<','<<x.selected_trees<<'\n';rows.flush();offset+=x.ids.size();
    }
    start=Clock::now();t.release();double release_ms=ms(start);
    meta<<std::setprecision(14)<<"{\"build_ms\":"<<build_ms<<",\"release_ms\":"<<release_ms<<",\"queries\":"<<count<<",\"PNUM\":8}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
