// Frozen search kernels with serial, exact-occurrence append/swap-delete storage.
#define main inherited_static_main
#include "range_base.cuh"
#undef main
#include "selected.cuh"
#include <cuda_profiler_api.h>
#include <sys/resource.h>
#include <cstring>
#include <numeric>
#include <random>
#include <set>
#include <unordered_map>
#ifndef MODE
#error Explicit system MODE required
#endif
static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
struct Mutation {int kind,id,before,row,last,moved,next,after;};
static_assert(sizeof(Mutation)==32,"eight native32-bit mutation fields");
struct Cost {double submit=0,tail=0;};
struct Answer {int phase,slot,mutation,invocation;double ack=0;std::vector<int> ids;std::vector<float> fields;std::vector<double> raw,authority;};
struct Op {int kind,phase,slot,mutation,before,after,rows;double ack,stats_submit,stats_tail;};

#if MODE==3
// One owner per dimension; stream order protects gather -> overwrite -> delta.
__global__ void gather_deleted(const float* x,const int* rows,float* out,int count){
    int k=int(blockIdx.x)*256+threadIdx.x;
    if(k<count*960)out[k]=x[size_t(rows[k/960])*960+k%960];
}
__global__ void maintain_mean(const float* rows,int count,double sign,int live,double* sums,float* mean){
    int j=int(blockIdx.x)*256+threadIdx.x;
    if(j<960){double value=sums[j];
        for(int r=0;r<count;r++)value=__dadd_rn(value,__dmul_rn(sign,double(rows[size_t(r)*960+j])));
        sums[j]=value;mean[j]=live?__double2float_rn(__ddiv_rn(value,double(live))):0.f;
    }
}
#endif

