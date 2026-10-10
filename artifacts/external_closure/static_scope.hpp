#pragma once
// Host-only static adapter: a non-indexed query row preserves all GPU kernels.
namespace closure {
static const float* host=nullptr;
static int n=0,d=0;
static double warm_ms[2]={},pass_ms[2]={},buffer_prepare_ms=0,buffer_release_ms=0;
static U10Clock::time_point phase,buffer;
inline void before(int i,int flag) {
    if(flag!=2&&flag!=3)throw std::runtime_error("static adapter forbids updates");
    if(i==0||i==8||i==16||i==48)phase=U10Clock::now();
}
inline void submit(float* device,int row) {
    if(row<0||row>=n)throw std::runtime_error("static query row");
    u10_ck(cudaMemcpy(device+size_t(n)*d,host+size_t(row)*d,size_t(d)*4,cudaMemcpyHostToDevice));
}
inline void after(int i,int flag) {
    if(i==7||i==15)warm_ms[flag-2]=u10_ms(phase);
    if(i==47||i==79)pass_ms[flag-2]=u10_ms(phase);
}
inline void write(const std::string& out,double setup,double load,double release) {
    std::ofstream f(out+".static.json");f<<std::setprecision(17)
      <<"{\"method\":\"GTSPP_P\",\"preparation_ms\":"<<load
      <<",\"build_ms\":"<<setup-load+buffer_prepare_ms
      <<",\"warmup_ms\":"<<warm_ms[0]+warm_ms[1]
      <<",\"range_pass_ms\":"<<pass_ms[0]<<",\"knn_pass_ms\":"<<pass_ms[1]
      <<",\"release_ms\":"<<release+buffer_release_ms
      <<",\"host_query_upload_bytes\":"<<size_t(80)*d*4
      <<",\"extra_nonindexed_query_bytes\":"<<size_t(d)*4
      <<",\"queries\":80,\"warmup_per_task\":8,\"measured_per_task\":32}\n";
    if(!f)throw std::runtime_error("static scope write");
}
}
