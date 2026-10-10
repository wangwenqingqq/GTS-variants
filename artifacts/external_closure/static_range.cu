// Same qualified Scan implementation; only retain/write and phase timers differ.
#define main closure_qualification_main
#include "range_service.cu"
#undef main
struct Answer {int qid;std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;double ack;};
int main(int argc,char** argv) try {
    if(argc!=4)throw std::runtime_error("DATA REQUESTS OUTPUT");
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);
    if(!f||h[0]<1||h[0]>960||h[1]<0||h[1]>1000000||h[2]!=2)throw std::runtime_error("header");
    std::vector<float> data(size_t(h[0])*h[1]);f.read((char*)data.data(),data.size()*4);
    if(!f||f.peek()!=EOF)throw std::runtime_error("input length");for(float x:data)if(!std::isfinite(x))throw std::runtime_error("nonfinite");
    std::ifstream req(argv[2]);int count;req>>count;if(count!=40)throw std::runtime_error("8 warmup +32 measured");
    struct Request{int qid;float radius;};std::vector<Request> requests;
    for(int i=0;i<count;i++){int task,row,k;float radius;req>>task>>row>>radius>>k;
        if(!req||task!=1||row<0||(h[1]&&row>=h[1])||!std::isfinite(radius)||k!=8)throw std::runtime_error("request");requests.push_back({row,radius});}
    std::string extra;if(req>>extra)throw std::runtime_error("trailing request");
    auto tick=Clock::now();ck(cudaFree(nullptr));double context=ms(tick);size_t free_before,total,free_built,free_end;
    ck(cudaMemGetInfo(&free_before,&total));Scan scan;tick=Clock::now();scan.build(data,h[1],h[0]);double build=ms(tick);ck(cudaMemGetInfo(&free_built,&total));
    std::vector<Answer> answers;answers.reserve(40);double warm=0,pass=0;std::vector<float> zero(h[0],0);tick=Clock::now();
    for(int i=0;i<40;i++) {
        if(i==8){warm=ms(tick);tick=Clock::now();}
        auto begin=Clock::now();Answer answer;answer.qid=requests[i].qid;
        scan.range(h[1]?data.data()+size_t(answer.qid)*h[0]:zero.data(),requests[i].radius,answer.ids,answer.fields,answer.raw);
        answers.push_back(std::move(answer));answers.back().ack=ms(begin);
    }
    pass=ms(tick);tick=Clock::now();scan.release();double release=ms(tick);ck(cudaMemGetInfo(&free_end,&total));
    std::string out=argv[3];std::ofstream ids(out+".ids.i32",std::ios::binary),fields(out+".dist.f32",std::ios::binary),raw(out+".native_squared.f64",std::ios::binary),rows(out+".queries.csv"),meta(out+".static.json");
    rows<<"task,query,qid,count,offset,ack_ms\n"<<std::setprecision(17);size_t at=0;
    for(int i=0;i<40;i++){auto& a=answers[i];ids.write((char*)a.ids.data(),a.ids.size()*4);fields.write((char*)a.fields.data(),a.fields.size()*4);raw.write((char*)a.raw.data(),a.raw.size()*8);rows<<"range,"<<i<<','<<a.qid<<','<<a.ids.size()<<','<<at<<','<<a.ack<<'\n';at+=a.ids.size();}
    meta<<std::setprecision(17)<<"{\"method\":\"GPU_RANGE_COMPLETE\",\"preparation_ms\":0,\"build_ms\":"<<build<<",\"warmup_ms\":"<<warm<<",\"range_pass_ms\":"<<pass<<",\"release_ms\":"<<release<<",\"context_ms\":"<<context<<",\"queries\":40,\"warmup_per_task\":8,\"measured_per_task\":32,\"device_used_before\":"<<total-free_before<<",\"device_used_built\":"<<total-free_built<<",\"device_used_final\":"<<total-free_end<<",\"workspace_bytes\":"<<scan.bytes<<",\"raw_squared_observer_included\":true,\"build_includes_allocations_and_H2D\":true}\n";
    if(!ids||!fields||!raw||!rows||!meta)throw std::runtime_error("output write");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
