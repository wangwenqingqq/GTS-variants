// Both variants inherit identical accepted storage, insert/delete and kNN bodies.
#include "shared_native.cuh"
#include "../progressive_gpu_gate2_20261013/progressive.cuh"
#include <cstring>
#include <sstream>
#ifndef G3_PROGRESSIVE
#error Explicit D0/D1 build required
#endif
struct Service:DynamicScan {
    ProgressiveScan progressive;
    size_t progressive_scratch=0,allocated_scratch_bytes=0;
    void build_service(const std::vector<float>& data,int rows,int dim){
        build_live(data,rows,dim);
        if constexpr(G3_PROGRESSIVE){
            auto& p=progressive;p.database=database;p.query=query;p.stream=stream;p.n=n;p.d=d;
            p.flags=flags;p.outids=outids;p.fields=fields;p.raw=raw;p.count=count;
            alloc(p.active_state,capacity);alloc(p.temporary,capacity);
            ck(cub::DeviceSelect::Flagged(nullptr,progressive_scratch,p.temporary,p.flags,p.active_state,p.count,capacity,stream));
            if(progressive_scratch>bytes){drop(scratch);bytes=progressive_scratch;ck(cudaMalloc(&scratch,bytes));}
            p.scratch=scratch;p.bytes=bytes;for(auto& e:p.events)ck(cudaEventCreate(&e));ck(cudaStreamSynchronize(stream));
        }
        allocated_scratch_bytes=bytes;
    }
    void range(const float* q,float r,std::vector<int>& ids,std::vector<float>& f,std::vector<double>& raw){
        if constexpr(G3_PROGRESSIVE){progressive.n=n;progressive.range(q,r,ids,f,raw);}
        else DynamicScan::range(q,r,ids,f,raw);
    }
    void release_service(){
        if constexpr(G3_PROGRESSIVE){drop(progressive.active_state);drop(progressive.temporary);for(auto& e:progressive.events)ck(cudaEventDestroy(e));}
        release_live();
    }
};
struct Answer {int step,flag;size_t offset;std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;};
struct Operation {int step,flag,n_before,n_after;double ack;};
struct Mutation {int step,flag,id,n_before,n_after,row,last,moved,next;};
static void write_answers(const std::string& p,const std::vector<Answer>& answers){
    std::ofstream ids(p+".ids.i32",std::ios::binary),f(p+".dist.f32",std::ios::binary),raw(p+".native_squared.f64",std::ios::binary),rows(p+".queries.csv");
    rows<<"step,flag,count,offset\n";
    for(auto& a:answers){ids.write((char*)a.ids.data(),a.ids.size()*4);f.write((char*)a.fields.data(),a.fields.size()*4);raw.write((char*)a.raw.data(),a.raw.size()*8);rows<<a.step<<','<<a.flag<<','<<a.ids.size()<<','<<a.offset<<'\n';}
    pe::require(bool(ids)&&bool(f)&&bool(raw)&&bool(rows),"complete output persistence");
}
static void final_proof(Service& s,const pe::Trace& t,const std::vector<float>& initial,const std::string& p){
    auto begin=Clock::now();std::vector<float> expected=initial;std::vector<int> physical(t.n),reverse(s.capacity,-1);std::iota(physical.begin(),physical.end(),0);
    for(int i=0;i<t.n;i++)reverse[i]=i;
    for(size_t i=0;i<t.flags.size();i++){
        int id=t.occ[i];
        if(t.flags[i]==0){int row=int(physical.size());std::memcpy(expected.data()+size_t(row)*960,t.vector(i),960*4);physical.push_back(id);reverse[id]=row;}
        if(t.flags[i]==1){int row=reverse[id],last=int(physical.size())-1;pe::require(row>=0,"CPU replay live delete");
            if(row!=last){std::memcpy(expected.data()+size_t(row)*960,expected.data()+size_t(last)*960,960*4);physical[row]=physical[last];reverse[physical[row]]=row;}physical.pop_back();reverse[id]=-1;}
    }
    pe::require(physical==s.occurrence&&reverse==s.position&&int(physical.size())==s.n,"full final bijection");
    std::vector<float> block(4096*960);size_t compared=0;
    for(int start=0;start<s.n;start+=4096){int rows=std::min(4096,s.n-start);size_t bytes=size_t(rows)*960*4;
        ck(cudaMemcpyAsync(block.data(),s.database+size_t(start)*960,bytes,cudaMemcpyDeviceToHost,s.stream));ck(cudaStreamSynchronize(s.stream));
        pe::require(std::memcmp(block.data(),expected.data()+size_t(start)*960,bytes)==0,"every final GPU vector byte");compared+=bytes;}
    std::ofstream a(p+".physical.i32",std::ios::binary),b(p+".reverse.i32",std::ios::binary),proof(p+".final.proof.json");
    a.write((char*)s.occurrence.data(),s.occurrence.size()*4);b.write((char*)s.position.data(),s.position.size()*4);
    proof<<"{\"passed\":true,\"all_vector_bytes_bitwise_compared\":"<<compared<<",\"physical_rows\":"<<s.n<<",\"reverse_entries\":"<<s.capacity<<",\"scope\":\"offline direct comparison,not hashing-only\",\"elapsed_ms\":"<<std::setprecision(17)<<ms(begin)<<"}\n";
    pe::require(bool(a)&&bool(b)&&bool(proof),"final proof persistence");
}
static void probe(Service& s,const std::vector<float>& initial,const std::vector<int>& pool,int step,float radius,std::vector<Answer>& answers,std::ofstream& counts,size_t& at){
    if constexpr(G3_PROGRESSIVE){
        for(int q:pool){size_t before=s.progressive.records.size();Answer a{};a.step=step;a.flag=q;a.offset=at;s.range(initial.data()+size_t(q)*960,radius,a.ids,a.fields,a.raw);s.map(a.ids);at+=a.ids.size();answers.push_back(std::move(a));
            pe::require(s.progressive.records.size()==before+4,"probe four stages");
            for(size_t i=before;i<before+4;i++){auto& r=s.progressive.records[i];counts<<step<<','<<q<<','<<s.n<<','<<r.stage<<','<<r.input<<','<<r.output<<'\n';}
        }
    }
}
static void execute(const pe::Trace& t,const std::vector<float>& data,const std::string& out,float radius,double context,const std::vector<int>& pool,bool dry){
    Service s;auto tick=Clock::now();s.build_service(data,t.n,t.d);double setup=ms(tick);size_t free,total;ck(cudaMemGetInfo(&free,&total));size_t built=total-free;
    std::vector<Answer> answers,probes;std::vector<Operation> ops;std::vector<Mutation> updates;answers.reserve(t.flags.size());ops.reserve(t.flags.size());updates.reserve(t.flags.size());size_t at=0,probe_at=0;
    std::ofstream probe_counts;int inserted=0,deleted=0;bool p20=false,p40=false;
    if(dry&&G3_PROGRESSIVE){probe_counts.open(out+".probe.stages.csv");probe_counts<<"step,qid,live,stage,input,output\n";probe(s,data,pool,-1,radius,probes,probe_counts,probe_at);}
    rusage before{},after{};getrusage(RUSAGE_SELF,&before);auto start=Clock::now();
    for(size_t i=0;i<t.flags.size();i++){
        auto begin=Clock::now();int n=s.n,flag=t.flags[i];Mutation m{int(i),flag,t.occ[i],n,0,-1,-1,-1,0};
        if(flag==0){m.row=s.n;s.insert(t.occ[i],t.vector(i));++inserted;}
        else if(flag==1){m.row=s.position.at(t.occ[i]);m.last=s.n-1;if(m.row!=m.last)m.moved=s.occurrence.back();s.erase(t.occ[i]);++deleted;}
        else {Answer a{};a.step=int(i);a.flag=flag;a.offset=at;
            if(flag==2)s.range(t.vector(i),radius,a.ids,a.fields,a.raw);else s.knn(t.vector(i),a.ids,a.fields,a.raw);
            s.map(a.ids);at+=a.ids.size();pe::require(at<=size_t(1)<<26,"complete-output 1GiB bound");answers.push_back(std::move(a));}
        if(flag<2){m.n_after=s.n;m.next=s.next;updates.push_back(m);
            pe::require(int(s.occurrence.size())==s.n&&s.position.at(m.id)==(flag==0?m.row:-1),"local mutation owner");
            if(flag==0)pe::require(s.occurrence.at(m.row)==m.id,"appended forward owner");
            if(m.moved>=0)pe::require(s.occurrence.at(m.row)==m.moved&&s.position.at(m.moved)==m.row,"local moved owner");}
        ck(cudaDeviceSynchronize());ops.push_back({int(i),flag,n,s.n,ms(begin)});
        // Diagnostic-only dry processes are never primary samples.
        if(dry&&G3_PROGRESSIVE){if(inserted==20&&deleted==20&&!p20){probe(s,data,pool,int(i),radius,probes,probe_counts,probe_at);p20=true;}
            if(inserted==40&&deleted==40&&!p40){probe(s,data,pool,int(i),radius,probes,probe_counts,probe_at);p40=true;}}
    }
    double events=ms(start);getrusage(RUSAGE_SELF,&after);ck(cudaMemGetInfo(&free,&total));size_t after_events=total-free;
    tick=Clock::now();if(dry&&G3_PROGRESSIVE){pe::require(p20&&p40,"exact snapshot checkpoints");probe(s,data,pool,int(t.flags.size()),radius,probes,probe_counts,probe_at);probe_counts.close();write_answers(out+".probe",probes);}
    // Human-approved excluded interval: all final bytes and full maps, before release.
    final_proof(s,t,data,out);if constexpr(G3_PROGRESSIVE) s.progressive.write_audit(out);double offline=ms(tick);
    size_t query_bytes=size_t(s.capacity)*(4+4+4+1+4+8)+960*4+4+s.allocated_scratch_bytes+(G3_PROGRESSIVE?size_t(s.capacity)*32:0);
    int swaps=s.swaps,norm_updates=s.norm_updates,capacity=s.capacity;size_t inserted_bytes=s.inserted_bytes,swapped_bytes=s.swapped_bytes;int final_n=s.n;size_t fwd=s.occurrence.capacity()*4,reverse=s.position.capacity()*4;
    tick=Clock::now();auto final=s.occurrence;s.release_service();double release=ms(tick);double trace=events+release;
    ck(cudaMemGetInfo(&free,&total));size_t final_used=total-free;
    write_answers(out,answers);std::ofstream operations(out+".ops.csv"),ownership(out+".ownership.csv"),meta(out+".meta.json");
    operations<<std::setprecision(17)<<"step,flag,n_before,n_after,ack_ms,rebuild_ms\n";
    for(auto& o:ops)operations<<o.step<<','<<o.flag<<','<<o.n_before<<','<<o.n_after<<','<<o.ack<<",0\n";
    ownership<<"step,flag,id,n_before,n_after,row,last,moved,next\n";
    for(auto& m:updates)ownership<<m.step<<','<<m.flag<<','<<m.id<<','<<m.n_before<<','<<m.n_after<<','<<m.row<<','<<m.last<<','<<m.moved<<','<<m.next<<'\n';
    auto seconds=[](timeval x){return x.tv_sec+x.tv_usec*1e-6;};
    meta<<std::setprecision(17)<<"{\"variant\":\"D"<<G3_PROGRESSIVE<<"\",\"dry\":"<<(dry?"true":"false")<<",\"setup_ms\":"<<setup<<",\"events_ms\":"<<events<<",\"trace_ms\":"<<trace<<",\"release_ms\":"<<release<<",\"offline_final_and_probe_ms\":"<<offline<<",\"context_ms\":"<<context
        <<",\"cpu_event_user_s\":"<<seconds(after.ru_utime)-seconds(before.ru_utime)<<",\"cpu_event_system_s\":"<<seconds(after.ru_stime)-seconds(before.ru_stime)
        <<",\"device_used_built_bytes\":"<<built<<",\"device_used_after_events_bytes\":"<<after_events<<",\"device_used_final_bytes\":"<<final_used<<",\"vector_storage_bytes\":"<<data.size()*4<<",\"norm_storage_bytes\":"<<capacity*4
        <<",\"forward_map_capacity_bytes\":"<<fwd<<",\"reverse_map_capacity_bytes\":"<<reverse<<",\"query_owned_bytes\":"<<query_bytes<<",\"progressive_state_bytes\":"<<(G3_PROGRESSIVE?size_t(capacity)*32:0)<<",\"cub_scratch_bytes\":"<<s.allocated_scratch_bytes
        <<",\"capacity\":"<<capacity<<",\"final_live\":"<<final_n<<",\"rebuilds\":0,\"norm_updates\":"<<norm_updates<<",\"swap_deletes\":"<<swaps<<",\"inserted_H2D_bytes\":"<<inserted_bytes<<",\"swap_D2D_bytes\":"<<swapped_bytes<<",\"client_payload_bytes\":"<<at*16<<"}\n";
    pe::require(bool(operations)&&bool(ownership)&&bool(meta),"trace ledger persistence");
}
int main(int argc,char** argv)try{
    if(argc!=7)throw std::runtime_error("DATA TRACE_PREFIX RADIUS OUTPUT PROBE_POOL DRY");
    auto begin=Clock::now();pe::Trace measured,warm;measured.load(argv[2]);warm.load(std::string(argv[2])+".warmup");pe::require(measured.n==warm.n&&measured.d==960&&warm.d==960,"shape");
    int inserts=std::max(std::count(measured.flags.begin(),measured.flags.end(),0),std::count(warm.flags.begin(),warm.flags.end(),0));std::ifstream f(argv[1],std::ios::binary);int h[3]{};f.read((char*)h,12);pe::require(bool(f)&&h[0]==960&&h[1]==measured.n&&h[2]==2,"data header");
    std::vector<float> data(size_t(h[1]+inserts)*960);f.read((char*)data.data(),size_t(h[1])*960*4);pe::require(bool(f)&&f.peek()==EOF,"data bytes");for(float x:data)pe::require(std::isfinite(x)&&std::abs(x)<=16,"common numerical envelope");
    float radius=std::stof(argv[3]);pe::require(std::isfinite(radius)&&radius>=0,"radius");std::ifstream p(argv[5]);std::vector<int> pool;int q;while(p>>q){pe::require(q>=0&&q<h[1],"probe query ID");pool.push_back(q);}bool dry=std::stoi(argv[6]);pe::require(!dry||!G3_PROGRESSIVE||pool.size()==32,"probe pool");
    double parse=ms(begin);begin=Clock::now();ck(cudaFree(nullptr));double context=ms(begin);
    execute(warm,data,std::string(argv[4])+".warmup",radius,context,{},false);execute(measured,data,argv[4],radius,context,pool,dry);
    std::ofstream s(std::string(argv[4])+".scope.json");s<<"{\"parse_ms\":"<<parse<<",\"warmup_events\":"<<warm.flags.size()<<",\"warmup_queries\":8}\n";pe::require(bool(s),"scope persistence");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
