// One diagnostic-only SCAN_MATCHED reference; ordered-FP64 kernel bodies unchanged.
#include MATCHED_SUPPORT
int main(int argc,char** argv)try {
    uk::require(argc==4,"DATA QIDS OUTPUT");bt::configure();uk::require(bt::tiled,"TILED");
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);uk::require(bool(f)&&h[0]==960&&h[1]==1000000&&h[2]==2,"shape");
    std::vector<float> input(size_t(h[0])*h[1]);f.read((char*)input.data(),input.size()*4);uk::require(bool(f)&&f.peek()==EOF,"length");
    std::ifstream qf(argv[2]);std::vector<int> qids;int q;while(qf>>q){uk::require(q>=0&&q<h[1],"qid");qids.push_back(q);}uk::require(qids.size()==32,"queries");
    std::string out=argv[3];uk::require(std::filesystem::create_directory(out),"fresh output");
    u10_ck(cudaFree(nullptr));pv::Probe p(h[1],h[0],0.705625057220459f,out);auto t=U10Clock::now();p.setup(input);double tree=u10_ms(t);
    t=U10Clock::now();uk::live.initialize(data_d,p.n,p.d,8,(p.n+31)/32*32);u10_ck(cudaMemset(uk::live.mask,1,p.n));u10_ck(cudaDeviceSynchronize());double layout=u10_ms(t);
    for(int i=0;i<8;i++)p.rows.push_back({-1,3,i,qids[i],p.query(3,i,qids[i],false)});
    for(int i=0;i<32;i++)p.rows.push_back({0,3,i,qids[i],p.query(3,i,qids[i],false)});
    p.finish();p.save();std::ofstream meta(out+"/META.json");meta<<std::setprecision(17)<<"{\"diagnostic_only\":true,\"N\":1000000,\"D\":960,\"tree_setup_ms\":"<<tree<<",\"packed_setup_ms\":"<<layout<<"}\n";uk::require(bool(meta),"meta");return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
