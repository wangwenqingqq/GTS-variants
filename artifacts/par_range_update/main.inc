
int main(int argc,char** argv) try {
    if(argc!=6 || std::string(argv[3])!="2")throw std::runtime_error("native timed arguments");
    auto context_begin=U10Clock::now();u10_ck(cudaFree(nullptr));rex::bridge.context_ms=u10_ms(context_begin);auto setup_begin=U10Clock::now();auto start=setup_begin;
    load(argv[1],data_info,data_d,data_s,size_s);
    loadUpdate(argv[2],update_list,update_num);
    r=std::stof(argv[4]);int queries=0;
    for(int i=0;i<update_num;++i)queries+=update_list[i].update_flag==2;
    u10_ck(cudaDeviceSynchronize());u10.load_ms=u10_ms(start);
    u10.initialize(data_info[1],queries,update_num);
    start=U10Clock::now();nvtxRangePushA("native.cold_build");
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
    u10_ck(cudaDeviceSynchronize());nvtxRangePop();u10.cold_build_ms=u10_ms(start);
    rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);
    rex::bridge.setup_ms=u10_ms(setup_begin);
    u10.begin();
    updateIndexRnn(data_d,node_list,id_list,max_node_num,qid_list,1,r,tree_h,data_info,empty_list,
                   qresult_count,qresult_count_prefix,result_id,result_dis,data_s,size_s,nullptr,
                   time_update_s,time_update_u,count_update_s,count_update_u);
    start=U10Clock::now();
    rex::bridge.finish();
    for(void* p:{(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s,(void*)id_list,
                (void*)node_list,(void*)max_node_num,(void*)qid_list,(void*)empty_list,
                (void*)update_list,(void*)res,(void*)res_dis})u10_ck(cudaFree(p));
    u10_ck(cudaDeviceSynchronize());u10.drain_ms=u10_ms(start);u10.finish();
    u10.write(argv[5]);rex::bridge.write(argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