struct Store {
    ProgressiveScan p;std::vector<int> occurrence,position;std::vector<Mutation> mutations;
    int next=0,capacity=0;uint64_t inserted=0,swapped=0,stats_rows=0,stats_calls=0;
#if MODE==3
    double* sums=nullptr;float *device_mean=nullptr,*deleted=nullptr;int* gather_rows=nullptr;
#endif
    void build(const std::vector<float>& x,int n,int extra){
        require(n>0&&n<=1000000&&x.size()==size_t(n)*960&&extra>=0,"store shape");
        p.build(x,n,960);capacity=n;next=n;occurrence.resize(n);std::iota(occurrence.begin(),occurrence.end(),0);
        occurrence.reserve(n);position.assign(n+extra,-1);for(int i=0;i<n;i++)position[i]=i;
        mutations.reserve(size_t(extra)*2);
#if MODE==3
        alloc(sums,960);alloc(device_mean,960);alloc(deleted,512*960);alloc(gather_rows,512);
        std::array<double,960> anchor{};for(int j=0;j<960;j++)anchor[j]=double(p.means[j])*n;
        ck(cudaMemcpyAsync(sums,anchor.data(),960*8,cudaMemcpyHostToDevice,p.stream));
        ck(cudaMemcpyAsync(device_mean,p.means.data(),960*4,cudaMemcpyHostToDevice,p.stream));
        ck(cudaStreamSynchronize(p.stream));
#endif
    }
    Cost erase(const std::vector<int>& ids){
        require(!ids.empty()&&ids.size()<=512,"delete batch bound");
        std::set<int> unique;for(int id:ids)require(id>=0&&id<next&&position.at(id)>=0&&unique.insert(id).second,"live unique delete IDs");
        Cost c;
#if MODE==3
        auto begin=Clock::now();std::vector<int> rows;rows.reserve(ids.size());for(int id:ids)rows.push_back(position[id]);
        ck(cudaMemcpyAsync(gather_rows,rows.data(),rows.size()*4,cudaMemcpyHostToDevice,p.stream));
        gather_deleted<<<(int(ids.size())*960+255)/256,256,0,p.stream>>>(p.database,gather_rows,deleted,int(ids.size()));ck(cudaGetLastError());
        c.submit=ms(begin);
#endif
        for(int id:ids){int row=position[id],last=p.n-1,moved=row==last?-1:occurrence.back();
            Mutation m{0,id,p.n,row,last,moved,next,p.n-1};
            if(row!=last){ck(cudaMemcpyAsync(p.database+size_t(row)*960,p.database+size_t(last)*960,960*4,cudaMemcpyDeviceToDevice,p.stream));
                occurrence[row]=moved;position[moved]=row;swapped+=960*4;}
            occurrence.pop_back();position[id]=-1;--p.n;mutations.push_back(m);
            require(int(occurrence.size())==p.n&&position[id]==-1,"delete local owner");
            if(moved>=0)require(occurrence[row]==moved&&position[moved]==row,"swap local owner");
        }
#if MODE==3
        auto tick=Clock::now();maintain_mean<<<4,256,0,p.stream>>>(deleted,int(ids.size()),-1.,p.n,sums,device_mean);ck(cudaGetLastError());
        ck(cudaMemcpyAsync(p.means.data(),device_mean,960*4,cudaMemcpyDeviceToHost,p.stream));c.submit+=ms(tick);
        ck(cudaStreamSynchronize(p.stream));c.tail=ms(tick);stats_rows+=ids.size();++stats_calls;
#else
        ck(cudaStreamSynchronize(p.stream));
#endif
        return c;
    }
    Cost insert(const float* values,int count){
        require(count>0&&count<=512&&p.n+count<=capacity&&next+count<=int(position.size()),"insert batch capacity");
        int start=p.n;ck(cudaMemcpyAsync(p.database+size_t(start)*960,values,size_t(count)*960*4,cudaMemcpyHostToDevice,p.stream));
        for(int k=0;k<count;k++){
            int id=next;Mutation m{1,id,p.n,p.n,-1,-1,next+1,p.n+1};require(position[id]==-1,"fresh insertion ID");
            position[id]=p.n;occurrence.push_back(id);++p.n;++next;mutations.push_back(m);
            require(occurrence.back()==id&&position[id]==p.n-1,"insert local owner");
        }
        inserted+=uint64_t(count)*960*4;Cost c;
#if MODE==3
        auto tick=Clock::now();maintain_mean<<<4,256,0,p.stream>>>(p.database+size_t(start)*960,count,1.,p.n,sums,device_mean);ck(cudaGetLastError());
        ck(cudaMemcpyAsync(p.means.data(),device_mean,960*4,cudaMemcpyDeviceToHost,p.stream));c.submit=ms(tick);
        ck(cudaStreamSynchronize(p.stream));c.tail=ms(tick);stats_rows+=count;++stats_calls;
#else
        ck(cudaStreamSynchronize(p.stream));
#endif
        return c;
    }
    void query(const float* q,float radius,Answer& a){
        p.last_scores.clear();a.invocation=p.invocation;p.range(q,radius,a.ids,a.fields,a.raw);
        for(int& id:a.ids){require(id>=0&&id<p.n,"query physical owner");id=occurrence[id];}
    }
    uint64_t extra_device_bytes()const{return MODE==3?uint64_t(960)*12+512*960*4+512*4:0;}
    void release(){
#if MODE==3
        drop(sums);drop(device_mean);drop(deleted);drop(gather_rows);
#endif
        p.release();std::vector<int>().swap(occurrence);std::vector<int>().swap(position);std::vector<Mutation>().swap(mutations);
        std::vector<StageRecord>().swap(p.records);std::vector<std::array<double,3>>().swap(p.outputs);
        for(auto& a:p.last_ids)std::vector<int>().swap(a);std::vector<double>().swap(p.last_scores);
#if MODE>=2
        std::vector<std::array<double,3>>().swap(p.ordering);
#endif
    }
};

