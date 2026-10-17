// Full-capacity arbitrary-bit tests use the actual Store/executor,not a test clone.
static void bitcheck(){
    int cases=0;
    for(int n:{65,513})for(int b:{1,7,32,65,511,512})for(int shape=0;shape<3;shape++){
        int count=std::min(n,b);std::vector<float> x(size_t(n)*960),got(x.size());uint32_t seed=2026101704;
        for(float& value:x){seed=1664525u*seed+1013904223u;std::memcpy(&value,&seed,4);}
        uint32_t nan=0x7fc01234u;for(int r=0;r<3;r++)for(int j=0;j<960;j++)std::memcpy(&x[size_t(r)*960+j],&nan,4);
        auto expected=x;std::vector<int> owner(n),pos(n),ids;std::iota(owner.begin(),owner.end(),0);pos=owner;
        if(shape==2){ids.push_back(0);for(int i=1;i<count;i++)ids.push_back(n-i);}
        else{ids=owner;if(shape==1){std::mt19937 rng(2026101705);std::shuffle(ids.begin(),ids.end(),rng);}ids.resize(count);}
        for(int id:ids){int row=pos[id],last=int(owner.size())-1;if(row!=last){std::memcpy(expected.data()+size_t(row)*960,expected.data()+size_t(last)*960,3840);int moved=owner.back();owner[row]=moved;pos[moved]=row;}owner.pop_back();pos[id]=-1;}
        // The search API admits finite inputs only;inject arbitrary bits directly
        // after a valid build to test the unchanged row-copy primitive separately.
        Store s;std::vector<float> finite(x.size(),0.f);s.build(finite,n,count);
        ck(cudaMemcpyAsync(s.p.database,x.data(),x.size()*4,cudaMemcpyHostToDevice,s.p.stream));ck(cudaStreamSynchronize(s.p.stream));
        s.erase(ids);require(s.occurrence==owner,"bitcheck owner");
        ck(cudaMemcpyAsync(got.data(),s.p.database,got.size()*4,cudaMemcpyDeviceToHost,s.p.stream));ck(cudaStreamSynchronize(s.p.stream));
        require(std::memcmp(got.data(),expected.data(),got.size()*4)==0,"bitcheck full allocated bytes,NaNs,duplicates and retired rows");s.release();++cases;
    }
    std::vector<float> x(513*960,0);Store s;s.build(x,513,2048);int rejected=0;
    for(auto ids:{std::vector<int>{},std::vector<int>{0,0},std::vector<int>{-1},std::vector<int>{513},std::vector<int>(513,1)}){
        auto owners=s.occurrence;auto reverse=s.position;auto size=s.mutations.size();bool failed=false;try{s.erase(ids);}catch(const std::exception&){failed=true;}
        require(failed&&owners==s.occurrence&&reverse==s.position&&size==s.mutations.size(),"invalid delete atomicity");++rejected;
    }
    s.erase({0});auto owners=s.occurrence;bool failed=false;try{s.erase({0});}catch(const std::exception&){failed=true;}
    require(failed&&owners==s.occurrence,"repeat delete rejection");s.release();++rejected;
    std::cout<<"BITCHECK capacity_cases="<<cases<<" invalid_rejections="<<rejected<<"\n";
}
