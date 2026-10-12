#include "u10_trace.hpp"
#include "tree.cuh"
#pragma push_macro("short")
#undef short
#include <filesystem>
#pragma pop_macro("short")
int main(int argc,char** argv) try {
    uk::require(argc==6,"AOS PRE CURRENT DOSE OUT");std::string out=argv[5];
    uk::require(std::filesystem::is_directory(out),"replay output directory");
    bt::configure();uk::require(bt::tiled&&bt::auditing,"frozen TILED audited construction");
    causal::configure(argv[2],argv[3],std::stoi(argv[4]),out);
    auto data=causal::read<float>(argv[1]);uk::require(data.size()==size_t(1000000)*960,"frozen N1M D960");
    int* info=nullptr;float* device=nullptr;int* order=nullptr;int* empty=nullptr;int* maximum=nullptr;TN* nodes=nullptr;int height=0;
    u10_ck(cudaMallocManaged((void**)&info,3*sizeof(int)));info[0]=960;info[1]=1000000;info[2]=2;
    u10_ck(cudaMalloc((void**)&device,data.size()*sizeof(float)));
    u10_ck(cudaMemcpy(device,data.data(),data.size()*sizeof(float),cudaMemcpyHostToDevice));
    indexConstru(device,nullptr,nullptr,info,order,nodes,maximum,height,empty);
    u10_ck(cudaDeviceSynchronize());bt::folder=out;
    bt::dump("order.i32",bt::copy(order,info[1]));bt::dump("nodes.bin",bt::copy(nodes,maximum[0]));bt::dump("empty.i32",bt::copy(empty,maximum[0]));
    std::ofstream receipt(out+"/REPLAY.json");receipt<<"{\"n\":1000000,\"d\":960,\"nodes\":"<<maximum[0]<<",\"height\":"<<height<<",\"dose\":"<<causal::dose<<",\"performance_claim\":false}\n";
    uk::require(bool(receipt),"replay receipt");causal::release();
    for(void* p:{(void*)info,(void*)device,(void*)order,(void*)nodes,(void*)empty,(void*)maximum})u10_ck(cudaFree(p));
    u10_ck(cudaDeviceSynchronize());return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
