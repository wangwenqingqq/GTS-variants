// Unchanged parent operators; optional NVTX and new bounded client workloads only.
#include "adapter.cuh"
struct Sample {int sample,kind,rows;double ack,del,ins;uint64_t copies,h2d,d2d,sync;};
static void write_answers(Store& s,const std::vector<Answer>& answers,const std::string& out){
    s.p.write_audit(out);std::ofstream qr(out+".queries.csv"),oi(out+".ids.i32",std::ios::binary),of(out+".dist.f32",std::ios::binary),
        os(out+".squared.f64",std::ios::binary),oa(out+".authority.f64",std::ios::binary);
    qr<<std::setprecision(17)<<"phase,slot,mutation,invocation,count,offset,ack_ms\n";size_t offset=0;
    for(const auto& a:answers){qr<<a.phase<<','<<a.slot<<','<<a.mutation<<','<<a.invocation<<','<<a.ids.size()<<','<<offset<<','<<a.ack<<'\n';
        oi.write((char*)a.ids.data(),a.ids.size()*4);of.write((char*)a.fields.data(),a.fields.size()*4);
        os.write((char*)a.raw.data(),a.raw.size()*8);oa.write((char*)a.authority.data(),a.authority.size()*8);offset+=a.ids.size();}
    require(bool(qr)&&bool(oi)&&bool(of)&&bool(os)&&bool(oa),"query export");
}
static void micro(int argc,char** argv){
    require(argc==13,"--micro DATA PREFIX QIDS RADIUS OUT OP B N K DIAGNOSTIC");
    int op=std::stoi(argv[7]),batch=std::stoi(argv[8]),n=std::stoi(argv[9]),k=std::stoi(argv[10]),diag=std::stoi(argv[11]);
    // The last literal identifies this client contract, not an unregistered option.
    require(std::string(argv[12])=="v1"&&op>=0&&op<=2&&batch>=1&&batch<=512&&n>0&&n<=1000000&&k>0&&k<=n/2&&k%batch==0,"micro envelope");
    std::ifstream data(argv[2],std::ios::binary);int header[3];data.read((char*)header,12);require(header[0]==960&&header[1]==1000000&&header[2]==2,"data header");
    std::vector<float> x(size_t(n)*960),incoming(size_t(k)*960);std::vector<int> victims(k);data.read((char*)x.data(),x.size()*4);require(bool(data),"initial bytes");
    std::string prefix=argv[3],out=argv[6];std::ifstream fi(prefix+".incoming.f32",std::ios::binary),fv(prefix+".victims.i32",std::ios::binary),fq(argv[4]);
    fi.read((char*)incoming.data(),incoming.size()*4);fv.read((char*)victims.data(),k*4);require(bool(fi)&&bool(fv),"registered prefix bytes");
    std::array<int,32> qids;for(int& q:qids){fq>>q;require(bool(fq)&&q>=0&&q<n,"query ID");}
    float radius=std::stof(argv[5]);require(std::isfinite(radius)&&radius>=0&&diag>=0&&diag<=2,"radius/diagnostic");
    std::set<int> unique;for(int id:victims)require(id>=0&&id<n&&unique.insert(id).second,"unique original victims");
    for(float value:incoming)require(std::isfinite(value)&&std::abs(value)<=16,"incoming envelope");
    Store s;auto tick=Clock::now();s.build(x,n,k);s.p.audit_mode=diag==2?4:0;
    if(op==0)for(int a=0;a<k;a+=512)s.erase(std::vector<int>(victims.begin()+a,victims.begin()+std::min(k,a+512)));
    std::vector<Answer> answers;answers.reserve(40);std::vector<Sample> samples;samples.reserve(size_t(k/batch)*(op==2?3:1));
    auto query=[&](int phase,int slot){Answer a{};a.phase=phase;a.slot=slot;a.mutation=phase<0?(op==0?k:0):k;
        auto t=Clock::now();s.query(x.data()+size_t(qids[slot])*960,radius,a);a.ack=ms(t);if(diag==2)a.authority=s.p.last_scores;answers.push_back(std::move(a));};
    for(int i=0;i<8;i++)query(-1,i);double preparation=ms(tick);uint64_t before_h=s.inserted,before_d=s.swapped;
    rusage cpu0{},cpu1{};getrusage(RUSAGE_SELF,&cpu0);if(diag==1)ck(cudaProfilerStart());auto event=Clock::now();
    {
        Zone formal("MICRO_FORMAL");
        for(int a=0;a<k;a+=batch){
            std::vector<int> ids(victims.begin()+a,victims.begin()+a+batch);uint64_t d=s.swapped;double del=0,ins=0;auto pair=Clock::now();
            if(op!=0){auto t=Clock::now();s.erase(ids);del=ms(t);samples.push_back({a/batch,0,batch,del,del,0,(s.swapped-d)/3840,0,s.swapped-d,1});}
            if(op!=1){auto t=Clock::now();s.insert(incoming.data()+size_t(a)*960,batch);ins=ms(t);samples.push_back({a/batch,1,batch,ins,0,ins,1,uint64_t(batch)*3840,0,1});}
            if(op==2)samples.push_back({a/batch,2,batch,ms(pair),del,ins,1+(s.swapped-d)/3840,uint64_t(batch)*3840,s.swapped-d,2});
        }
    }
    double events=ms(event);if(diag==1)ck(cudaProfilerStop());getrusage(RUSAGE_SELF,&cpu1);
    uint64_t h2d=s.inserted-before_h,d2d=s.swapped-before_d;for(int i=0;i<32;i++)query(0,i);
    tick=Clock::now();final_proof(s,x,incoming,out);write_answers(s,answers,out);
    std::ofstream f(out+".ops.csv");f<<std::setprecision(17)<<"sample,kind,rows,ack_ms,delete_ms,insert_ms,copy_calls,H2D_bytes,D2D_bytes,sync_calls\n";
    for(auto& v:samples)f<<v.sample<<','<<v.kind<<','<<v.rows<<','<<v.ack<<','<<v.del<<','<<v.ins<<','<<v.copies<<','<<v.h2d<<','<<v.d2d<<','<<v.sync<<'\n';require(bool(f),"operation export");f.close();
    int live=s.p.n;uint64_t owned=uint64_t(n)*960*4+uint64_t(n)*49+960*4+4+s.p.bytes+240;
    double offline=ms(tick);tick=Clock::now();s.release();std::vector<Answer>().swap(answers);std::vector<Sample>().swap(samples);double release=ms(tick);
    auto sec=[](timeval t){return t.tv_sec+double(t.tv_usec)*1e-6;};std::ofstream meta(out+".meta.json");
    meta<<std::setprecision(17)<<"{\"kind\":\"micro\",\"N\":"<<n<<",\"K\":"<<k<<",\"op\":"<<op<<",\"batch\":"<<batch<<",\"trace\":"<<TRACE<<",\"diagnostic\":"<<diag
        <<",\"final_live\":"<<live<<",\"warmup_queries\":8,\"final_validation_queries\":32,\"events_ms\":"<<events<<",\"release_ms\":"<<release
        <<",\"preparation_ms\":"<<preparation<<",\"offline_state_export_ms\":"<<offline<<",\"formal_H2D_request_bytes\":"<<h2d<<",\"formal_D2D_request_bytes\":"<<d2d
        <<",\"known_device_owned_peak_bytes\":"<<owned<<",\"CPU_events_user_s\":"<<sec(cpu1.ru_utime)-sec(cpu0.ru_utime)<<",\"CPU_events_system_s\":"<<sec(cpu1.ru_stime)-sec(cpu0.ru_stime)<<"}\n";
    require(bool(meta),"micro metadata");
}
static void copy_reference(const std::string& out,int reverse){
    const size_t bytes=size_t(1)<<30;std::vector<uint32_t> source(bytes/4),check(bytes/4);uint32_t seed=2026101512;
    for(auto& v:source){seed=1664525u*seed+1013904223u;v=seed;}
    uint32_t *a=nullptr,*b=nullptr;cudaStream_t stream;ck(cudaStreamCreate(&stream));alloc(a,source.size());alloc(b,source.size());
    auto run=[&](int kind){ck(cudaMemcpyAsync(kind?b:a,kind?a:source.data(),bytes,kind?cudaMemcpyDeviceToDevice:cudaMemcpyHostToDevice,stream));ck(cudaStreamSynchronize(stream));};
    ck(cudaMemcpy(a,source.data(),bytes,cudaMemcpyHostToDevice));for(int r=0;r<2;r++){run(0);run(1);}
    struct Copy {int round,kind;double ack;};std::vector<Copy> values;values.reserve(32);ck(cudaProfilerStart());
    {Zone formal("COPY_FORMAL");for(int r=0;r<16;r++)for(int i=0;i<2;i++){int kind=reverse?1-i:i;auto begin=Clock::now();
        {Zone range(kind?"CAL_D2D":"CAL_H2D");run(kind);}values.push_back({r,kind,ms(begin)});}}
    ck(cudaProfilerStop());
    for(auto* pointer:{a,b}){ck(cudaMemcpy(check.data(),pointer,bytes,cudaMemcpyDeviceToHost));require(std::memcmp(check.data(),source.data(),bytes)==0,"every bulk destination byte");}
    std::ofstream f(out+".copy.csv");f<<std::setprecision(17)<<"round,kind,bytes,ack_ms\n";for(auto v:values)f<<v.round<<','<<v.kind<<','<<bytes<<','<<v.ack<<'\n';require(bool(f),"copy export");
    drop(a);drop(b);ck(cudaStreamDestroy(stream));std::ofstream m(out+".meta.json");m<<"{\"kind\":\"copy\",\"trace\":"<<TRACE<<",\"bytes\":"<<bytes<<",\"samples_per_direction\":16,\"all_destination_bytes_compared\":"<<2*bytes<<",\"passed\":true}\n";require(bool(m),"copy metadata");
}
int main(int argc,char** argv)try{
    if(argc==2&&std::string(argv[1])=="--selftest"){selftest();return 0;}
    if(argc>=2&&std::string(argv[1])=="--legacy")return frozen_service_main(argc-1,argv+1);
    if(argc==4&&std::string(argv[1])=="--copy"){copy_reference(argv[2],std::stoi(argv[3]));return 0;}
    micro(argc,argv);return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
