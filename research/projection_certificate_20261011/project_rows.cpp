// Ordered RN-FP64 CPU projection; no CUDA, FMA, reassociation, FTZ, or DAZ.
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <xmmintrin.h>
static void check(bool x,const char* s){if(!x)throw std::runtime_error(s);}
int main(int argc,char** argv){
 try{
  check(argc==4,"data basis output required");
  check(std::fesetround(FE_TONEAREST)==0,"round mode");
  _mm_setcsr(_mm_getcsr() & ~((1u<<15)|(1u<<6)));
  std::ifstream data(argv[1],std::ios::binary),basis(argv[2],std::ios::binary);
  check(data.good()&&basis.good(),"open inputs");
  int32_t header[3]={};data.read(reinterpret_cast<char*>(header),12);
  check(data.gcount()==12,"short data header");
  check(header[0]==960&&header[1]==1000000&&header[2]==2,"data header");
  std::vector<double> p(16*960);basis.read(reinterpret_cast<char*>(p.data()),p.size()*8);
  check(basis.gcount()==static_cast<std::streamsize>(p.size()*8),"basis length");
  check(basis.peek()==EOF,"basis trailing bytes");
  std::ofstream out(argv[3],std::ios::binary);check(out.good(),"open output");
  std::vector<float> block(8192*960);std::vector<double> result(8192*16);
  for(int start=0;start<1000000;start+=8192){
   int count=std::min(8192,1000000-start);
   data.read(reinterpret_cast<char*>(block.data()),static_cast<std::streamsize>(count)*960*4);
   check(data.gcount()==static_cast<std::streamsize>(count)*960*4,"short data");
   for(int r=0;r<count;++r){
    const float* row=block.data()+r*960;
    for(int j=0;j<16;++j){
     double sum=0.;
     for(int d=0;d<960;++d){double term=static_cast<double>(row[d])*p[j*960+d];sum=sum+term;}
     check(std::isfinite(sum),"projection domain");result[r*16+j]=sum;
    }
   }
   out.write(reinterpret_cast<char*>(result.data()),static_cast<std::streamsize>(count)*16*8);
   check(out.good(),"output write");
  }
  check(data.peek()==EOF,"data trailing bytes");
  out.close();check(!out.fail(),"output close");
  std::cout<<"PASS ordered projection rows=1000000 directions=16 GPU=false\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
