// Independent CPU rolling-row integer Levenshtein; no GPU/tree code.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>
int main(int argc,char** argv) {
    assert(argc==4);std::ifstream f(argv[1]);int width,n,metric;f>>width>>n>>metric;
    assert(metric==6);std::string line;std::getline(f,line);std::vector<std::string> data;
    while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();data.push_back(line);}
    assert(int(data.size())==n);std::ifstream qf(argv[2]);int nq;qf>>nq;std::vector<int> qs(nq);
    for(auto& q:qs){qf>>q;assert(q>=0&&q<n);}std::ofstream out(argv[3],std::ios::binary);
    for(int q:qs) {
        std::vector<uint8_t> row(n);const auto& a=data[q];
        for(int k=0;k<n;++k) {
            const auto& b=data[k];assert(a.size()<109&&b.size()<109);
            int prev[109],cur[109];std::iota(prev,prev+b.size()+1,0);
            for(size_t i=0;i<a.size();++i){cur[0]=i+1;for(size_t j=0;j<b.size();++j)
                cur[j+1]=std::min({prev[j+1]+1,cur[j]+1,prev[j]+int(a[i]!=b[j])});
                std::copy(cur,cur+b.size()+1,prev);}
            row[k]=uint8_t(prev[b.size()]);
        }
        out.write(reinterpret_cast<const char*>(row.data()),row.size());assert(out.good());
    }
    std::cout<<"PASS CPU oracle "<<nq<<" x "<<n<<" distances\n";
}
