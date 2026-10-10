// Diagnostic Host harness over the unchanged qualified P implementation.
#ifdef PV_CAPTURE
#define REGION_COUNTERS
#endif
#define main qualified_parent_main
#include "main.cu"
#undef main
#undef short
#include <filesystem>
namespace pv {
struct Answer {std::vector<int> ids;std::vector<float> fields;double ms;float front,verify,output;std::vector<float> levels;};
struct Row {int pass,mode,query,qid;Answer answer;};
template<class T> void write(const std::string& p,const std::vector<T>& v) {
    uk::require(!std::filesystem::exists(p),"do not overwrite probe evidence");
    std::ofstream f(p,std::ios::binary);f.write((const char*)v.data(),v.size()*sizeof(T));uk::require(bool(f),"write probe");
}
template<class T> std::vector<T> read(const std::string& p,size_t count) {
    std::vector<T> v(count);std::ifstream f(p,std::ios::binary);f.read((char*)v.data(),count*sizeof(T));uk::require(bool(f)&&f.peek()==EOF,"probe input size");return v;
}
// Range output adaptation only: the original FULL verifier computes every score.
__global__ void range_fields(const double* scores,int n,float radius,int* hit,float* fields) {
    int p=blockIdx.x*blockDim.x+threadIdx.x;if(p>=n)return;
    double s=scores[p];hit[p]=s<=__dmul_rn(double(radius),double(radius));
    if(hit[p])fields[p]=__double2float_rn(__dsqrt_rn(s));
}
struct Probe {
    std::vector<float> data;int n,d;float radius;std::string out;
    int* deleted=nullptr;int* replay_leaves=nullptr;uint8_t* replay_masks=nullptr;
    std::vector<cudaEvent_t> events;std::vector<Row> rows;
    Probe(int count,int dim,float rad,std::string path):n(count),d(dim),radius(rad),out(path) {}
    void record(int i){u10_ck(cudaEventRecord(events[i]));}
    float elapsed(int a,int b){float ms;u10_ck(cudaEventElapsedTime(&ms,events[a],events[b]));return ms;}
    void setup(const std::vector<float>& input) {
        data=input;data_info=nullptr;data_d=nullptr;
        u10_ck(cudaMallocManaged((void**)&data_info,12));data_info[0]=d;data_info[1]=n;data_info[2]=2;
        u10_ck(cudaMallocManaged((void**)&data_d,size_t(n+1)*d*4));
        u10_ck(cudaMemcpy(data_d,data.data(),size_t(n)*d*4,cudaMemcpyHostToDevice));
        MAX_H=uk::tree_height(n);indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
        target::refresh_bounds(data_d,node_list,empty_list,id_list,max_node_num[0],n,d);
        rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],n,TREE_ORDER);
        u10_ck(cudaMalloc((void**)&deleted,n*4));u10_ck(cudaMemset(deleted,0,n*4));
        u10_ck(cudaMallocManaged((void**)&qid_list,4));qid_list[0]=n;
        auto& b=rex::bridge;b.view.d=d;b.view.data=data_d;b.view.deleted=deleted;b.view.qids=qid_list;
        events.resize(b.plan.level_offsets.size()+5);
        for(auto& e:events)u10_ck(cudaEventCreate(&e));
        int nn=max_node_num[0];auto hn=bt::copy(node_list,nn);auto he=bt::copy(empty_list,nn);
        auto lo=bt::copy(target::bounds.lo,nn),hi=bt::copy(target::bounds.hi,nn);
        for(int i=0;i<nn;i++)if(he[i]){std::memset(&hn[i],0,sizeof(TN));lo[i]=hi[i]=0;}
        write(out+"/nodes",hn);write(out+"/empty",he);write(out+"/order",bt::copy(id_list,n));
        write(out+"/lo",lo);write(out+"/hi",hi);write(out+"/leaves",b.plan.leaves);
        write(out+"/offsets",b.plan.level_offsets);
    }
    Answer query(int mode,int qi,int source_qid,bool observe) {
        auto& b=rex::bridge;auto view=b.view;rex::Work work{};
#ifdef PV_CAPTURE
        uk::require(observe&&mode==0,"observer only TREE_NOW");work=b.work;
        for(auto p:{work.nodes,work.pivots,work.leaves})u10_ck(cudaMemset(p,0,view.node_count*8));
        u10_ck(cudaMemset(work.objects,0,n*8));
#else
        uk::require(!observe,"performance cannot observe");
#endif
        auto start=U10Clock::now();
        u10_ck(cudaMemcpy(data_d+size_t(n)*d,data.data()+size_t(source_qid)*d,d*4,cudaMemcpyHostToDevice));
        record(0);
        u10_ck(cudaMemset(b.hit,0,n*4));
        if(mode==0) {
            for(auto p:b.flags)u10_ck(cudaMemset(p,0,view.node_count*4));
            u10_ck(cudaMemset(b.active,0,view.node_count*4));int one=1;
            u10_ck(cudaMemcpy(b.flags[0],&one,4,cudaMemcpyHostToDevice));u10_ck(cudaMemcpy(b.active,&one,4,cudaMemcpyHostToDevice));
            int parity=0;const auto& offsets=b.plan.level_offsets;
            for(size_t l=1;l<offsets.size();l++) {
                int begin=offsets[l-1],num=offsets[l]-begin;
                if(observe)record(4+int(l)-1);
                if(num)rex::parent_groups<<<num,256>>>(view,b.parents,begin,b.flags[parity],b.flags[1-parity],b.active,radius,work);
                parity=1-parity;
            }
            if(observe)record(4+int(offsets.size())-1);
            rex::materialize<<<(b.plan.total_leaves+255)/256,256>>>(view,b.leaves,b.plan.total_leaves,b.active,b.leaf_list,work);
        }
        record(1);
        if(mode<2)rex::verify_materialized<<<b.plan.total_leaves,256>>>(view,mode==0?b.leaf_list:replay_leaves+size_t(qi)*b.plan.total_leaves,radius,b.hit,b.distances,work);
        else {
            auto& live=uk::live;
            const uint8_t* mask=mode==2?replay_masks+size_t(qi)*n:live.mask;
            verify_distances<1,false,true><<<(n+255)/256,256,d*4>>>(data_d,live.packed,qid_list,live.cutoff,mask,live.scores,n,d,1);
            range_fields<<<(n+255)/256,256>>>(live.scores,n,radius,b.hit,b.distances);
            view.slot_pid=live.identity;
        }
        record(2);u10_ck(cudaGetLastError());
        int count=thrust::reduce(thrust::device,b.hit,b.hit+n,0);
        int *counts,*prefix,*ids;float* fields;
        u10_ck(cudaMallocManaged((void**)&counts,4));counts[0]=count;
        u10_ck(cudaMallocManaged((void**)&prefix,4));prefix[0]=0;
        u10_ck(cudaMallocManaged((void**)&ids,std::max(count,1)*4));
        u10_ck(cudaMallocManaged((void**)&fields,std::max(count,1)*4));
        thrust::exclusive_scan(thrust::device,b.hit,b.hit+n,b.prefix);
        rex::collect<<<(n+255)/256,256>>>(view,b.hit,b.prefix,b.distances,ids,fields);
        u10_ck(cudaDeviceSynchronize());uk::require(!*b.error,"tree error");
        Answer a;a.ids.resize(count);a.fields.resize(count);
        if(count){u10_ck(cudaMemcpy(a.ids.data(),ids,count*4,cudaMemcpyDeviceToHost));u10_ck(cudaMemcpy(a.fields.data(),fields,count*4,cudaMemcpyDeviceToHost));}
        for(void* p:{(void*)counts,(void*)prefix,(void*)ids,(void*)fields})u10_ck(cudaFree(p));
        record(3);u10_ck(cudaEventSynchronize(events[3]));a.ms=u10_ms(start);
        a.front=elapsed(0,1);a.verify=elapsed(1,2);a.output=elapsed(2,3);
        if(observe){for(size_t l=1;l<b.plan.level_offsets.size();l++)a.levels.push_back(elapsed(4+l-1,4+l));
            std::string p=out+"/q"+std::to_string(qi);std::filesystem::create_directory(p);
            write(p+"/nodes",bt::copy(work.nodes,view.node_count));write(p+"/pivots",bt::copy(work.pivots,view.node_count));
            write(p+"/objects",bt::copy(work.objects,n));write(p+"/active",bt::copy(b.active,view.node_count));
            write(p+"/leaf_list",bt::copy(b.leaf_list,b.plan.total_leaves));write(p+"/levels_ms",a.levels);
        }
        return a;
    }
    void finish() {
        for(auto e:events)u10_ck(cudaEventDestroy(e));
        for(void* p:{(void*)replay_leaves,(void*)replay_masks,(void*)deleted})if(p)u10_ck(cudaFree(p));
        if(uk::live.owned_bytes)uk::live.finish();rex::bridge.finish();target::release_bounds();
        for(void* p:{(void*)data_info,(void*)data_d,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)qid_list,(void*)empty_list})if(p)u10_ck(cudaFree(p));
        u10_ck(cudaDeviceSynchronize());
    }
    void save() {
        std::ofstream f(out+"/queries.csv");f<<"pass,mode,query,qid,count,offset,host_ms,front_ms,verify_ms,output_ms\n"<<std::setprecision(17);
        std::vector<int> ids;std::vector<float> fields;
        for(auto& r:rows){auto& a=r.answer;f<<r.pass<<','<<r.mode<<','<<r.query<<','<<r.qid<<','<<a.ids.size()<<','<<ids.size()<<','<<a.ms<<','<<a.front<<','<<a.verify<<','<<a.output<<'\n';ids.insert(ids.end(),a.ids.begin(),a.ids.end());fields.insert(fields.end(),a.fields.begin(),a.fields.end());}
        uk::require(bool(f),"write query table");write(out+"/ids",ids);write(out+"/fields",fields);
    }
};
}
int main(int argc,char** argv) try {
    uk::require(argc==5,"DATA QIDS OUTPUT CACHE_OR_BUILD_ONLY");bt::configure();uk::require(bt::tiled,"TILED required");
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);uk::require(bool(f)&&h[1]>0&&(h[0]==128||h[0]==960)&&h[2]==2,"input header");
    std::vector<float> input(size_t(h[0])*h[1]);f.read((char*)input.data(),input.size()*4);uk::require(bool(f)&&f.peek()==EOF,"data length");
    for(float x:input)uk::require(std::isfinite(x),"finite input");
    std::ifstream qfile(argv[2]);std::vector<int> qids;int q;while(qfile>>q){uk::require(q>=0&&q<h[1],"query row");qids.push_back(q);}uk::require(qids.size()==32,"32 original queries");
    std::string out=argv[3],cache=argv[4];uk::require(std::filesystem::create_directory(out),"fresh output required");
    auto tick=U10Clock::now();u10_ck(cudaFree(nullptr));double context=u10_ms(tick);
    pv::Probe p(h[1],h[0],0.705625057220459f,out);tick=U10Clock::now();p.setup(input);double setup=u10_ms(tick);
    double layout=0,cache_ms=0,warm_ms=0;size_t cache_bytes=0,layout_bytes=0;
    if(cache!="BUILD_ONLY") {
#ifdef PV_CAPTURE
        for(int i=0;i<32;i++)p.rows.push_back({0,0,i,qids[i],p.query(0,i,qids[i],true)});
#else
        tick=U10Clock::now();uk::live.initialize(data_d,p.n,p.d,8,(p.n+31)/32*32);u10_ck(cudaMemset(uk::live.mask,1,p.n));u10_ck(cudaDeviceSynchronize());layout=u10_ms(tick);layout_bytes=uk::live.owned_bytes;
        tick=U10Clock::now();int leaves=rex::bridge.plan.total_leaves;
        auto lists=pv::read<int>(cache+"/leaf_lists",size_t(32)*leaves);auto masks=pv::read<uint8_t>(cache+"/masks",size_t(32)*p.n);
        rex::bridge.upload(p.replay_leaves,lists);rex::bridge.upload(p.replay_masks,masks);u10_ck(cudaDeviceSynchronize());cache_ms=u10_ms(tick);cache_bytes=lists.size()*4+masks.size();
        tick=U10Clock::now();for(int mode=0;mode<4;mode++)for(int i=0;i<8;i++)p.rows.push_back({-1,mode,i,qids[i],p.query(mode,i,qids[i],false)});warm_ms=u10_ms(tick);
        for(int pass=0;pass<4;pass++)for(int j=0;j<4;j++){int mode=pass%2?3-j:j;for(int i=0;i<32;i++)p.rows.push_back({pass,mode,i,qids[i],p.query(mode,i,qids[i],false)});}
#endif
    }
    tick=U10Clock::now();p.finish();double release=u10_ms(tick);p.save();
    std::ofstream meta(out+"/META.json");meta<<std::setprecision(17)<<"{\"N\":"<<p.n<<",\"D\":"<<p.d<<",\"context_ms\":"<<context<<",\"tree_setup_ms\":"<<setup<<",\"packed_setup_ms\":"<<layout<<",\"packed_owned_bytes\":"<<layout_bytes<<",\"cache_load_ms\":"<<cache_ms<<",\"cache_bytes\":"<<cache_bytes<<",\"warm_ms\":"<<warm_ms<<",\"release_ms\":"<<release<<"}\n";uk::require(bool(meta),"write metadata");u10_ck(cudaDeviceReset());return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
