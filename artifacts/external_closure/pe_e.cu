// Dynamic service adapter, not a claim of native Faiss dynamic support.
#define main closure_range_qualification_main
#include "range_service.cu"
#undef main
#include "pe_common.hpp"
#include <faiss/gpu/GpuDistance.h>
#include <faiss/gpu/StandardGpuResources.h>
#include <faiss/gpu/impl/L2Norm.cuh>
#include <memory>
#include <numeric>
#include <sys/resource.h>
struct DynamicScan:Scan {
    std::unique_ptr<faiss::gpu::StandardGpuResources> faiss;
    float* norms=nullptr;std::vector<int> occurrence,position;int next=0,capacity=0;
    size_t inserted_bytes=0,swapped_bytes=0;int norm_updates=0,swaps=0;
    void norm(int begin,int rows){
        if(!rows)return;
        faiss::gpu::Tensor<float,2,true> x(database+size_t(begin)*d,{rows,d});
        faiss::gpu::Tensor<float,1,true> y(norms+begin,{rows});
        faiss::gpu::runL2Norm(x,true,y,true,stream);++norm_updates;
    }
    void build_live(const std::vector<float>& host,int real_n,int dim){
        capacity=int(host.size()/dim);Scan::build(host,capacity,dim);n=next=real_n;
        occurrence.resize(n);std::iota(occurrence.begin(),occurrence.end(),0);
        occurrence.reserve(capacity);position.assign(capacity,-1);for(int i=0;i<n;i++)position[i]=i;
        faiss=std::make_unique<faiss::gpu::StandardGpuResources>();faiss->setDefaultStream(0,stream);
        alloc(norms,capacity);norm(0,n);ck(cudaStreamSynchronize(stream));
    }
    void insert(int id,const float* v){
        pe::require(id==next&&next<capacity&&n<capacity,"E insertion capacity/ID");
        ck(cudaMemcpyAsync(database+size_t(n)*d,v,size_t(d)*4,cudaMemcpyHostToDevice,stream));
        norm(n,1);position[id]=n;occurrence.push_back(id);++n;++next;inserted_bytes+=size_t(d)*4;
        ck(cudaStreamSynchronize(stream));
    }
    void erase(int id){
        pe::require(id>=0&&id<next&&position[id]>=0,"E delete exact live occurrence");int row=position[id],last=n-1;
        if(row!=last){
            ck(cudaMemcpyAsync(database+size_t(row)*d,database+size_t(last)*d,size_t(d)*4,cudaMemcpyDeviceToDevice,stream));
            ck(cudaMemcpyAsync(norms+row,norms+last,4,cudaMemcpyDeviceToDevice,stream));
            occurrence[row]=occurrence[last];position[occurrence[row]]=row;swapped_bytes+=size_t(d)*4+4;++swaps;
        }
        occurrence.pop_back();position[id]=-1;--n;ck(cudaStreamSynchronize(stream));
    }
    void knn(const float* q,std::vector<int>& ids,std::vector<float>& dist,std::vector<double>& raw){
        ids.assign(8,-1);dist.assign(8,INFINITY);raw.assign(8,INFINITY);if(!n)return;
        ck(cudaMemcpyAsync(query,q,size_t(d)*4,cudaMemcpyHostToDevice,stream));
        faiss::gpu::GpuDistanceParams p;p.k=std::min(8,n);p.dims=d;p.numVectors=n;p.vectors=database;p.vectorNorms=norms;
        p.queries=query;p.numQueries=1;p.outIndicesType=faiss::gpu::IndicesDataType::I32;p.outIndices=ids.data();
        p.outDistances=dist.data();p.device=0;p.use_cuvs=false;faiss::gpu::bfKnn(faiss.get(),p);ck(cudaStreamSynchronize(stream));
        for(int i=0;i<p.k;i++){raw[i]=double(dist[i]);dist[i]=std::sqrt(std::max(0.f,dist[i]));}
    }
    void map(std::vector<int>& ids){for(int& id:ids)if(id>=0){pe::require(id<n,"E selected row");id=occurrence[id];}}
    void release_live(){
        faiss.reset();drop(norms);std::vector<int>().swap(occurrence);std::vector<int>().swap(position);Scan::release();
    }
};
struct Answer {int step,flag;size_t offset;std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;};
struct Operation {int step,flag,n_before,n_after;double ack;};
static void execute(const pe::Trace& trace,const std::vector<float>& data,const std::string& out,float radius,double context){
    DynamicScan scan;auto tick=Clock::now();scan.build_live(data,trace.n,trace.d);double setup=ms(tick);
    size_t free,total,peak=0;ck(cudaMemGetInfo(&free,&total));peak=total-free;
    std::vector<Answer> answers;answers.reserve(trace.flags.size());std::vector<Operation> ops;ops.reserve(trace.flags.size());
    size_t at=0;rusage before{},after{};getrusage(RUSAGE_SELF,&before);auto start=Clock::now();
    for(size_t i=0;i<trace.flags.size();i++){
        auto begin=Clock::now();int n=scan.n,flag=trace.flags[i];
        if(flag==0)scan.insert(trace.occ[i],trace.vector(i));
        else if(flag==1)scan.erase(trace.occ[i]);
        else {
            Answer a{};a.step=int(i);a.flag=flag;a.offset=at;
            if(flag==2)scan.range(trace.vector(i),radius,a.ids,a.fields,a.raw);
            else scan.knn(trace.vector(i),a.ids,a.fields,a.raw);
            scan.map(a.ids);at+=a.ids.size();pe::require(at<=size_t(1)<<26,"E complete-output 1GiB bound");answers.push_back(std::move(a));
        }
        ck(cudaDeviceSynchronize());ops.push_back({int(i),flag,n,scan.n,ms(begin)});
    }
    tick=Clock::now();auto final=scan.occurrence;scan.release_live();double release=ms(tick),trace_ms=ms(start);getrusage(RUSAGE_SELF,&after);
    ck(cudaMemGetInfo(&free,&total));size_t end_used=total-free;
    auto seconds=[](timeval x){return x.tv_sec+x.tv_usec*1e-6;};tick=Clock::now();
    std::ofstream ids(out+".ids.i32",std::ios::binary),fields(out+".dist.f32",std::ios::binary),raw(out+".native_squared.f64",std::ios::binary),queries(out+".queries.csv"),operations(out+".ops.csv"),state(out+".final.i32",std::ios::binary),meta(out+".pe.json");
    queries<<"step,flag,count,offset\n";operations<<std::setprecision(17)<<"step,flag,n_before,n_after,ack_ms,rebuild_ms\n";
    for(auto& a:answers){ids.write((char*)a.ids.data(),a.ids.size()*4);fields.write((char*)a.fields.data(),a.fields.size()*4);raw.write((char*)a.raw.data(),a.raw.size()*8);queries<<a.step<<','<<a.flag<<','<<a.ids.size()<<','<<a.offset<<'\n';}
    for(auto& o:ops)operations<<o.step<<','<<o.flag<<','<<o.n_before<<','<<o.n_after<<','<<o.ack<<",0\n";
    state.write((char*)final.data(),final.size()*4);
    meta<<std::setprecision(17)<<"{\"method\":\"E_ADAPT\",\"setup_ms\":"<<setup<<",\"trace_ms\":"<<trace_ms<<",\"release_ms\":"<<release<<",\"context_ms\":"<<context
        <<",\"cpu_user_s\":"<<seconds(after.ru_utime)-seconds(before.ru_utime)<<",\"cpu_system_s\":"<<seconds(after.ru_stime)-seconds(before.ru_stime)
        <<",\"device_used_built_bytes\":"<<peak<<",\"device_used_final_bytes\":"<<end_used<<",\"vector_storage_bytes\":"<<data.size()*4<<",\"norm_storage_bytes\":"<<scan.capacity*4
        <<",\"capacity\":"<<scan.capacity<<",\"final_live\":"<<final.size()<<",\"rebuilds\":0,\"native_norm_updates_including_build\":"<<scan.norm_updates<<",\"swap_deletes\":"<<scan.swaps
        <<",\"inserted_H2D_bytes\":"<<scan.inserted_bytes<<",\"swap_D2D_bytes\":"<<scan.swapped_bytes<<",\"native_squared_observer_charged\":true,\"client_payload_bytes\":"<<at*16<<"}\n";
    pe::require(bool(ids)&&bool(fields)&&bool(raw)&&bool(queries)&&bool(operations)&&bool(state)&&bool(meta),"E output persistence");
}
int main(int argc,char** argv)try{
    if(argc!=5)throw std::runtime_error("DATA TRACE_PREFIX RADIUS OUTPUT");
    auto parse=Clock::now();pe::Trace measured,warm;measured.load(argv[2]);warm.load(std::string(argv[2])+".warmup");
    pe::require(measured.n==warm.n&&measured.d==warm.d,"warm shape");
    int inserts=std::max(std::count(measured.flags.begin(),measured.flags.end(),0),std::count(warm.flags.begin(),warm.flags.end(),0));
    std::ifstream file(argv[1],std::ios::binary);int h[3]{};file.read((char*)h,12);
    pe::require(bool(file)&&h[0]==measured.d&&h[1]==measured.n&&h[2]==2,"E data header");
    std::vector<float> data(size_t(h[1]+inserts)*h[0]);file.read((char*)data.data(),size_t(h[1])*h[0]*4);
    pe::require(bool(file)&&file.peek()==EOF,"E data bytes");for(float x:data)pe::require(std::isfinite(x),"E finite data");
    size_t consumed=0;float radius=std::stof(argv[3],&consumed);pe::require(consumed==std::string(argv[3]).size()&&std::isfinite(radius)&&radius>=0,"E radius");
    double parse_ms=ms(parse);auto start=Clock::now();ck(cudaFree(nullptr));double context=ms(start);
    start=Clock::now();execute(warm,data,std::string(argv[4])+".warmup",radius,context);double warm_ms=ms(start);
    execute(measured,data,argv[4],radius,context);
    std::ofstream scope(std::string(argv[4])+".scope.json");scope<<std::setprecision(17)<<"{\"parse_ms\":"<<parse_ms<<",\"context_ms\":"<<context<<",\"warmup_total_ms\":"<<warm_ms<<",\"warmup_events\":"<<warm.flags.size()<<",\"warmup_queries\":8}\n";
    pe::require(bool(scope),"E scope write");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
