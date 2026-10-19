// CPU-only finite-chain sharing diagnostic. No CUDA or vector-search timing.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <queue>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using State = uint64_t;
using Action = std::pair<int,int>; // Physical zone and query-consumer mask.
using Path = std::vector<Action>;
struct Problem {
    int b, z;
    std::array<std::array<int,30>,8> order{}, position{};
    std::array<int,8> length{};
    std::array<std::array<uint32_t,31>,8> suffix{};
    int pair_lcs[8][8][31][31]{};
    int at(State s,int q) const {return int((s>>(5*q))&31);}
    uint32_t ready(State s) const {
        uint32_t mask=0;
        for(int q=0;q<b;++q) if(at(s,q)<length[q]) mask|=1u<<order[q][at(s,q)];
        return mask;
    }
    Action consumers(State s,int tile) const {
        int mask=0;
        for(int q=0;q<b;++q) if(at(s,q)<length[q] && order[q][at(s,q)]==tile) mask|=1<<q;
        return {tile,mask};
    }
    State step(State s,Action a) const {
        if(!a.second || a.second&~consumers(s,a.first).second) throw std::runtime_error("Illegal shared action");
        for(int q=0;q<b;++q) if(a.second&(1<<q)) s+=State(1)<<(5*q);
        return s;
    }
    int remaining_union(State s) const {
        uint32_t mask=0;
        for(int q=0;q<b;++q) mask|=suffix[q][at(s,q)];
        return __builtin_popcount(mask);
    }
    void set_lengths(State key) {
        if(key>>(5*b)) throw std::runtime_error("Invalid context bits");
        for(int q=0;q<b;++q) {
            length[q]=at(key,q);
            if(length[q]>z) throw std::runtime_error("Invalid chain length");
            suffix[q].fill(0);
            for(int k=length[q]-1;k>=0;--k) suffix[q][k]=suffix[q][k+1]|(1u<<order[q][k]);
        }
    }
    int lower() const {
        int lb=remaining_union(0);
        for(int q=0;q<b;++q) for(int r=q+1;r<b;++r)
            lb=std::max(lb,length[q]+length[r]-pair_lcs[q][r][length[q]][length[r]]);
        return lb;
    }
    void verify(const Path& path,bool serve_all) const {
        State s=0;
        for(auto a:path) {
            if(a.first<0 || a.first>=z || (serve_all && a!=consumers(s,a.first))) throw std::runtime_error("Invalid witness");
            s=step(s,a);
        }
        if(ready(s)) throw std::runtime_error("Incomplete witness");
    }
    Path greedy(bool lookahead) const {
        State s=0; Path path;
        while(uint32_t mask=ready(s)) {
            int best=-1,fan=-1,look=-1;
            for(int t=0;t<z;++t) if(mask&(1u<<t)) {
                int f=__builtin_popcount(unsigned(consumers(s,t).second)),l=0;
                // Use known request orders, never future rejection depths.
                if(lookahead) for(int q=0;q<b;++q) if(at(s,q)<length[q] && position[q][t]>=at(s,q))
                    l+=z-(position[q][t]-at(s,q));
                if(f>fan || (f==fan && l>look)) {best=t;fan=f;look=l;}
            }
            auto a=consumers(s,best);path.push_back(a);s=step(s,a);
        }
        verify(path,true);return path;
    }
    Path trie() const {
        Path path;
        std::function<void(State,int)> walk=[&](State s,int group) {
            std::map<int,int> children;
            for(int q=0;q<b;++q) if((group&(1<<q)) && at(s,q)<length[q]) children[order[q][at(s,q)]]|=1<<q;
            for(auto [tile,mask]:children) {Action a{tile,mask};path.push_back(a);walk(step(s,a),mask);}
        };
        walk(0,(1<<b)-1);verify(path,false);return path;
    }
};

struct Answer {int lb,ub,expanded;Path path;};
Answer oracle(const Problem& p,Path upper,int cap) {
    int initial=p.lower(),ub=int(upper.size()),expanded=0;
    if(initial>ub) throw std::runtime_error("Lower bound exceeds witness");
    if(initial==ub || !cap) return {initial,ub,0,upper};
    struct Node {int f,g;State s;};
    struct Compare {bool operator()(Node a,Node b) const {
        if(a.f!=b.f)return a.f>b.f;
        if(a.g!=b.g)return a.g<b.g;
        return a.s>b.s;
    }};
    struct Parent {State previous;Action action;};
    std::priority_queue<Node,std::vector<Node>,Compare> open;
    std::unordered_map<State,int> distance;
    std::unordered_map<State,Parent> parent;
    open.push({initial,0,0});distance[0]=0;
    while(!open.empty()) {
        auto n=open.top();open.pop();
        if(distance.at(n.s)!=n.g)continue;
        if(n.f>=ub)return {ub,ub,expanded,upper};
        if(expanded==cap)return {std::max(initial,n.f),ub,expanded,upper};
        if(!p.ready(n.s)) {
            Path result;
            for(State s=n.s;s;) {auto a=parent.at(s);result.push_back(a.action);s=a.previous;}
            std::reverse(result.begin(),result.end());p.verify(result,true);
            if(int(result.size())!=n.g)throw std::runtime_error("Witness length mismatch");
            return {n.g,n.g,expanded,result};
        }
        ++expanded;
        uint32_t choices=p.ready(n.s);
        for(int t=0;t<p.z;++t)if(choices&(1u<<t)) {
            auto a=p.consumers(n.s,t);State s=p.step(n.s,a);int g=n.g+1;
            int f=std::max(initial,g+p.remaining_union(s));
            if(f>=ub)continue;
            auto old=distance.find(s);
            if(old!=distance.end() && old->second<=g)continue;
            distance[s]=g;parent[s]={n.s,a};open.push({f,g,s});
        }
    }
    return {ub,ub,expanded,upper};
}

