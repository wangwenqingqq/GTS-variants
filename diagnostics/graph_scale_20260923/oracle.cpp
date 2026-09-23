// Independent CPU full-table integer edit distance, not GPU pruning code.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
int main(int argc,char** argv) {
    assert(argc==4);std::ifstream f(argv[1]),q(argv[2]);assert(f&&q);std::string line;
    std::getline(f,line);int width,n,metric;std::istringstream(line)>>width>>n>>metric;assert(metric==6);
    std::vector<std::string> data;while(std::getline(f,line)){assert(line.size()<109);data.push_back(line);}assert(data.size()==size_t(n));
    int count;q>>count;std::vector<int> qs(count);for(int& x:qs){q>>x;assert(x>=0&&x<n);}assert(q.good());
    std::ofstream out(argv[3],std::ios::binary);assert(out);int table[109][109];std::vector<uint8_t> distances(n);
    for(int id:qs) {
        const auto& a=data[id];for(size_t i=0;i<=a.size();++i)table[i][0]=i;
        for(int k=0;k<n;++k) {
            const auto& b=data[k];for(size_t j=0;j<=b.size();++j)table[0][j]=j;
            for(size_t i=1;i<=a.size();++i)for(size_t j=1;j<=b.size();++j)
                table[i][j]=std::min({table[i-1][j]+1,table[i][j-1]+1,table[i-1][j-1]+(a[i-1]!=b[j-1])});
            distances[k]=table[a.size()][b.size()];
        }
        out.write(reinterpret_cast<char*>(distances.data()),n);assert(out);std::cout<<id<<" complete\n"<<std::flush;
    }
}
