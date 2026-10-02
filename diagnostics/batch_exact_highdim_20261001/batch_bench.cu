#include <cuda_runtime.h>
#include <cub/cub.cuh>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include "rootcause_l2.cuh"
#include "batch_l2.cuh"
#include "batch_output.cuh"

using Clock=std::chrono::steady_clock;
static double seconds(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now()-start).count();
}
static void ck(cudaError_t e) {
    if(e!=cudaSuccess) {std::cerr<<cudaGetErrorString(e)<<'\n';std::exit(2);}
}
template<class T> static T* gpu(size_t items) {
    T* p=nullptr;ck(cudaMalloc(&p,items*sizeof(T)));return p;
}
template<class T> static T* pinned(size_t items) {
    T* p=nullptr;ck(cudaMallocHost(&p,items*sizeof(T)));return p;
}
static std::vector<int> queries(const std::string& path,int n) {
    std::ifstream in(path);int count;in>>count;
    if(!in||count<=0)throw std::runtime_error("bad query header");
    std::vector<int> ids(count);
    for(int& id:ids)if(!(in>>id)||id<0||id>=n)throw std::runtime_error("bad query ID");
    int extra;if(in>>extra)throw std::runtime_error("extra query ID");
    return ids;
}
static std::vector<float> radii(const std::string& spec,size_t count) {
    std::vector<float> values(count);
    if(spec[0]=='@') {
        std::ifstream in(spec.substr(1),std::ios::binary);
        in.read(reinterpret_cast<char*>(values.data()),values.size()*sizeof(float));
        if(!in||in.peek()!=EOF)throw std::runtime_error("bad radius array");
    } else {
        const uint32_t bits=uint32_t(std::stoul(spec,nullptr,0));
        float radius;std::memcpy(&radius,&bits,4);
        std::fill(values.begin(),values.end(),radius);
    }
    for(float radius:values)if(!std::isfinite(radius))throw std::runtime_error("nonfinite radius");
    return values;
}
static uint64_t digest(int count,const int* ids,const float* distances) {
    uint64_t h=1469598103934665603ull;
    for(int i=0;i<count;++i){uint32_t bits;std::memcpy(&bits,distances+i,4);
        h=(h^uint32_t(ids[i]))*1099511628211ull;
        h=(h^bits)*1099511628211ull;}
    return (h^uint32_t(count))*1099511628211ull;
}
static uint64_t id_digest(const int* ids,int count) {
    uint64_t h=1469598103934665603ull;
    for(int i=0;i<count;++i)h=(h^uint32_t(ids[i]))*1099511628211ull;
    return h;
}

struct Batch {
    int n,d,b,qt,blocks;
    std::string mode;
    int *id_list,*query_ids,*out_ids,*host_query_ids,*host_ids,*bridge_hits;
    float *data,*packed,*query_radii,*raw_distance,*out_distance;
    float *host_query_radii,*host_distance;
    uint8_t* flags;
    int64_t *block_counts,*block_prefix,*offsets,*host_offsets;
    void* scan_temp=nullptr;size_t scan_bytes=0;
    cudaStream_t stream;
    cudaGraph_t graph;cudaGraphExec_t graph_exec;
    cudaEvent_t start_event,ready_event;