static double score(const float* x,const float* q){double s=0;for(int j=0;j<960;j++){double d=double(x[j])-double(q[j]);s=s+d*d;}return s;}
static void selftest(){
    std::mt19937 rng(2026101504);int checks=0,empty=0;uint64_t values=0;
    for(int epoch=0;epoch<10;epoch++){
        std::array<Store,2> stores;std::array<std::unordered_map<int,std::array<float,960>>,2> truth;
        std::array<std::vector<float>,2> initial;std::array<std::array<double,960>,2> expected{};
        for(int slot=0;slot<2;slot++){
            int n=slot?513:65;initial[slot].resize(size_t(n)*960);
            for(float& v:initial[slot])v=float(int(rng()%17)-8)/128.f;
            for(int r=0;r<5;r++)std::fill_n(initial[slot].data()+r*960,960,0.f);
            initial[slot][2*960]=1.f;initial[slot][3*960]=std::nextafter(1.f,0.f);initial[slot][4*960]=std::nextafter(1.f,2.f);
            for(int r=0;r<n;r++){std::array<float,960> v;std::copy_n(initial[slot].data()+r*960,960,v.data());truth[slot][r]=v;}
            stores[slot].build(initial[slot],n,6000);stores[slot].p.audit_mode=4;
#if MODE==3
            for(int j=0;j<960;j++)expected[slot][j]=double(stores[slot].p.means[j])*n;
#endif
        }
        for(int it=0;it<10;it++)for(int slot=0;slot<2;slot++){
            auto& s=stores[slot];auto& t=truth[slot];int options[]={1,7,32,65,128,511,512};
            int count=std::min(s.p.n,options[(epoch*10+it)%7]);std::vector<int> victims(s.occurrence.begin(),s.occurrence.begin()+count);
            s.erase(victims);for(int id:victims){
#if MODE==3
                for(int j=0;j<960;j++)expected[slot][j]-=double(t.at(id)[j]);
#endif
                t.erase(id);}
#if MODE==3
            for(int j=0;j<960;j++)require(s.p.means[j]==(s.p.n?float(expected[slot][j]/s.p.n):0.f),"selftest deleted mean");
#endif
            auto verify=[&](float radius){
                std::array<float,960> q{};if(it%3==0)q.fill(4.f);Answer a{};s.query(q.data(),radius,a);
                std::set<int> want,got(a.ids.begin(),a.ids.end());for(auto& kv:t)if(score(kv.second.data(),q.data())<=double(radius)*radius)want.insert(kv.first);
                require(got==want&&got.size()==a.ids.size(),"selftest complete exact members");
                require(a.ids.size()==s.p.last_scores.size(),"selftest internal full-score count");
                for(size_t i=0;i<a.ids.size();i++){
                    double ref=score(t.at(a.ids[i]).data(),q.data());require(std::memcmp(&ref,&s.p.last_scores[i],8)==0,"selftest FP64 bits");
                    require(a.raw[i]==double(float(ref)),"selftest native squared field");++values;
                }
                ++checks;if(a.ids.empty())++empty;
            };
            verify(it%3==1?100.f:1.f);std::vector<float> incoming(size_t(count)*960);
            for(float& v:incoming)v=float(int(rng()%33)-16)/64.f;
            int first=s.next;s.insert(incoming.data(),count);
            for(int r=0;r<count;r++){std::array<float,960> v;std::copy_n(incoming.data()+r*960,960,v.data());t[first+r]=v;}
#if MODE==3
            for(int r=0;r<count;r++)for(int j=0;j<960;j++)expected[slot][j]+=double(incoming[size_t(r)*960+j]);
            for(int j=0;j<960;j++)require(s.p.means[j]==float(expected[slot][j]/s.p.n),"selftest inserted mean");
#endif
            verify(it%3==1?100.f:1.f);
            require(int(t.size())==s.p.n,"selftest live count");
            for(int r=0;r<s.p.n;r++)require(s.position[s.occurrence[r]]==r,"selftest full bijection");
        }
        for(auto& s:stores)s.release();
    }
    std::cout<<"{\"passed\":true,\"iterations\":100,\"stream_slots\":2,\"query_checks\":"<<checks<<",\"empty_answers\":"<<empty<<",\"full_hit_FP64_bit_checks\":"<<values<<",\"pointer_churn_epochs\":10,\"max_batch\":512}\n";
}

