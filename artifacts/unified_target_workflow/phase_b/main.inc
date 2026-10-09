#include <thread>
#include <cstring>

static int diagnostic_delay(const char* name) {
    const char* value=std::getenv(name);if(!value)return 0;
    uk::require(u10_env("TARGET_SCOPE_DIAGNOSTIC"),"timing injection requires diagnostic admission");
    size_t used=0;int ms=std::stoi(value,&used);
    uk::require(used==std::string(value).size()&&ms>=0&&ms<=1000,"diagnostic delay range");return ms;
}
static void pause_ms(int ms) {if(ms)std::this_thread::sleep_for(std::chrono::milliseconds(ms));}
static void reset_service() {
    uk::require(!uk::live.owned_bytes&&!rex::bridge.owned_bytes&&!target::bounds.bytes,"unreleased previous service");
    uk::live=uk::LiveKnn{};rex::bridge=rex::Bridge{};
    target::bounds=target::Bounds{};target::bounds_refresh_ms.clear();u10=U10Trace{};
    data_info=nullptr;data_d=nullptr;data_s=nullptr;size_s=nullptr;id_list=nullptr;
    node_list=nullptr;max_node_num=nullptr;qid_list=nullptr;empty_list=nullptr;update_list=nullptr;
    qresult_count=qresult_count_prefix=result_id=nullptr;result_dis=nullptr;res=nullptr;res_dis=nullptr;
    time_update_s=time_update_u=0;count_update_s=count_update_u=0;tree_h=0;qnum_leaf=500;
    tree_size=in_size=0;
}
static void execute_state(const uk::Input& input,const std::string& output,bool warm,double context_ms,
                          int setup_delay,int trace_delay,int write_delay,size_t& restored_bytes) {
    reset_service();if(warm)u10.observe=true;
    std::cout<<"TARGET_PHASE "<<(warm?"warmup":"measured")<<'\n';std::cout.flush();
    rex::bridge.context_ms=context_ms;
    auto setup_begin=U10Clock::now();auto start=setup_begin;
    u10_ck(cudaMallocManaged((void**)&data_info,3*sizeof(int)));data_info[0]=input.d;data_info[1]=input.n;data_info[2]=2;
    u10_ck(cudaMallocManaged((void**)&data_d,input.data.size()*sizeof(float)));
    u10_ck(cudaMemcpy(data_d,input.data.data(),input.data.size()*sizeof(float),cudaMemcpyHostToDevice));
    if(!warm&&u10_env("TARGET_RESTORE_AUDIT")) {
        std::vector<float> copy(input.data.size());
        u10_ck(cudaMemcpy(copy.data(),data_d,copy.size()*sizeof(float),cudaMemcpyDeviceToHost));
        uk::require(!std::memcmp(copy.data(),input.data.data(),copy.size()*sizeof(float)),"restored initial FP32 bytes differ");
        restored_bytes=copy.size()*sizeof(float);
    }
    update_num=int(input.events.size());u10_ck(cudaMallocManaged((void**)&update_list,update_num*sizeof(UO)));
    for(int i=0;i<update_num;i++){update_list[i].update_flag=input.events[i].first;update_list[i].update_id=input.events[i].second;}
    u10_ck(cudaDeviceSynchronize());u10.load_ms=u10_ms(start);u10.initialize(input.n,input.queries,update_num);
    start=U10Clock::now();nvtxRangePushA("native.cold_build");MAX_H=uk::tree_height(input.n);
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
    u10_ck(cudaDeviceSynchronize());nvtxRangePop();u10.cold_build_ms=u10_ms(start);
    target::refresh_bounds(data_d,node_list,empty_list,id_list,max_node_num[0],data_info[1],data_info[0]);
    rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);
    uk::live.initialize(data_d,data_info[1],data_info[0],k,input.capacity);
    uk::require(target::bounds.epoch==1&&target::bounds.refreshes==1&&uk::live.refreshes==1&&
                target::bounds.n==input.n&&uk::live.n==input.n&&
                rex::bridge.refreshes==(rex::bridge.mode?1:0),"initial service not restored");
    pause_ms(setup_delay);rex::bridge.setup_ms=u10_ms(setup_begin);
    u10.begin();
    updateIndexRnn(data_d,node_list,id_list,max_node_num,qid_list,1,r,tree_h,data_info,empty_list,
                   qresult_count,qresult_count_prefix,result_id,result_dis,data_s,size_s,nullptr,
                   time_update_s,time_update_u,count_update_s,count_update_u);
    pause_ms(trace_delay);
    start=U10Clock::now();uk::live.finish();rex::bridge.finish();target::release_bounds();
    for(void* p:{(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s,(void*)id_list,
                (void*)node_list,(void*)max_node_num,(void*)qid_list,(void*)empty_list,
                (void*)update_list,(void*)res,(void*)res_dis})u10_ck(cudaFree(p));
    u10_ck(cudaDeviceSynchronize());u10.drain_ms=u10_ms(start);u10.finish();
    uk::require(!uk::live.owned_bytes&&!rex::bridge.owned_bytes&&!target::bounds.bytes,"final service release incomplete");
    pause_ms(write_delay);
    u10.write(output);rex::bridge.write(output);uk::live.write(output);target::write_bounds(output);
}
int main(int argc,char** argv) try {
    if(argc!=7||std::string(argv[3])!="2")throw std::runtime_error("DATA EVENTS 2 RADIUS OUTPUT K");
    size_t consumed=0;r=std::stof(argv[4],&consumed);uk::require(consumed==std::string(argv[4]).size(),"radius token");
    k=std::stoi(argv[6],&consumed);uk::require(consumed==std::string(argv[6]).size(),"K token");
    const char* km=std::getenv("KNN_MODE");uk::require(!km||std::string(km)=="BOUND"||std::string(km)=="FULL","unknown kNN mode");
    uk::require(rex::bridge.mode==0||rex::bridge.mode==1,"unified range dispatch");
    int setup_delay=diagnostic_delay("TARGET_SETUP_DELAY_MS"),trace_delay=diagnostic_delay("TARGET_TRACE_DELAY_MS");
    int write_delay=diagnostic_delay("TARGET_WRITE_DELAY_MS");
    auto parse_begin=U10Clock::now();auto input=uk::parse(argv[1],argv[2],k,r);double parse_ms=u10_ms(parse_begin);
    uk::require(input.n>=255,"phase B registered minimum shape");
    auto context_begin=U10Clock::now();u10_ck(cudaFree(nullptr));double context_ms=u10_ms(context_begin);
    const char* warm_env=std::getenv("TARGET_WARMUP");
    uk::require(!warm_env||std::string(warm_env)=="0"||std::string(warm_env)=="1","warmup flag");
    bool warmup=!warm_env||u10_env("TARGET_WARMUP");double warm_ms=0,warm_trace_ms=0;size_t restored_bytes=0;
    if(warmup) {
        auto start=U10Clock::now();
        {auto clone=input;clone.events={{2,0},{3,0},{0,0},{2,0},{3,0},{1,0},{2,0},{3,0}};
        for(int i=0;i<9;i++)clone.events.emplace_back(0,0);clone.events.emplace_back(2,0);clone.events.emplace_back(3,0);
        clone.queries=8;clone.capacity=std::max(input.capacity,(input.n+10+31)/32*32);
        execute_state(clone,std::string(argv[5])+".warmup",true,context_ms,0,0,0,restored_bytes);
        uk::require(target::bounds.refreshes==2&&uk::live.refreshes==2&&tree_size==input.n+9&&in_size==0,"warmup did not exercise real rebuild");
        warm_trace_ms=u10.trace_ms;}
        warm_ms=u10_ms(start);
    }
    execute_state(input,argv[5],false,context_ms,setup_delay,trace_delay,write_delay,restored_bytes);
    std::ofstream scope(std::string(argv[5])+".scope.json");scope<<std::setprecision(17)
      <<"{\"warmup\":"<<(warmup?"true":"false")<<",\"warmup_events\":"<<(warmup?19:0)
      <<",\"warmup_queries\":"<<(warmup?8:0)<<",\"warmup_rebuilds\":"<<(warmup?1:0)
      <<",\"warmup_total_ms\":"<<warm_ms<<",\"warmup_trace_ms\":"<<warm_trace_ms
      <<",\"parse_ms\":"<<parse_ms<<",\"context_ms\":"<<context_ms
      <<",\"initial_n\":"<<input.n<<",\"initial_d\":"<<input.d<<",\"initial_epoch\":1"
      <<",\"restored_device_bytes_checked\":"<<restored_bytes<<",\"setup_delay_ms\":"<<setup_delay
      <<",\"trace_delay_ms\":"<<trace_delay<<",\"write_delay_ms\":"<<write_delay<<"}\n";
    uk::require(bool(scope),"write measured scope");scope.close();
    // Release context-owned managed symbols after serialization; not a physical-GPU reset.
    u10_ck(cudaDeviceReset());return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
