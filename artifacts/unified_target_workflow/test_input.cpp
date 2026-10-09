#include "input.hpp"
#include <iostream>
#include <numeric>
#include <random>
#include <cassert>
int main(int argc,char** argv) try {
    std::mt19937 rng(20261009);
    for(int n:{1,255,256,257,1000,1023,1024,1025,4096,65536,1000000}){
        uk::RankTree t;t.reset(n);std::vector<int> rows(n);std::iota(rows.begin(),rows.end(),0);
        for(int j=0;j<std::min(n,2000);++j){int r=rng()%rows.size();assert(t.erase(r)==rows[r]);rows.erase(rows.begin()+r);assert(t.live==int(rows.size()));}
    }
    assert(uk::tree_height(1000)==3&&uk::tree_height(2010)==4&&uk::tree_height(1000000)==6);
    assert(uk::data_bytes(1000000,960)==3840000000ULL);
    assert(size_t((1000000+255)/256)*8==31256);
    bool rejected=false;try{uk::checked_product(SIZE_MAX,2);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
    if(argc==4){auto x=uk::parse(argv[1],argv[2],8,std::stof(argv[3]));
        assert(x.capacity%32==0&&x.capacity>=x.n);std::cout<<x.n<<' '<<x.d<<' '<<x.capacity<<' '<<x.queries<<'\n';}
    std::cout<<"PASS rank mapping, checked bytes and scratch geometry\n";
}
catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}