template<class T> static void persist(const std::string& p,const std::vector<T>& values){
    std::ofstream f(p,std::ios::binary);f.write((char*)values.data(),values.size()*sizeof(T));require(bool(f),"binary persistence");
}
static void final_proof(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){
    std::vector<float> buffer(4096*960);uint64_t bytes=0;
    for(int start=0;start<s.p.n;start+=4096){int count=std::min(4096,s.p.n-start);
        ck(cudaMemcpyAsync(buffer.data(),s.p.database+size_t(start)*960,size_t(count)*960*4,cudaMemcpyDeviceToHost,s.p.stream));ck(cudaStreamSynchronize(s.p.stream));
        for(int r=0;r<count;r++){int id=s.occurrence[start+r];require(s.position[id]==start+r,"actual final bijection");
            const float* expected=id<s.capacity?x.data()+size_t(id)*960:incoming.data()+size_t(id-s.capacity)*960;
            require(std::memcmp(expected,buffer.data()+size_t(r)*960,960*4)==0,"every final actual GPU vector byte");bytes+=960*4;}
    }
    persist(out+".physical.i32",s.occurrence);persist(out+".reverse.i32",s.position);persist(out+".mutations.i32",s.mutations);
    std::ofstream f(out+".final.json");f<<"{\"passed\":true,\"all_vector_bytes_compared\":"<<bytes<<",\"live\":"<<s.p.n<<"}\n";require(bool(f),"final proof persistence");
}
static void execute(const std::vector<float>& x,const std::vector<float>& incoming,const std::vector<int>& victims,
                    const std::array<int,32>& qids,const std::array<int,5>& ends,int workload,float radius,
                    const std::string& out,int diagnostic){
    int n=int(x.size()/960);auto tick=Clock::now();Store s;s.build(x,n,int(victims.size()));
    s.p.audit_mode=diagnostic==2?4:0;double build=ms(tick);std::vector<Answer> answers;std::vector<Op> ops;
    answers.reserve(168);ops.reserve(2200);std::vector<std::array<float,960>> means;
    auto request=[&](int phase,int slot,int mutation,bool formal){
        if(formal&&diagnostic==1)ck(cudaProfilerStart());
        auto begin=Clock::now();Answer a{};a.phase=phase;a.slot=slot;a.mutation=mutation;int before=s.p.n;
        s.query(x.data()+size_t(qids[slot])*960,radius,a);a.ack=ms(begin);
        if(diagnostic==2)a.authority=s.p.last_scores;
        if(formal)ops.push_back({2,phase,slot,mutation,before,s.p.n,1,a.ack,0,0});
        answers.push_back(std::move(a));if(formal&&diagnostic==1)ck(cudaProfilerStop());
    };
    for(int i=0;i<8;i++)request(-1,i,0,false);
    size_t free,total;ck(cudaMemGetInfo(&free,&total));size_t used_built=total-free;
    rusage cpu_before{},cpu_after{};getrusage(RUSAGE_SELF,&cpu_before);auto service=Clock::now();int replaced=0;
    for(int phase=0;phase<5;phase++){
        bool interleaved=workload==1&&phase>0;
        while(replaced<ends[phase]){
            int count=std::min(workload==2?512:1,ends[phase]-replaced);std::vector<int> ids(victims.begin()+replaced,victims.begin()+replaced+count);
            if(diagnostic==3)ck(cudaProfilerStart());
            auto begin=Clock::now();int before=s.p.n;Cost c=s.erase(ids);
            ops.push_back({0,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});
            begin=Clock::now();before=s.p.n;c=s.insert(incoming.data()+size_t(replaced)*960,count);replaced+=count;
            ops.push_back({1,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});
            if(diagnostic==3)ck(cudaProfilerStop());
            if(interleaved){int k=replaced-ends[phase-1]-1;request(phase,2*k,replaced,true);request(phase,2*k+1,replaced,true);}
        }
        if(!interleaved)for(int k=0;k<32;k++)request(phase,k,replaced,true);
#if MODE>=2
        means.push_back(s.p.means);
#endif
    }
    double events=ms(service);getrusage(RUSAGE_SELF,&cpu_after);ck(cudaMemGetInfo(&free,&total));size_t used_after=total-free;
    tick=Clock::now();final_proof(s,x,incoming,out);s.p.write_audit(out);
    std::ofstream qr(out+".queries.csv"),operations(out+".ops.csv");
    std::ofstream oi(out+".ids.i32",std::ios::binary),of(out+".dist.f32",std::ios::binary),orr(out+".squared.f64",std::ios::binary),oa(out+".authority.f64",std::ios::binary);
    qr<<std::setprecision(17)<<"phase,slot,mutation,invocation,count,offset,ack_ms\n";size_t offset=0;
    for(auto& a:answers){qr<<a.phase<<','<<a.slot<<','<<a.mutation<<','<<a.invocation<<','<<a.ids.size()<<','<<offset<<','<<a.ack<<'\n';
        oi.write((char*)a.ids.data(),a.ids.size()*4);of.write((char*)a.fields.data(),a.fields.size()*4);orr.write((char*)a.raw.data(),a.raw.size()*8);oa.write((char*)a.authority.data(),a.authority.size()*8);offset+=a.ids.size();}
    require(offset<=(size_t(1)<<26),"complete output bound");
    operations<<std::setprecision(17)<<"kind,phase,slot,mutation,n_before,n_after,rows,ack_ms,stats_submit_ms,stats_tail_inclusive_ms\n";
    double query_ms=0,update_ms=0;int update_batches=0;
    for(auto& o:ops){operations<<o.kind<<','<<o.phase<<','<<o.slot<<','<<o.mutation<<','<<o.before<<','<<o.after<<','<<o.rows<<','<<o.ack<<','<<o.stats_submit<<','<<o.stats_tail<<'\n';
        if(o.kind==2)query_ms+=o.ack;else{update_ms+=o.ack;++update_batches;}}
    require(bool(qr)&&bool(operations)&&bool(oi)&&bool(of)&&bool(orr)&&bool(oa),"complete outputs");
    qr.close();operations.close();oi.close();of.close();orr.close();oa.close();
    if(!means.empty()){std::ofstream f(out+".means.f32",std::ios::binary);for(auto& mu:means)f.write((char*)mu.data(),960*4);require(bool(f),"mean snapshots");}
    double offline=ms(tick);uint64_t inserted=s.inserted,swapped=s.swapped,statrows=s.stats_rows,statcalls=s.stats_calls;
    uint64_t query_owned=uint64_t(n)*49+960*4+4+s.p.bytes+(MODE>=2?240:0),extra=s.extra_device_bytes();
    tick=Clock::now();s.release();std::vector<Answer>().swap(answers);std::vector<Op>().swap(ops);std::vector<std::array<float,960>>().swap(means);double release=ms(tick);
    auto seconds=[](timeval t){return t.tv_sec+double(t.tv_usec)*1e-6;};std::ofstream meta(out+".meta.json");
    meta<<std::setprecision(17)<<"{\"mode\":"<<MODE<<",\"N\":"<<n<<",\"D\":960,\"B\":1,\"diagnostic\":"<<diagnostic<<",\"formal_queries\":160,\"warmup_queries\":8,\"replacements\":"<<replaced
        <<",\"update_batches\":"<<update_batches<<",\"point_updates\":"<<2*replaced<<",\"build_ms\":"<<build<<",\"events_ms\":"<<events<<",\"release_ms\":"<<release<<",\"service_ms\":"<<events+release
        <<",\"query_ms\":"<<query_ms<<",\"update_ms_including_statistics\":"<<update_ms<<",\"other_ms\":"<<events-query_ms-update_ms<<",\"standalone_maintenance_ms\":0,\"offline_validation_and_export_ms\":"<<offline
        <<",\"insert_H2D_request_bytes\":"<<inserted<<",\"swap_D2D_request_bytes\":"<<swapped<<",\"statistics_rows\":"<<statrows<<",\"statistics_calls\":"<<statcalls
        <<",\"raw_device_bytes\":"<<uint64_t(n)*960*4<<",\"base_query_device_bytes\":"<<query_owned<<",\"extra_statistics_device_bytes\":"<<extra<<",\"device_owned_peak_bytes\":"<<uint64_t(n)*960*4+query_owned+extra
        <<",\"device_observed_built_bytes\":"<<used_built<<",\"device_observed_after_events_bytes\":"<<used_after
        <<",\"cpu_events_user_s\":"<<seconds(cpu_after.ru_utime)-seconds(cpu_before.ru_utime)<<",\"cpu_events_system_s\":"<<seconds(cpu_after.ru_stime)-seconds(cpu_before.ru_stime)
        <<",\"process_peak_RSS_KiB_including_client_inputs\":"<<cpu_after.ru_maxrss<<",\"rebuilds\":0,\"client_complete_items\":"<<offset<<"}\n";
    require(bool(meta),"metadata persistence");
}