template<class T>T read(std::istream& f) {
    T x{};f.read(reinterpret_cast<char*>(&x),sizeof(x));
    if(!f)throw std::runtime_error("Truncated input");
    return x;
}
std::string encode(const Path& p) {
    std::ostringstream s;s<<std::hex<<std::setfill('0');
    for(auto [tile,mask]:p)s<<std::setw(2)<<tile<<std::setw(2)<<mask;
    return s.str();
}
int main(int argc,char** argv) {
    try {
        if(argc!=5)throw std::runtime_error("usage: solver INPUT OUTPUT CASE_CAP BATCH_CAP");
        uint16_t endian=1;if(*reinterpret_cast<uint8_t*>(&endian)!=1)throw std::runtime_error("Little endian required");
        int case_cap=std::stoi(argv[3]),budget=std::stoi(argv[4]);
        if(case_cap<0 || budget<0)throw std::runtime_error("Negative budget");
        std::ifstream in(argv[1],std::ios::binary);char magic[8];in.read(magic,8);
        if(std::string(magic,8)!="BQSI001\n")throw std::runtime_error("Bad magic");
        Problem p{};p.b=int(read<uint32_t>(in));p.z=int(read<uint32_t>(in));uint32_t cases=read<uint32_t>(in);
        if(p.b<1 || p.b>8 || p.z<1 || p.z>30 || !cases)throw std::runtime_error("Bad shape");
        for(int q=0;q<p.b;++q) {
            uint32_t seen=0;
            for(int k=0;k<p.z;++k) {int t=read<uint8_t>(in);if(t>=p.z || (seen&(1u<<t)))throw std::runtime_error("Bad permutation");seen|=1u<<t;p.order[q][k]=t;p.position[q][t]=k;}
        }
        for(int q=0;q<p.b;++q)for(int r=q+1;r<p.b;++r)for(int i=1;i<=p.z;++i)for(int j=1;j<=p.z;++j)
            p.pair_lcs[q][r][i][j]=p.order[q][i-1]==p.order[r][j-1]?p.pair_lcs[q][r][i-1][j-1]+1:std::max(p.pair_lcs[q][r][i-1][j],p.pair_lcs[q][r][i][j-1]);
        if(std::ifstream(argv[2]).good())throw std::runtime_error("Output already exists");
        std::ofstream out(argv[2]);if(!out)throw std::runtime_error("Cannot create output");
        out<<"key,frequency,independent,trie,fanout,lookahead,lower,upper,expanded,witness\n";
        State previous=0;uint64_t total=0;int expanded=0;
        for(uint32_t c=0;c<cases;++c) {
            State key=read<uint64_t>(in);uint32_t freq=read<uint32_t>(in);
            if(!freq || (c && key<=previous))throw std::runtime_error("Bad context ordering/count");
            previous=key;p.set_lengths(key);
            auto trie=p.trie(),fan=p.greedy(false),look=p.greedy(true);
            // Serving extra ready consumers is weakly dominant for read count.
            // The trie is counted, but the A* upper witness must serve all ready consumers.
            Path eager;State cursor=0;
            for(auto a:trie) if(auto all=p.consumers(cursor,a.first);all.second) {
                eager.push_back(all);cursor=p.step(cursor,all);
            }
            p.verify(eager,true);
            Path upper=fan.size()<=look.size()?fan:look;
            if(eager.size()<upper.size())upper=eager;
            auto answer=oracle(p,upper,std::min(case_cap,budget));
            p.verify(answer.path,true);budget-=answer.expanded;expanded+=answer.expanded;
            int independent=0;for(int q=0;q<p.b;++q)independent+=p.length[q];
            if(answer.lb>answer.ub || answer.ub>int(std::min({fan.size(),look.size(),trie.size()})) || answer.lb<0 || int(answer.path.size())!=answer.ub)throw std::runtime_error("Bad oracle interval");
            out<<key<<','<<freq<<','<<independent<<','<<trie.size()<<','<<fan.size()<<','<<look.size()<<','<<answer.lb<<','<<answer.ub<<','<<answer.expanded<<','<<encode(answer.path)<<'\n';
            total+=freq;
        }
        if(in.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Trailing input");
        out.close();if(!out)throw std::runtime_error("Write failed");
        std::cout<<"SHARING_PASS contexts="<<cases<<" sectors="<<total<<" expansions="<<expanded<<" GPU_starts=0\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
