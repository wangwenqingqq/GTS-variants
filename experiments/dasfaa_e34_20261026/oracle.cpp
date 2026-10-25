// Independent CPU oracle: exhaustive explicit FP64 differences, no GPU/library GT.
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <queue>
#include <vector>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
int main(int argc,char**argv){
 assert(argc==5);int n=atoi(argv[3]);int fd=open(argv[1],O_RDONLY);assert(fd>=0);struct stat st;fstat(fd,&st);auto raw=(char*)mmap(nullptr,st.st_size,PROT_READ,MAP_SHARED,fd,0);assert(raw!=MAP_FAILED);int d=((int*)raw)[1];auto x=(float*)(raw+8);
 std::ifstream f(argv[2],std::ios::binary);int nq,dq;f.read((char*)&nq,4);f.read((char*)&dq,4);assert(dq==d);std::vector<float>q(size_t(nq)*d);f.read((char*)q.data(),q.size()*4);assert(f);
 std::vector<int> ids(size_t(nq)*10);std::vector<double> ds(size_t(nq)*10);
 #pragma omp parallel for schedule(dynamic,1)
 for(int a=0;a<nq;a++){
   std::priority_queue<std::pair<double,int>> top;
   for(int i=0;i<n;i++){double sum=0;for(int j=0;j<d;j++){double v=double(x[size_t(i)*d+j])-double(q[size_t(a)*d+j]);sum+=v*v;}if(top.size()<10)top.emplace(sum,i);else if(sum<top.top().first){top.pop();top.emplace(sum,i);}}
   for(int k=9;k>=0;k--){ds[size_t(a)*10+k]=sqrt(top.top().first);ids[size_t(a)*10+k]=top.top().second;top.pop();}
 }
 std::ofstream o(argv[4],std::ios::binary);o.write((char*)ids.data(),ids.size()*4);o.write((char*)ds.data(),ds.size()*8);assert(o);
}