int main(int argc,char** argv)try{
    if(argc==2&&std::string(argv[1])=="--selftest"){selftest();return 0;}
    if(argc!=9)throw std::runtime_error("DATA INPUT_PREFIX QIDS RADIUS OUTPUT WORKLOAD DIAGNOSTIC N");
    int n=std::stoi(argv[8]),workload=std::stoi(argv[6]),diagnostic=std::stoi(argv[7]);require(n>0&&n<=1000000&&workload>=0&&workload<=2&&diagnostic>=0&&diagnostic<=3,"arguments");
    std::ifstream input(argv[1],std::ios::binary);int h[3]{};input.read((char*)h,12);require(h[0]==960&&h[1]==1000000&&h[2]==2,"data header");
    std::vector<float> x(size_t(n)*960);input.read((char*)x.data(),x.size()*4);require(bool(input),"initial data bytes");
    std::string prefix=argv[2];std::ifstream v(prefix+".victims.i32",std::ios::binary),inc(prefix+".incoming.f32",std::ios::binary),config(prefix+".ends.txt"),pool(argv[3]);
    std::array<int,5> ends{};for(int& e:ends)config>>e;require(bool(config)&&ends[0]==0&&ends[4]<=n/2,"checkpoint bounds");
    std::vector<int> victims(ends[4]);std::vector<float> incoming(size_t(ends[4])*960);v.read((char*)victims.data(),victims.size()*4);inc.read((char*)incoming.data(),incoming.size()*4);
    require(bool(v)&&bool(inc)&&v.peek()==EOF&&inc.peek()==EOF,"update payload bytes");
    std::set<int> unique;for(int id:victims)require(id>=0&&id<n&&unique.insert(id).second,"unique original victims");
    std::array<int,32> qids{};for(int& q:qids){pool>>q;require(bool(pool)&&q>=0&&q<n,"query ID");}
    for(float value:incoming)require(std::isfinite(value)&&std::abs(value)<=16,"insert envelope");
    float radius=std::stof(argv[4]);require(std::isfinite(radius)&&radius>=0,"radius");
    execute(x,incoming,victims,qids,ends,workload,radius,argv[5],diagnostic);return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
