// Independent CPU enumeration of the complete ordered range result.
#include <cmath>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <iostream>

int main(int argc,char** argv) {
    try {
        if(argc!=6)throw std::runtime_error("usage: small_oracle data idlist qids radii output");
        std::ifstream input(argv[1],std::ios::binary);
        int header[3];input.read(reinterpret_cast<char*>(header),12);
        const int d=header[0],n=header[1];
        if(!input||header[2]!=2||n<1||d<2)throw std::runtime_error("bad input");
        std::vector<float> data(size_t(n)*d);
        input.read(reinterpret_cast<char*>(data.data()),data.size()*4);
        if(!input||input.peek()!=EOF)throw std::runtime_error("bad data length");
        std::vector<int> order(n);
        std::ifstream idfile(argv[2],std::ios::binary);
        idfile.read(reinterpret_cast<char*>(order.data()),size_t(n)*4);
        if(!idfile||idfile.peek()!=EOF)throw std::runtime_error("bad idlist length");
        std::ifstream qfile(argv[3]);int b;qfile>>b;
        if(!qfile||b<1)throw std::runtime_error("bad queries");
        std::vector<int> qids(b);for(int& q:qids)if(!(qfile>>q)||q<0||q>=n)throw std::runtime_error("bad qid");
        std::ifstream rfile(argv[4],std::ios::binary);std::vector<float> radii(b);
        rfile.read(reinterpret_cast<char*>(radii.data()),size_t(b)*4);
        if(!rfile||rfile.peek()!=EOF)throw std::runtime_error("bad radii");
        std::ofstream output(argv[5],std::ios::binary);
        if(!output)throw std::runtime_error("bad output");
        long long total=0;
        for(int index=0;index<b;++index) {
            const int q=qids[index];const float radius=radii[index];
            if(!std::isfinite(radius))throw std::runtime_error("nonfinite radius");
            const double cutoff=double(radius)*double(radius);
            std::vector<int> ids;std::vector<float> distances;
            for(int pos=0;pos<n;++pos) {
                const int id=order[pos];double sum=0.0;
                if(radius<0)continue;
                for(int j=0;j<d;++j) {
                    const double delta=double(data[size_t(id)*d+j])-double(data[size_t(q)*d+j]);
                    sum=sum+delta*delta;
                }
                if(sum<=cutoff){ids.push_back(id);distances.push_back(float(std::sqrt(sum)));}
            }
            const int count=int(ids.size());total+=count;
            output.write(reinterpret_cast<const char*>(&q),4);
            output.write(reinterpret_cast<const char*>(&count),4);
            output.write(reinterpret_cast<const char*>(ids.data()),size_t(count)*4);
            output.write(reinterpret_cast<const char*>(distances.data()),size_t(count)*4);
        }
        std::cout<<"PASS CPU oracle queries="<<b<<" results="<<total<<'\n';
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
