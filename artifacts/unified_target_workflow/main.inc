int main(int argc,char** argv) try {
    if(argc!=7||std::string(argv[3])!="2")throw std::runtime_error("DATA EVENTS 2 RADIUS OUTPUT K");
    size_t consumed=0;r=std::stof(argv[4],&consumed);uk::require(consumed==std::string(argv[4]).size(),"radius token");
    k=std::stoi(argv[6],&consumed);uk::require(consumed==std::string(argv[6]).size(),"K token");
    // Parse, validate and retain the exact host input before any GPU allocation.
    const char* km=std::getenv("KNN_MODE");uk::require(!km||std::string(km)=="BOUND"||std::string(km)=="FULL","unknown kNN mode");
    uk::require(rex::bridge.mode==0||rex::bridge.mode==1,"unified range dispatch");
    auto input=uk::parse(argv[1],argv[2],k,r);
    auto context_begin=U10Clock::now();u10_ck(cudaFree(nullptr));rex::bridge.context_ms=u10_ms(context_begin);
    auto setup_begin=U10Clock::now();auto start=setup_begin;
    u10_ck(cudaMallocManaged((void**)&data_info,3*sizeof(int)));data_info[0]=input.d;data_info[1]=input.n;data_info[2]=2;
    u10_ck(cudaMallocManaged((void**)&data_d,input.data.size()*sizeof(float)));
    u10_ck(cudaMemcpy(data_d,input.data.data(),input.data.size()*sizeof(float),cudaMemcpyHostToDevice));
    update_num=int(input.events.size());u10_ck(cudaMallocManaged((void**)&update_list,update_num*sizeof(UO)));
    for(int i=0;i<update_num;i++){update_list[i].update_flag=input.events[i].first;update_list[i].update_id=input.events[i].second;}
    u10_ck(cudaDeviceSynchronize());u10.load_ms=u10_ms(start);u10.initialize(input.n,input.queries,update_num);
    start=U10Clock::now();nvtxRangePushA("native.cold_build");
    MAX_H=uk::tree_height(input.n);
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
    u10_ck(cudaDeviceSynchronize());nvtxRangePop();u10.cold_build_ms=u10_ms(start);
    target::refresh_bounds(data_d,node_list,empty_list,id_list,max_node_num[0],data_info[1],data_info[0]);
    rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);
    uk::live.initialize(data_d,data_info[1],data_info[0],k,input.capacity);rex::bridge.setup_ms=u10_ms(setup_begin);
    if(u10_env("TARGET_STALE"))target::bounds.base=nullptr;
    if(u10_env("PAR_STALE"))--rex::bridge.view.tree_epoch;
    if(u10_env("KNN_STALE"))--uk::live.published_epoch;
    u10.begin();
    updateIndexRnn(data_d,node_list,id_list,max_node_num,qid_list,1,r,tree_h,data_info,empty_list,
                   qresult_count,qresult_count_prefix,result_id,result_dis,data_s,size_s,nullptr,
                   time_update_s,time_update_u,count_update_s,count_update_u);
    start=U10Clock::now();uk::live.finish();rex::bridge.finish();target::release_bounds();
    for(void* p:{(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s,(void*)id_list,
                (void*)node_list,(void*)max_node_num,(void*)qid_list,(void*)empty_list,
                (void*)update_list,(void*)res,(void*)res_dis})u10_ck(cudaFree(p));
    u10_ck(cudaDeviceSynchronize());u10.drain_ms=u10_ms(start);u10.finish();
    u10.write(argv[5]);rex::bridge.write(argv[5]);uk::live.write(argv[5]);target::write_bounds(argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
