// CPU-only planning diagnostics. No CUDA APIs, vector payloads, or service ACK.
#include "generic.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <set>
#include <string>
using Clock=std::chrono::steady_clock;
static int64_t elapsed(Clock::time_point a,Clock::time_point b){
    return std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count();
}
static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
struct Result {int count=0,levels=0;int64_t build=0,release=0;uint64_t signature=0;};
static uint64_t signature(std::vector<RowMove> values){
    std::sort(values.begin(),values.end(),[](auto a,auto b){return a.dst<b.dst;});
    uint64_t h=1469598103934665603ULL;
    for(auto m:values)for(uint32_t x:{uint32_t(m.src),uint32_t(m.dst)}){
        for(int j=0;j<4;j++){h^=(x>>(8*j))&255;h*=1099511628211ULL;}
    }
    return h;
}
static Result plan(const std::vector<RowMove>& commands,int n,int b,int variant){
    Result r;Clock::time_point destroy;
    auto begin=Clock::now();
    {
        std::unique_ptr<BatchPlan> tp;
        std::vector<RowMove> final,sorted;
        std::vector<int> offsets;
        if(variant==0){
            tp=std::make_unique<BatchPlan>(n,b,false);
            for(auto m:commands)tp->push(m.src,m.dst);
            tp->finish(true);
            r.levels=tp->levels.empty()?0:*std::max_element(tp->levels.begin(),tp->levels.end())+1;
            offsets.assign(r.levels+1,0);
            for(int l:tp->levels)++offsets[l+1];
            for(int l=0;l<r.levels;l++)offsets[l+1]+=offsets[l];
            auto cursor=offsets;sorted.resize(commands.size());
            for(size_t i=0;i<commands.size();i++)sorted[cursor[tp->levels[i]]++]=commands[i];
            r.count=int(sorted.size());
        }else{
            final=generic_compile(commands);
            std::set<int> destinations;
            for(auto m:final)require(m.src>=0&&m.src<n&&m.dst>=0&&m.dst<n&&destinations.insert(m.dst).second,"final destination");
            for(auto m:final)require(!destinations.count(m.src),"nonalias certificate");
            r.count=int(final.size());r.levels=!final.empty();
        }
        auto built=Clock::now();r.build=elapsed(begin,built);
        // Exclude the validation/signature copy and sorting from both intervals.
        r.signature=signature(variant==0?sorted:final);
        destroy=Clock::now();
    }
    r.release=elapsed(destroy,Clock::now());return r;
}
template<class T>static T read(std::ifstream& f){T x;f.read(reinterpret_cast<char*>(&x),sizeof(x));require(bool(f),"truncated input");return x;}
int main(int argc,char** argv){
    try{
        require(argc==4,"usage: cpu_cost cases.bin round new.csv");
        uint32_t little=1;require(*reinterpret_cast<char*>(&little)==1,"little endian required");
        require(!std::filesystem::exists(argv[3]),"output must be new");
        int round=std::stoi(argv[2]);require(round>=0&&round<6,"registered round");
        std::ifstream f(argv[1],std::ios::binary);char magic[8];f.read(magic,8);
        require(std::string(magic,8)=="GTSTRC1\n","input magic");uint32_t count=read<uint32_t>(f);
        require(count<10000,"bounded case count");
        std::ofstream out(argv[3]);out<<"case,request_step,rows,M,variant,F,levels,build_ns,release_ns,total_ns,signature\n";
        for(uint32_t i=0;i<count;i++){
            int step=read<int32_t>(f),n=read<int32_t>(f),b=read<int32_t>(f),moves=read<int32_t>(f);
            require(step>0&&b>0&&b<=512&&n>=b&&n<=1000000&&moves>=0&&moves<=b,"case envelope");
            std::vector<RowMove> commands;commands.reserve(moves);
            for(int j=0;j<moves;j++){
                int src=read<int32_t>(f),dst=read<int32_t>(f);
                require(src>=n-b&&src<n&&dst>=0&&dst<src&&(commands.empty()||src<commands.back().src),"command geometry");
                commands.push_back({src,dst});
            }
            Result results[2];
            for(int order=0;order<2;order++){
                int variant=(round+order)%2;auto r=plan(commands,n,b,variant);results[variant]=r;
                out<<i<<','<<step<<','<<b<<','<<moves<<','<<(variant==0?"GENERIC_WAVES":"GENERIC_DSE")<<','
                   <<r.count<<','<<r.levels<<','<<r.build<<','<<r.release<<','<<r.build+r.release<<','<<r.signature<<'\n';
            }
            // Registered benchmark cases have no conflicts/elimination. Reject
            // anything else rather than assuming this comparator is general.
            require(results[0].levels<=1&&results[0].count==results[1].count&&results[0].signature==results[1].signature,"registered no-dependence control");
        }
        require(f.peek()==std::char_traits<char>::eof()&&bool(out),"trailing input or write failure");
        std::cout<<"CPU_COST_PASS "<<count<<" batches;GPU starts 0\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
