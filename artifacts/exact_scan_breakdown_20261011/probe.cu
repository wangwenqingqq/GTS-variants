// Diagnostic controls over the unchanged qualified cuVS distance path; no optimization dispatch.
#define main qualified_scan_main
#include "../external_closure/range_service.cu"
#undef main
#include <cuda_profiler_api.h>
#include <nvtx3/nvToolsExt.h>
#include <filesystem>
#include <thrust/iterator/transform_iterator.h>
#include <string>
struct Predicate {double cutoff;__host__ __device__ int operator()(float x)const{return double(x)<=cutoff;}};
// Every coordinate is consumed once; FP32 checksum and one block reduction prevent elimination.
__global__ void coordinate_read(const float4* x,size_t elements,float* partial){
    using R=cub::BlockReduce<float,256>;__shared__ typename R::TempStorage tmp;float sum=0;
    for(size_t i=size_t(blockIdx.x)*256+threadIdx.x;i<elements;i+=size_t(gridDim.x)*256){float4 v=x[i];sum+=((v.x+v.y)+v.z)+v.w;}
    float block=R(tmp).Sum(sum);if(!threadIdx.x)partial[blockIdx.x]=block;
}
struct Control:Scan {
    float *partial=nullptr,*aggregate=nullptr,*copy=nullptr;void* reduce=nullptr;size_t reduce_bytes=0;int blocks=0;std::vector<cudaEvent_t> ev;
    void extra(const std::string& mode,bool diagnostic){
        cudaDeviceProp p{};ck(cudaGetDeviceProperties(&p,0));blocks=p.multiProcessorCount*8;
        alloc(partial,blocks);alloc(aggregate,1);
        size_t a=0,b=0,c=0;ck(cub::DeviceReduce::Sum(nullptr,a,partial,aggregate,blocks,stream));ck(cub::DeviceReduce::Sum(nullptr,b,squared,aggregate,n,stream));
        auto it=thrust::make_transform_iterator(squared,Predicate{0});ck(cub::DeviceReduce::Sum(nullptr,c,it,count,n,stream));reduce_bytes=std::max({a,b,c});ck(cudaMalloc(&reduce,reduce_bytes));
        if(mode=="COPY")alloc(copy,size_t(n)*d);
        if(diagnostic||mode=="COPY"){ev.resize(8);for(auto& e:ev)ck(cudaEventCreate(&e));}
    }
    void mark(int i){if(!ev.empty())ck(cudaEventRecord(ev[i],stream));}
    float elapsed(int i,int j){float t;ck(cudaEventElapsedTime(&t,ev[i],ev[j]));return t;}
    void distance(const float* q){
        ck(cudaMemcpyAsync(query,q,size_t(d)*4,cudaMemcpyHostToDevice,stream));mark(1);
        int64_t qs[2]={1,d},ds[2]={n,d},os[2]={1,n};auto a=tensor(query,qs),b=tensor(database,ds),c=tensor(squared,os);
        cv(cuvsPairwiseDistance(resource,&a,&b,&c,L2Unexpanded,0));mark(2);
    }
    float control(const std::string& mode,const float* q,float radius,int& hits){
        mark(0);float value=0;
        if(mode=="READ_ONLY"){
            ck(cudaMemcpyAsync(query,q,size_t(d)*4,cudaMemcpyHostToDevice,stream));mark(1);
            coordinate_read<<<blocks,256,0,stream>>>(reinterpret_cast<const float4*>(database),size_t(n)*d/4,partial);mark(2);
            ck(cub::DeviceReduce::Sum(reduce,reduce_bytes,partial,aggregate,blocks,stream));mark(3);
        }else {
            distance(q);
            if(mode=="DISTANCE_ONLY")ck(cub::DeviceReduce::Sum(reduce,reduce_bytes,squared,aggregate,n,stream));
            else {auto it=thrust::make_transform_iterator(squared,Predicate{double(radius)*double(radius)});ck(cub::DeviceReduce::Sum(reduce,reduce_bytes,it,count,n,stream));}
            mark(3);
        }
        ck(cudaGetLastError());
        if(mode=="THRESHOLD_COUNT")ck(cudaMemcpyAsync(&hits,count,4,cudaMemcpyDeviceToHost,stream));
        else ck(cudaMemcpyAsync(&value,aggregate,4,cudaMemcpyDeviceToHost,stream));
        mark(4);ck(cudaStreamSynchronize(stream));return value;
    }
    void full_diag(const float* q,float radius,std::vector<int>& ids,std::vector<float>& dist,std::vector<double>& native){
        mark(0);distance(q);
        flags_kernel<<<(n+255)/256,256,0,stream>>>(squared,identity,flags,n,double(radius)*double(radius),radius>=0);mark(3);
        ck(cub::DeviceSelect::Flagged(scratch,bytes,identity,flags,outids,count,n,stream));mark(4);
        fields_kernel<<<(n+255)/256,256,0,stream>>>(squared,outids,count,fields,raw,n);ck(cudaGetLastError());mark(5);
        int result;ck(cudaMemcpyAsync(&result,count,4,cudaMemcpyDeviceToHost,stream));mark(6);ck(cudaStreamSynchronize(stream));
        if(result<0||result>n)throw std::runtime_error("capacity");ids.resize(result);dist.resize(result);native.resize(result);
        if(result){ck(cudaMemcpyAsync(ids.data(),outids,result*4,cudaMemcpyDeviceToHost,stream));ck(cudaMemcpyAsync(dist.data(),fields,result*4,cudaMemcpyDeviceToHost,stream));ck(cudaMemcpyAsync(native.data(),raw,result*8,cudaMemcpyDeviceToHost,stream));}
        mark(7);ck(cudaStreamSynchronize(stream));
    }
    void finish(){for(auto e:ev)ck(cudaEventDestroy(e));drop(partial);drop(aggregate);drop(copy);drop(reduce);release();}
};
struct Answer {int qid,count=0;float checksum=0;double ack=0;std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;std::vector<float> phases;};
int main(int argc,char** argv)try {
    if(argc!=9)throw std::runtime_error("DATA QIDS N D RADIUS MODE OUTPUT DIAGNOSTIC");
    std::string mode=argv[6],out=argv[7];int n=std::stoi(argv[3]),d=std::stoi(argv[4]);float radius=std::stof(argv[5]);bool diagnostic=std::stoi(argv[8]);
    if(std::filesystem::exists(out+".rows.csv")||n<1||n>1000000||(d!=128&&d!=256&&d!=512&&d!=960)||!std::isfinite(radius)||radius<0)throw std::runtime_error("contract/input/output boundary");
    if(mode!="READ_ONLY"&&mode!="DISTANCE_ONLY"&&mode!="THRESHOLD_COUNT"&&mode!="FULL_OUTPUT"&&mode!="COPY")throw std::runtime_error("mode");
    auto tick=Clock::now();std::ifstream f(argv[1],std::ios::binary);int h[3]{};f.read((char*)h,12);if(!f||h[0]!=960||h[1]!=1000000||h[2]!=2)throw std::runtime_error("original GIST header");
    std::vector<float> original(size_t(h[0])*h[1]);f.read((char*)original.data(),original.size()*4);if(!f||f.peek()!=EOF)throw std::runtime_error("data length");
    std::vector<int> qids;std::ifstream qfile(argv[2]);int q;while(qfile>>q){if(q<0||q>=h[1])throw std::runtime_error("query bounds");qids.push_back(q);}if(!qfile.eof()||qids.size()!=32)throw std::runtime_error("32 qids");
    std::vector<float> data(size_t(n)*d),queries(size_t(32)*d);
    for(int i=0;i<n;i++){std::copy_n(original.data()+size_t(i)*960,d,data.data()+size_t(i)*d);}
    for(int i=0;i<32;i++)std::copy_n(original.data()+size_t(qids[i])*960,d,queries.data()+size_t(i)*d);
    for(float v:data)if(!std::isfinite(v))throw std::runtime_error("finite data");for(float v:queries)if(!std::isfinite(v))throw std::runtime_error("finite query");
    double preparation=ms(tick);std::vector<float>().swap(original);tick=Clock::now();ck(cudaFree(nullptr));double context=ms(tick);
    Control s;tick=Clock::now();s.build(data,n,d);s.extra(mode,diagnostic);double build=ms(tick);
    std::vector<Answer> answers;answers.reserve(40);double warm=0,pass=0;tick=Clock::now();
    for(int i=0;i<40;i++){
        if(i==8){warm=ms(tick);tick=Clock::now();if(diagnostic)ck(cudaProfilerStart());}
        int qi=i<8?i:i-8;const float* query=queries.data()+size_t(qi)*d;Answer a;a.qid=qids[qi];
        if(diagnostic)nvtxRangePushA(("query_"+std::to_string(i)).c_str());auto begin=Clock::now();
        if(mode=="FULL_OUTPUT"){
            if(diagnostic)s.full_diag(query,radius,a.ids,a.fields,a.raw);else s.range(query,radius,a.ids,a.fields,a.raw);a.count=int(a.ids.size());
        }else if(mode=="COPY"){s.mark(0);ck(cudaMemcpyAsync(s.copy,s.database,size_t(n)*d*4,cudaMemcpyDeviceToDevice,s.stream));s.mark(1);ck(cudaStreamSynchronize(s.stream));a.phases.push_back(s.elapsed(0,1));}
        else a.checksum=s.control(mode,query,radius,a.count);
        a.ack=ms(begin);
        if(diagnostic){int limit=mode=="FULL_OUTPUT"?7:4;for(int j=0;j<limit;j++)a.phases.push_back(s.elapsed(j,j+1));nvtxRangePop();}
        answers.push_back(std::move(a));
    }
    pass=ms(tick);if(diagnostic)ck(cudaProfilerStop());
    if(mode=="COPY"){float first=0,last=0;ck(cudaMemcpy(&first,s.copy,4,cudaMemcpyDeviceToHost));ck(cudaMemcpy(&last,s.copy+size_t(n)*d-1,4,cudaMemcpyDeviceToHost));if(first!=data.front()||last!=data.back())throw std::runtime_error("copy checksum");}
    tick=Clock::now();s.finish();double release=ms(tick);
    std::ofstream rows(out+".rows.csv"),ids(out+".ids.i32",std::ios::binary),fields(out+".dist.f32",std::ios::binary),raw(out+".native_squared.f64",std::ios::binary),meta(out+".meta.json");
    rows<<"query,qid,warmup,count,offset,ack_ms,checksum,p0,p1,p2,p3,p4,p5,p6\n"<<std::setprecision(17);size_t at=0;
    for(int i=0;i<40;i++){auto& a=answers[i];rows<<i<<','<<a.qid<<','<<(i<8)<<','<<a.count<<','<<at<<','<<a.ack<<','<<a.checksum;for(int j=0;j<7;j++)rows<<','<<(j<int(a.phases.size())?a.phases[j]:-1);rows<<'\n';ids.write((char*)a.ids.data(),a.ids.size()*4);fields.write((char*)a.fields.data(),a.fields.size()*4);raw.write((char*)a.raw.data(),a.raw.size()*8);at+=a.ids.size();}
    meta<<std::setprecision(17)<<"{\"N\":"<<n<<",\"D\":"<<d<<",\"mode\":\""<<mode<<"\",\"diagnostic\":"<<(diagnostic?"true":"false")<<",\"preparation_ms\":"<<preparation<<",\"context_ms\":"<<context<<",\"build_ms\":"<<build<<",\"warmup_ms\":"<<warm<<",\"measured_pass_ms\":"<<pass<<",\"release_ms\":"<<release<<",\"persistent_select_bytes\":"<<s.bytes<<",\"persistent_reduce_bytes\":"<<s.reduce_bytes<<",\"read_blocks\":"<<s.blocks<<"}\n";
    if(!rows||!ids||!fields||!raw||!meta)throw std::runtime_error("output persist");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
