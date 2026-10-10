// Independent scalar exhaustive reference. Compile without FP reassociation/FMA.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
struct Key {double score;int id;};
static bool less(Key a,Key b){return a.score<b.score||(a.score==b.score&&a.id<b.id);}
int main(int argc,char** argv)try{
    require(argc==5,"oracle_cpu data qids K output.bin");int k=std::stoi(argv[3]);
    std::ifstream f(argv[1],std::ios::binary);int h[3];f.read((char*)h,12);require(bool(f),"header");
    int d=h[0],n=h[1];require(n>0&&d>0&&d<=960&&h[2]==2&&k>0&&k<=n,"contract");
    std::vector<float> data(size_t(n)*d);f.read((char*)data.data(),data.size()*4);require(bool(f),"payload");
    for(float x:data)require(std::isfinite(x)&&x>=0.f&&x<=2.f,"input envelope");
    std::ifstream qfile(argv[2]);int q;qfile>>q;require(bool(qfile)&&q>0,"queries");
    std::vector<int> outids(q*k);std::vector<double> scores(q*k);std::vector<Key> keys(n);
    for(int i=0;i<q;++i){int query;qfile>>query;require(bool(qfile)&&query>=0&&query<n,"query ID");
        for(int row=0;row<n;++row){double sum=0.;
            for(int j=0;j<d;++j){double delta=double(data[size_t(row)*d+j])-double(data[size_t(query)*d+j]);
                double square=delta*delta;sum=sum+square;}
            keys[row]={sum,row};}
        std::partial_sort(keys.begin(),keys.begin()+k,keys.end(),less);
        for(int j=0;j<k;++j){outids[i*k+j]=keys[j].id;scores[i*k+j]=keys[j].score;}
    }
    int extra;require(!(qfile>>extra),"extra queries");
    std::ofstream o(argv[4],std::ios::binary);int oh[4]={n,d,q,k};o.write((char*)oh,16);
    o.write((char*)outids.data(),outids.size()*4);o.write((char*)scores.data(),scores.size()*8);require(bool(o),"output");
    std::cout<<"PASS independent scalar exhaustive CPU reference for "<<q<<" queries; not tree/CUDA validation"<<std::endl;
}catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
