// Synthetic high-entropy bit tests and dependency-shape timing;not GIST service.
static std::vector<int> shape_ids(int n,int b,const std::string& shape){
    std::vector<int> ids;
    if(shape=="chain"){ids.push_back(0);for(int i=1;i<b;i++)ids.push_back(n-i);}
    else{ids.resize(n);std::iota(ids.begin(),ids.end(),0);if(shape=="random"){std::mt19937 r(2026101516);std::shuffle(ids.begin(),ids.end(),r);}else require(shape=="localized","shape name");ids.resize(b);}
    return ids;
}
static double generic_once(int n,int dimensions,const std::vector<int>& ids,cudaStream_t stream,uint64_t& native_moves,uint64_t& net_rows){
    require(n>0&&!ids.empty()&&ids.size()<=512&&ids.size()<=size_t(n),"generic envelope");
    std::set<int> valid;for(int id:ids)require(id>=0&&id<n&&valid.insert(id).second,"generic valid distinct IDs");
    std::vector<uint32_t> before(size_t(n)*dimensions),expected,actual(before.size());uint32_t seed=2026101517;
    for(auto& v:before){seed=1664525u*seed+1013904223u;v=seed;}
    for(int r=0;r<std::min(n,3);r++)std::fill_n(before.data()+size_t(r)*dimensions,dimensions,0x7fc01234u);
    expected=before;std::vector<int> f(n),p(n),ref(n),rp(n);std::iota(f.begin(),f.end(),0);p=f;ref=f;rp=f;
    for(int id:ids){int row=rp[id],last=int(ref.size())-1;if(row!=last){std::copy_n(expected.data()+size_t(last)*dimensions,dimensions,expected.data()+size_t(row)*dimensions);int moved=ref.back();ref[row]=moved;rp[moved]=row;}ref.pop_back();rp[id]=-1;}
    uint32_t* device=nullptr;RowMove* moves=nullptr;alloc(device,before.size());alloc(moves,512);
    ck(cudaMemcpyAsync(device,before.data(),before.size()*4,cudaMemcpyHostToDevice,stream));ck(cudaStreamSynchronize(stream));
    auto t=Clock::now();std::set<int> unique;for(int id:ids)require(id>=0&&id<n&&p[id]>=0&&unique.insert(id).second,"native validation");
#if UPDATE>0
    BatchPlan plan(n,int(ids.size()),UPDATE==2);
#endif
    native_moves=0;net_rows=0;
    for(int id:ids){int row=p[id],last=int(f.size())-1;if(row!=last){
#if UPDATE==0
        ck(cudaMemcpyAsync(device+size_t(row)*dimensions,device+size_t(last)*dimensions,size_t(dimensions)*4,cudaMemcpyDeviceToDevice,stream));
#else
        plan.push(last,row);
#endif
        int moved=f.back();f[row]=moved;p[moved]=row;++native_moves;
    }f.pop_back();p[id]=-1;}
#if UPDATE==0
    ck(cudaStreamSynchronize(stream));
#else
    plan.finish(UPDATE==1);execute_plan((float*)device,stream,moves,plan,dimensions);net_rows=plan.net.size();
#endif
    double ack=ms(t);require(f==ref&&p==rp,"generic complete ownership");
    ck(cudaMemcpyAsync(actual.data(),device,actual.size()*4,cudaMemcpyDeviceToHost,stream));ck(cudaStreamSynchronize(stream));
    require(actual==expected,"generic every allocated bit including retired rows/duplicate vectors/NaNs");drop(moves);drop(device);return ack;
}
static void ownership_selftest(){
    uint64_t tested=0,native=0,net=0;std::array<cudaStream_t,2> streams;for(auto& s:streams)ck(cudaStreamCreate(&s));
    for(int n:{65,513})for(int dimensions:{1,31,128,960,1024})for(int b:{1,7,32,65,511,512})for(const char* shape:{"random","localized","chain"}){
        int count=std::min(n,b);generic_once(n,dimensions,shape_ids(n,count,shape),streams[tested%2],native,net);++tested;
    }
    // Native Store rejection must precede every mutation and copy submission.
    std::vector<float> x(513*960);for(size_t i=0;i<x.size();i++)x[i]=float((i*1664525u+1013904223u)%10000)/10000;
    Store s;s.build(x,513,2048);int rejected=0;
    for(auto ids:{std::vector<int>{},std::vector<int>{0,0},std::vector<int>{-1},std::vector<int>{513},std::vector<int>(513,1)}){
        auto old=s.occurrence;auto reverse=s.position;auto count=s.mutations.size();bool threw=false;
        try{s.erase(ids);}catch(const std::exception&){threw=true;}
        require(threw&&s.occurrence==old&&s.position==reverse&&s.mutations.size()==count,"invalid delete atomicity");++rejected;
    }
    s.erase({0});auto old=s.occurrence;bool twice=false;try{s.erase({0});}catch(const std::exception&){twice=true;}
    require(twice&&s.occurrence==old,"repeated delete across ACKs rejected");s.release();
    for(auto stream:streams)ck(cudaStreamDestroy(stream));
    std::cout<<"OWNERSHIP_SELFTEST full_capacity_cases="<<tested<<" invalid_rejections="<<rejected+1<<" streams=2 dimensions=1,31,128,960,1024\n";
}
static void shape_benchmark(const std::string& shape,const std::string& out){
    cudaStream_t stream;ck(cudaStreamCreate(&stream));std::ofstream f(out+".shape.csv");f<<"D,iteration,ACK_ms,native_moves,compiled_rows\n"<<std::setprecision(17);
    for(int dimensions:{128,960}){auto ids=shape_ids(4096,512,shape);uint64_t native,net;
        for(int i=0;i<2;i++)generic_once(4096,dimensions,ids,stream,native,net);
        for(int i=0;i<32;i++){double ack=generic_once(4096,dimensions,ids,stream,native,net);f<<dimensions<<','<<i<<','<<ack<<','<<native<<','<<net<<'\n';}
    }ck(cudaStreamDestroy(stream));require(bool(f),"shape persistence");
    std::ofstream meta(out+".meta.json");meta<<"{\"passed\":true,\"kind\":\"shape\",\"UPDATE\":"<<UPDATE<<",\"N\":4096,\"B\":512,\"warmups_per_D\":2,\"iterations_per_D\":32,\"every_capacity_bit_compared\":true}\n";
}
