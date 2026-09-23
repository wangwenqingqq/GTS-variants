// Capacity-scaled common driver. K is a serial bundle, not parallel traversal.
int main(int argc,char** argv) {
    assert(argc==9);
    std::string mode=argv[3],out=argv[7];float radius=std::stof(argv[4]);
    int repeats=std::stoi(argv[5]),warmup=std::stoi(argv[6]);bool dump=std::stoi(argv[8]);
    int bundle=getenv("GTS_BUNDLE")?atoi(getenv("GTS_BUNDLE")):1;
    assert((mode=="A"||mode=="B"||mode=="C") && repeats>0 && warmup>=0 && (bundle==1||bundle==8||bundle==32));
    auto process_start=Clock::now();load(argv[1],data_info,data_d,data_s,size_s);ck(cudaGetLastError());
    int n=data_info[1];assert((n==2000||n==20000||n==100000||n==611756)&&data_info[2]==6);
    // The last child receives the integer-division remainder at every split.
    MAX_H=1;for(int worst=n;worst>MAX_SIZE;worst=worst-9*(worst/10))++MAX_H;
    std::ifstream qf(argv[2]);int nq=0;qf>>nq;assert(nq>0 && nq%bundle==0 && warmup%bundle==0);
    std::vector<int> queries(nq);for(int& q:queries){qf>>q;assert(q>=0&&q<n);}assert(qf.good());
    auto build=Clock::now();indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);ck(cudaDeviceSynchronize());
    double build_s=seconds(build);int nodes=*max_node_num,slots=nodes*MAX_SIZE;
    std::vector<TN> tree(nodes);std::vector<int> empty(nodes),permutation(n);
    ck(cudaMemcpy(tree.data(),node_list,nodes*sizeof(TN),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(empty.data(),empty_list,nodes*sizeof(int),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(permutation.data(),id_list,n*sizeof(int),cudaMemcpyDeviceToHost));
    std::sort(permutation.begin(),permutation.end());for(int i=0;i<n;++i)assert(permutation[i]==i);
    std::vector<std::pair<int,int>> leaves;int maxleaf=0;
    for(int i=0;i<nodes;++i)if(!empty[i]) {
        auto t=tree[i];assert(t.size>0&&t.lid>=0&&t.lid+t.size<=n);
        if(t.is_leaf){assert(t.size<=MAX_SIZE);leaves.emplace_back(t.lid,t.size);maxleaf=std::max(maxleaf,t.size);}
        else assert(i*10+1<nodes);
    }
    std::sort(leaves.begin(),leaves.end());int end=0;
    for(auto [offset,size]:leaves){assert(offset==end);end+=size;}assert(end==n);
    std::ofstream shape(out+".shape.json");shape<<"{\"n\":"<<n<<",\"height\":"<<tree_h<<",\"nodes\":"<<nodes
      <<",\"slots\":"<<slots<<",\"leaves\":"<<leaves.size()<<",\"max_leaf_size\":"<<maxleaf<<",\"bundle\":"<<bundle
      <<",\"output_copy_bytes_per_query\":"<<4+size_t(slots)*8<<",\"host_staging_bytes\":"<<size_t(bundle)*(8+size_t(slots)*8)<<"}\n";shape.close();
    tree_size=n;ck(cudaMallocManaged(&is_delete,n*sizeof(int)));ck(cudaMallocManaged(&is_delete_prefix,n*sizeof(int)));
    ck(cudaMemset(is_delete,0,n*sizeof(int)));ck(cudaMallocManaged(&qid_list,sizeof(int)));ck(cudaDeviceSynchronize());
    std::vector<std::vector<int>> ai;std::vector<std::vector<float>> ad;std::vector<int> ac(bundle);
    if(mode=="A"){ai.assign(bundle,std::vector<int>(slots));ad.assign(bundle,std::vector<float>(slots));}
    auto setup=Clock::now();Fixed* fixed=mode=="A"?nullptr:new Fixed(n,tree_h,bundle);double capture_s=0;
    if(mode=="C"){std::copy(queries.begin(),queries.begin()+bundle,fixed->hq);capture_s=fixed->capture(radius);}
    double setup_s=seconds(setup);
    auto call=[&](const int* qs){if(fixed)fixed->query(qs,radius,mode=="C");
        else for(int j=0;j<bundle;++j)original_query(qs[j],radius,ac[j],ai[j],ad[j]);};
    auto first=Clock::now();call(queries.data());double first_s=seconds(first);
    for(int i=0;i<warmup;i+=bundle)call(queries.data()+i%nq);
    std::ofstream full;if(dump)full.open(out+".results");
    std::vector<double> us;std::vector<int> counts;std::vector<uint64_t> hashes;
    us.reserve(nq*repeats);counts.reserve(nq*repeats);hashes.reserve(nq*repeats);
    double cpu_start=cpu_time();auto loop=Clock::now();
    for(int rep=0;rep<repeats;++rep)for(int i=0;i<nq;i+=bundle) {
        auto t=Clock::now();call(queries.data()+i);double batch_us=seconds(t)*1e6;
        for(int j=0;j<bundle;++j) {
            const int* ids=fixed?fixed->hi+size_t(j)*slots:ai[j].data();
            const float* ds=fixed?fixed->hd+size_t(j)*slots:ad[j].data();int count=fixed?fixed->hc[j]:ac[j];
            us.push_back(batch_us/bundle);counts.push_back(count);hashes.push_back(digest(count,ids,ds));
            if(dump){full<<queries[i+j]<<' '<<count;for(int k=0;k<count;++k)full<<' '<<ids[k]<<':'<<ds[k];full<<'\n';}
        }
    }
    double loop_s=seconds(loop),cpu_s=cpu_time()-cpu_start;
    std::ofstream samples(out+".csv");samples<<"qid,query_us,count,ordered_hash\n"<<std::setprecision(12);
    for(size_t i=0;i<us.size();++i)samples<<queries[i%nq]<<','<<us[i]<<','<<counts[i]<<','<<hashes[i]<<'\n';
    std::ofstream summary(out+".json");summary<<std::setprecision(12)
      <<"{\"mode\":\""<<mode<<"\",\"queries\":"<<us.size()<<",\"radius\":"<<radius<<",\"n\":"<<n<<",\"bundle\":"<<bundle
      <<",\"build_s\":"<<build_s<<",\"setup_s\":"<<setup_s<<",\"capture_instantiate_s\":"<<capture_s<<",\"first_bundle_s\":"<<first_s
      <<",\"sum_query_s\":"<<std::accumulate(us.begin(),us.end(),0.0)/1e6<<",\"loop_wall_s\":"<<loop_s
      <<",\"loop_cpu_s\":"<<cpu_s<<",\"before_cleanup_process_s\":"<<seconds(process_start)<<"}\n";
    delete fixed;ck(cudaFree(qid_list));ck(cudaFree(is_delete));ck(cudaFree(is_delete_prefix));
    for(void* p:{(void*)data_info,(void*)data_s,(void*)size_s,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)empty_list})ck(cudaFree(p));
    printf("PASS completed %s %zu queries, bundle %d\n",mode.c_str(),us.size(),bundle);
}