    Batch(int count,int dimension,int batch,int tile,const std::string& label,
          float bridge_radius,float* database,float* layout,int* order):n(count),d(dimension),b(batch),qt(tile),
          blocks((count+kObjectBlock-1)/kObjectBlock),mode(label),id_list(order),
          data(database),packed(layout) {
        const size_t pairs=size_t(n)*b;
        ck(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
        query_ids=gpu<int>(b);query_radii=gpu<float>(b);
        const bool bridge=mode.rfind("BRIDGE_",0)==0;
        flags=bridge?nullptr:gpu<uint8_t>(pairs);
        bridge_hits=bridge?gpu<int>(n):nullptr;
        raw_distance=gpu<float>(pairs);
        block_counts=gpu<int64_t>(size_t(blocks)*b);
        block_prefix=gpu<int64_t>(size_t(blocks)*b);
        offsets=gpu<int64_t>(b+1);
        out_ids=gpu<int>(pairs);out_distance=gpu<float>(pairs);
        host_query_ids=pinned<int>(b);host_query_radii=pinned<float>(b);
        host_offsets=pinned<int64_t>(b+1);host_ids=pinned<int>(pairs);
        host_distance=pinned<float>(pairs);
        ck(cub::DeviceScan::ExclusiveSum(nullptr,scan_bytes,block_counts,
                                           block_prefix,size_t(blocks)*b,stream));
        ck(cudaMalloc(&scan_temp,scan_bytes));
        ck(cudaEventCreate(&start_event));ck(cudaEventCreate(&ready_event));
        ck(cudaStreamBeginCapture(stream,cudaStreamCaptureModeGlobal));
        ck(cudaMemcpyAsync(query_ids,host_query_ids,b*sizeof(int),cudaMemcpyHostToDevice,stream));
        ck(cudaMemcpyAsync(query_radii,host_query_radii,b*sizeof(float),cudaMemcpyHostToDevice,stream));
        const bool early=mode.back()=='E';
        if(bridge){
            if(b!=1)throw std::runtime_error("bridge requires batch 1");
            if(mode=="BRIDGE_L")rootcauseFlat<true,false><<<blocks,kObjectBlock,0,stream>>>(
                id_list,data,packed,query_ids,n,d,bridge_radius,bridge_hits,
                out_ids,raw_distance,nullptr);
            else if(mode=="BRIDGE_E")rootcauseFlat<true,true><<<blocks,kObjectBlock,0,stream>>>(
                id_list,data,packed,query_ids,n,d,bridge_radius,bridge_hits,
                out_ids,raw_distance,nullptr);
            else throw std::runtime_error("bad bridge mode");
            ck(cudaGetLastError());
        } else if(mode.rfind("SEQ_",0)==0){
            for(int q=0;q<b;++q)launch<1>(early,dim3(blocks,1),q);
        } else if(mode.rfind("GRID_",0)==0){
            launch<1>(early,dim3(blocks,b),0);
        } else if(mode.rfind("TILE_",0)==0){
            const int effective=b==1?1:qt;
            switch(effective){
                case 1:launch<1>(early,dim3(blocks,b),0);break;
                case 2:launch<2>(early,dim3(blocks,(b+1)/2),0);break;
                case 4:launch<4>(early,dim3(blocks,(b+3)/4),0);break;
                case 8:launch<8>(early,dim3(blocks,(b+7)/8),0);break;
                default:throw std::runtime_error("unsupported query tile");
            }
        } else throw std::runtime_error("bad mode");
        if(bridge)collect(bridge_hits);
        else collect(flags);
        ck(cudaStreamEndCapture(stream,&graph));
        ck(cudaGraphInstantiate(&graph_exec,graph));
    }
    template<class Hit> void collect(const Hit* hits) {
        batchBlockCount<<<dim3(blocks,b),kObjectBlock,0,stream>>>(hits,n,blocks,block_counts);
        ck(cub::DeviceScan::ExclusiveSum(scan_temp,scan_bytes,block_counts,
                                           block_prefix,size_t(blocks)*b,stream));
        batchOffsets<<<(b+256)/256,256,0,stream>>>(block_counts,block_prefix,b,blocks,offsets);
        batchScatter<<<dim3(blocks,b),kObjectBlock,0,stream>>>(hits,raw_distance,id_list,
                                                block_prefix,n,blocks,out_ids,out_distance);
    }
    template<int QueryTile> void launch(bool early,dim3 grid,int first) {
        const size_t shared=size_t(QueryTile)*d*sizeof(float);
        if(early)batchDistance<QueryTile,true><<<grid,kObjectBlock,shared,stream>>>(
            id_list,data,packed,query_ids,query_radii,n,d,b,first,flags,raw_distance);
        else batchDistance<QueryTile,false><<<grid,kObjectBlock,shared,stream>>>(
            id_list,data,packed,query_ids,query_radii,n,d,b,first,flags,raw_distance);
        ck(cudaGetLastError());
    }
    struct Timed {double host_ms,gpu_ms;int64_t total;};
    Timed execute(const int* ids,const float* radii) {
        std::memcpy(host_query_ids,ids,b*sizeof(int));
        std::memcpy(host_query_radii,radii,b*sizeof(float));
        const auto begin=Clock::now();
        ck(cudaEventRecord(start_event,stream));
        ck(cudaGraphLaunch(graph_exec,stream));
        ck(cudaEventRecord(ready_event,stream));
        ck(cudaMemcpyAsync(host_offsets,offsets,(b+1)*sizeof(int64_t),
                           cudaMemcpyDeviceToHost,stream));
        ck(cudaStreamSynchronize(stream));
        const int64_t total=host_offsets[b];
        if(host_offsets[0]!=0||total<0||total>int64_t(n)*b)
            throw std::runtime_error("invalid batch offsets");
        for(int q=0;q<b;++q)
            if(host_offsets[q]>host_offsets[q+1]||host_offsets[q+1]-host_offsets[q]>n)
                throw std::runtime_error("invalid query count");
        if(total) {
            ck(cudaMemcpyAsync(host_ids,out_ids,size_t(total)*sizeof(int),
                               cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(host_distance,out_distance,size_t(total)*sizeof(float),
                               cudaMemcpyDeviceToHost,stream));
        }
        ck(cudaStreamSynchronize(stream));
        const double host_ms=seconds(begin)*1000;
        float gpu_ms;ck(cudaEventElapsedTime(&gpu_ms,start_event,ready_event));
        return {host_ms,double(gpu_ms),total};
    }
    ~Batch(){
        ck(cudaGraphExecDestroy(graph_exec));ck(cudaGraphDestroy(graph));
        ck(cudaEventDestroy(start_event));ck(cudaEventDestroy(ready_event));
        ck(cudaFreeHost(host_distance));ck(cudaFreeHost(host_ids));
        ck(cudaFreeHost(host_offsets));ck(cudaFreeHost(host_query_radii));
        ck(cudaFreeHost(host_query_ids));
        for(void* p:{(void*)out_distance,(void*)out_ids,(void*)offsets,
                     (void*)block_prefix,(void*)block_counts,(void*)raw_distance,
                     (void*)flags,(void*)bridge_hits,(void*)query_radii,(void*)query_ids,scan_temp})
            if(p)ck(cudaFree(p));
        ck(cudaStreamDestroy(stream));
    }
};

int main(int argc,char** argv) {
    try {
        if(argc!=12)throw std::runtime_error("usage: batch_bench data.f32bin idlist.i32 measured.qid warmup.qid MODE radius_bits|@file B Q_T reverse output_prefix dump");
        const std::string mode=argv[5],radius_spec=argv[6],out=argv[10];
        const int batch=std::stoi(argv[7]),qt=std::stoi(argv[8]);
        const bool reverse=std::stoi(argv[9])!=0,dump=std::stoi(argv[11])!=0;
        if(batch<1||batch>129||qt<1||qt>8)throw std::runtime_error("unsupported batch or tile");
        const auto setup_start=Clock::now();
        std::ifstream data_file(argv[1],std::ios::binary);int header[3];
        data_file.read(reinterpret_cast<char*>(header),sizeof(header));
        const int d=header[0],n=header[1];
        if(!data_file||header[2]!=2||n<1||d<2||d>960)throw std::runtime_error("bad data header");
        std::vector<float> host_data(size_t(n)*d);
        data_file.read(reinterpret_cast<char*>(host_data.data()),host_data.size()*sizeof(float));
        if(!data_file||data_file.peek()!=EOF)throw std::runtime_error("bad data length");
        for(float x:host_data)if(!std::isfinite(x))throw std::runtime_error("nonfinite data");
        std::vector<int> order(n);std::ifstream ids_file(argv[2],std::ios::binary);
        ids_file.read(reinterpret_cast<char*>(order.data()),size_t(n)*sizeof(int));
        if(!ids_file||ids_file.peek()!=EOF)throw std::runtime_error("bad id_list length");
        std::vector<uint8_t> seen(n,0);
        for(int id:order)if(id<0||id>=n||seen[id]++)throw std::runtime_error("bad id_list permutation");
        const auto measured=queries(argv[3],n),warmup=queries(argv[4],n);
        if(measured.size()%batch||warmup.size()<size_t(batch))
            throw std::runtime_error("query count incompatible with batch");
        const auto all_radii=radii(radius_spec,measured.size());
        float *device_data=gpu<float>(host_data.size());
        int* device_order=gpu<int>(n);
        const size_t layout_items=size_t((n+31)/32)*32*d;
        float* packed=gpu<float>(layout_items);
        ck(cudaMemcpy(device_data,host_data.data(),host_data.size()*sizeof(float),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(device_order,order.data(),size_t(n)*sizeof(int),cudaMemcpyHostToDevice));
        const auto layout_start=Clock::now();
        rootcausePack32<<<(n+511)/512,512>>>(device_order,device_data,packed,n,d);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());
        const double layout_s=seconds(layout_start);
        const double data_setup_s=seconds(setup_start);
        std::ofstream timing(out+".csv"),per_query(out+"_queries.csv");
        if(!timing||!per_query)throw std::runtime_error("cannot open output");
        timing<<"batch_id,host_ms,gpu_ms,result_count_total,d2h_bytes,ordered_hash,query_ids_hash\n";
        per_query<<"batch_id,query_index,qid,count,ordered_hash\n";
        timing<<std::setprecision(12);per_query<<std::setprecision(12);
        std::ofstream binary;
        if(dump){binary.open(out+".bin",std::ios::binary);if(!binary)throw std::runtime_error("cannot dump result");}
        {
        if(mode.rfind("BRIDGE_",0)==0 &&
           (batch!=1 || !std::all_of(all_radii.begin(),all_radii.end(),
                                     [&](float r){return r==all_radii[0];})))
            throw std::runtime_error("bridge needs one uniform radius");
        Batch engine(n,d,batch,qt,mode,all_radii[0],device_data,packed,device_order);
        for(int w=0;w<8;++w) {
            const size_t start=size_t(w*batch)%warmup.size();
            std::vector<float> wr(batch);
            for(int i=0;i<batch;++i)wr[i]=all_radii[size_t(i)%all_radii.size()];
            engine.execute(warmup.data()+start,wr.data());
        }
        const int batches=int(measured.size())/batch;
        for(int step=0;step<batches;++step) {
            const int index=reverse?batches-1-step:step;
            const size_t first=size_t(index)*batch;
            auto result=engine.execute(measured.data()+first,all_radii.data()+first);
            uint64_t group_hash=1469598103934665603ull;
            for(int q=0;q<batch;++q) {
                const size_t begin=size_t(engine.host_offsets[q]);
                const int count=int(engine.host_offsets[q+1]-engine.host_offsets[q]);
                const uint64_t hash=digest(count,engine.host_ids+begin,engine.host_distance+begin);
                group_hash=(group_hash^hash)*1099511628211ull;
                per_query<<index<<','<<first+q<<','<<measured[first+q]<<','<<count<<','<<hash<<'\n';
                if(dump){const int qid=measured[first+q];binary.write(reinterpret_cast<const char*>(&qid),4);
                    binary.write(reinterpret_cast<const char*>(&count),4);
                    binary.write(reinterpret_cast<const char*>(engine.host_ids+begin),size_t(count)*4);
                    binary.write(reinterpret_cast<const char*>(engine.host_distance+begin),size_t(count)*4);}
            }
            const uint64_t qhash=id_digest(measured.data()+first,batch);
            const uint64_t bytes=uint64_t(batch+1)*8+uint64_t(result.total)*8;
            timing<<index<<','<<result.host_ms<<','<<result.gpu_ms<<','<<result.total
                  <<','<<bytes<<','<<group_hash<<','<<qhash<<'\n';
        }
        timing.close();per_query.close();if(dump)binary.close();
        std::ofstream meta(out+".json");
        meta<<std::setprecision(12)<<"{\"mode\":\""<<mode<<"\",\"n\":"<<n
            <<",\"d\":"<<d<<",\"batch\":"<<batch<<",\"query_tile\":"<<qt
            <<",\"queries\":"<<measured.size()<<",\"warmup_batches\":8"
            <<",\"layout_s\":"<<layout_s<<",\"layout_bytes\":"<<layout_items*4
            <<",\"data_setup_s\":"<<data_setup_s<<",\"scan_temp_bytes\":"<<engine.scan_bytes
            <<",\"reverse_batches\":"<<(reverse?"true":"false")<<"}\n";
        }
        ck(cudaFree(packed));ck(cudaFree(device_order));ck(cudaFree(device_data));
        return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
