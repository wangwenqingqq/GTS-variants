// Host-only shape sweep; original native and complete-output device kernels are included unchanged.
#define main original_service_main
#include "../external_closure/range_service.cu"
#undef main
#include <cuda_profiler_api.h>
#include <filesystem>
#include <nvtx3/nvToolsExt.h>

struct Answer {int qid;std::vector<int> ids;std::vector<float> dist;std::vector<double> raw;};
struct Invocation {double ack;std::vector<Answer> answers;};
struct Batch : Scan {
    int batch;
    void build_batch(const std::vector<float>& data,int rows,int dim,int b){
        batch=b;build(data,rows,dim);
        if(b>1){drop(query);drop(squared);alloc(query,size_t(b)*d);alloc(squared,size_t(b)*n);}
    }
    void emit(float radius,Answer& answer){
        // Same host epilogue as Scan::range; each row remains a complete range query.
        auto& ids=answer.ids;auto& dist=answer.dist;auto& native=answer.raw;
        flags_kernel<<<(n+255)/256,256,0,stream>>>(squared,identity,flags,n,double(radius)*double(radius),radius>=0);
        ck(cub::DeviceSelect::Flagged(scratch,bytes,identity,flags,outids,count,n,stream));
        fields_kernel<<<(n+255)/256,256,0,stream>>>(squared,outids,count,fields,raw,n);ck(cudaGetLastError());
        int result;ck(cudaMemcpyAsync(&result,count,4,cudaMemcpyDeviceToHost,stream));ck(cudaStreamSynchronize(stream));
        if(result<0||result>n)throw std::runtime_error("capacity");ids.resize(result);dist.resize(result);native.resize(result);
        if(result){ck(cudaMemcpyAsync(ids.data(),outids,result*4,cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(dist.data(),fields,result*4,cudaMemcpyDeviceToHost,stream));ck(cudaMemcpyAsync(native.data(),raw,result*8,cudaMemcpyDeviceToHost,stream));}
        ck(cudaStreamSynchronize(stream));
    }
    void invoke(const float* q,float radius,std::vector<Answer>& answers){
        if(batch==1){range(q,radius,answers[0].ids,answers[0].dist,answers[0].raw);return;}
        ck(cudaMemcpyAsync(query,q,size_t(batch)*d*4,cudaMemcpyHostToDevice,stream));
        int64_t qs[2]={batch,d},ds[2]={n,d},os[2]={batch,n};auto a=tensor(query,qs),b=tensor(database,ds),c=tensor(squared,os);
        cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));
        float* base=squared;
        for(int i=0;i<batch;i++){squared=base+size_t(i)*n;emit(radius,answers[i]);}
        squared=base;
    }
};
int main(int argc,char** argv)try{
    if(argc!=8)throw std::runtime_error("DATA POOL N B RADIUS OUTPUT DIAGNOSTIC");
    int n=std::stoi(argv[3]),b=std::stoi(argv[4]);float radius=std::stof(argv[5]);std::string out=argv[6];bool diagnostic=std::stoi(argv[7]);
    if((n!=4096&&n!=1000000)||b<1||b>128||(b&(b-1))||!std::isfinite(radius)||radius<0||std::filesystem::exists(out+".rows.csv"))throw std::runtime_error("contract boundary");
    auto tick=Clock::now();std::ifstream f(argv[1],std::ios::binary);int h[3]{};f.read((char*)h,12);
    if(!f||h[0]!=960||h[1]!=1000000||h[2]!=2)throw std::runtime_error("original data header");
    std::vector<float> original(size_t(h[0])*h[1]);f.read((char*)original.data(),original.size()*4);if(!f||f.peek()!=EOF)throw std::runtime_error("data length");
    std::ifstream pool(argv[2]);std::vector<int> qids;int q;while(pool>>q){if(q<0||q>=h[1]||std::find(qids.begin(),qids.end(),q)!=qids.end())throw std::runtime_error("distinct pool");qids.push_back(q);}
    size_t poolsize=b<=32?32:128;if(!pool.eof()||qids.size()!=poolsize)throw std::runtime_error("pool size");
    std::vector<float> data(original.begin(),original.begin()+size_t(n)*960),queries(poolsize*960);
    for(size_t i=0;i<poolsize;i++)std::copy_n(original.data()+size_t(qids[i])*960,960,queries.data()+i*960);
    for(float v:data)if(!std::isfinite(v))throw std::runtime_error("finite data");for(float v:queries)if(!std::isfinite(v))throw std::runtime_error("finite query");
    std::vector<float>().swap(original);double preparation=ms(tick);tick=Clock::now();ck(cudaFree(nullptr));double context=ms(tick);
    Batch scan;tick=Clock::now();scan.build_batch(data,n,960,b);double build=ms(tick);
    std::vector<Invocation> all;all.reserve(40);double warm=0,pass=0;tick=Clock::now();
    for(int i=0;i<40;i++){
        if(i==8){warm=ms(tick);tick=Clock::now();}
        size_t start=size_t(i<8?i:i-8)*b%poolsize;Invocation item;item.answers.resize(b);
        for(int j=0;j<b;j++){size_t qi=(start+j)%poolsize;item.answers[j].qid=qids[qi];}
        if(diagnostic&&i==8){ck(cudaProfilerStart());nvtxRangePushA("selected_measured_invocation");}
        auto begin=Clock::now();scan.invoke(queries.data()+start*960,radius,item.answers);all.push_back(std::move(item));all.back().ack=ms(begin);
        if(diagnostic&&i==8){nvtxRangePop();ck(cudaProfilerStop());}
    }
    pass=ms(tick);tick=Clock::now();scan.release();double release=ms(tick);
    std::ofstream rows(out+".rows.csv"),inv(out+".invocations.csv"),ids(out+".ids.i32",std::ios::binary),dist(out+".dist.f32",std::ios::binary),raw(out+".native_squared.f64",std::ios::binary),meta(out+".meta.json");
    rows<<"invocation,query_in_batch,qid,warmup,count,offset\n";inv<<"invocation,warmup,B,ack_ms\n"<<std::setprecision(17);size_t at=0;
    for(int i=0;i<40;i++){inv<<i<<','<<(i<8)<<','<<b<<','<<all[i].ack<<'\n';for(int j=0;j<b;j++){auto& a=all[i].answers[j];rows<<i<<','<<j<<','<<a.qid<<','<<(i<8)<<','<<a.ids.size()<<','<<at<<'\n';ids.write((char*)a.ids.data(),a.ids.size()*4);dist.write((char*)a.dist.data(),a.dist.size()*4);raw.write((char*)a.raw.data(),a.raw.size()*8);at+=a.ids.size();}}
    meta<<std::setprecision(17)<<"{\"N\":"<<n<<",\"D\":960,\"B\":"<<b<<",\"diagnostic\":"<<(diagnostic?"true":"false")<<",\"preparation_ms\":"<<preparation<<",\"context_ms\":"<<context<<",\"build_ms\":"<<build<<",\"warmup_ms\":"<<warm<<",\"measured_pass_ms\":"<<pass<<",\"release_ms\":"<<release<<",\"squared_bytes\":"<<size_t(b)*n*4<<",\"query_bytes\":"<<size_t(b)*960*4<<",\"select_workspace_bytes\":"<<scan.bytes<<"}\n";
    if(!rows||!inv||!ids||!dist||!raw||!meta)throw std::runtime_error("output persistence");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
