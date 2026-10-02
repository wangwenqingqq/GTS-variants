// Diagnostic cuVS adapter. The P0 collector, delivery path, and timer are reused.
#define main frozen_batch_main
#include "batch_bench.cu"
#undef main
#include <cuvs/distance/pairwise_distance.h>
#include <memory>

static void cv(cuvsError_t status) {
    if(status!=CUVS_SUCCESS)throw std::runtime_error(cuvsGetLastErrorText());
}
static DLManagedTensor tensor(void* data,int64_t* shape,int bits) {
    DLManagedTensor t{};
    t.dl_tensor.data=data;t.dl_tensor.device={kDLCUDA,0};
    t.dl_tensor.ndim=2;t.dl_tensor.dtype={kDLFloat,uint8_t(bits),1};
    t.dl_tensor.shape=shape;
    return t;
}
template<class T> __global__ void ordered_data(const float* data,const int* ids,T* out,int n,int d) {
    const size_t at=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(at<size_t(n)*d)out[at]=T(data[size_t(ids[at/d])*d+at%d]);
}
template<class T> __global__ void gather_queries(const float* data,const int* ids,T* out,int b,int d) {
    const int at=blockIdx.x*blockDim.x+threadIdx.x;
    if(at<b*d)out[at]=T(data[size_t(ids[at/d])*d+at%d]);
}
template<class T> __global__ void threshold_matrix(const T* squared,const float* radii,
                                                    uint8_t* flags,float* distances,
                                                    int n,int b,int start,int rows) {
    const size_t at=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(at>=size_t(rows)*b)return;
    const int q=int(at/rows);
    const float radius=radii[q];
    const double v=double(squared[at]);
    const size_t out=size_t(q)*n+start+at%rows;
    if(radius>=0&&v<=__dmul_rn(double(radius),double(radius))) {
        flags[out]=1;
        distances[out]=float(sqrt(v>0?v:0.0));
    } else flags[out]=0;
}

template<class T> struct ExternalBatch {
    std::unique_ptr<Batch> core;
    T *database,*query,*squared;
    cuvsResources_t resource;
    int64_t shape_q[2];
    DLManagedTensor a;
    cuvsDistanceType metric;
    bool graph_supported;
    int chunk_n;
    double ordered_layout_s;
    ExternalBatch(int n,int d,int b,float* data,float* packed,int* order,
                  cuvsDistanceType m,int chunk):metric(m),chunk_n(std::min(n,chunk)) {
        core=std::make_unique<Batch>(n,d,b,2,"TILE_L",0,data,packed,order);
        graph_supported=(metric==L2Unexpanded);
        if(graph_supported){ck(cudaGraphExecDestroy(core->graph_exec));ck(cudaGraphDestroy(core->graph));}
        database=gpu<T>(size_t(n)*d);query=gpu<T>(size_t(b)*d);
        squared=gpu<T>(size_t(chunk_n)*b);
        const auto layout_start=Clock::now();
        ordered_data<<<(size_t(n)*d+255)/256,256>>>(data,order,database,n,d);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());
        ordered_layout_s=seconds(layout_start);
        shape_q[0]=b;shape_q[1]=d;
        a=tensor(query,shape_q,sizeof(T)*8);
        cv(cuvsResourcesCreate(&resource));cv(cuvsStreamSet(resource,core->stream));
        if(graph_supported){
            ck(cudaStreamBeginCapture(core->stream,cudaStreamCaptureModeGlobal));
            pipeline();
            ck(cudaStreamEndCapture(core->stream,&core->graph));
            ck(cudaGraphInstantiate(&core->graph_exec,core->graph));
        }
    }
    void pipeline() {
        const int n=core->n,b=core->b,d=core->d;
        ck(cudaMemcpyAsync(core->query_ids,core->host_query_ids,b*sizeof(int),cudaMemcpyHostToDevice,core->stream));
        ck(cudaMemcpyAsync(core->query_radii,core->host_query_radii,b*sizeof(float),cudaMemcpyHostToDevice,core->stream));
        gather_queries<<<(b*d+255)/256,256,0,core->stream>>>(core->data,core->query_ids,query,b,d);
        for(int start=0;start<n;start+=chunk_n) {
            const int rows=std::min(chunk_n,n-start);
            int64_t shape_db[2]={rows,d},shape_out[2]={b,rows};
            auto z=tensor(database+size_t(start)*d,shape_db,sizeof(T)*8);
            auto c=tensor(squared,shape_out,sizeof(T)*8);
            cv(cuvsPairwiseDistance(resource,&a,&z,&c,metric,0));
            threshold_matrix<<<(size_t(rows)*b+255)/256,256,0,core->stream>>>(
                squared,core->query_radii,core->flags,core->raw_distance,n,b,start,rows);
        }
        ck(cudaGetLastError());core->collect(core->flags);
    }
    Batch::Timed execute(const int* ids,const float* radii) {
        if(graph_supported)return core->execute(ids,radii);
        const int b=core->b,n=core->n;
        std::memcpy(core->host_query_ids,ids,b*4);
        std::memcpy(core->host_query_radii,radii,b*4);
        const auto begin=Clock::now();
        ck(cudaEventRecord(core->start_event,core->stream));
        pipeline();
        ck(cudaEventRecord(core->ready_event,core->stream));
        ck(cudaMemcpyAsync(core->host_offsets,core->offsets,(b+1)*sizeof(int64_t),cudaMemcpyDeviceToHost,core->stream));
        ck(cudaStreamSynchronize(core->stream));
        const int64_t total=core->host_offsets[b];
        if(core->host_offsets[0]!=0||total<0||total>int64_t(n)*b)throw std::runtime_error("invalid offsets");
        for(int q=0;q<b;++q)
            if(core->host_offsets[q]>core->host_offsets[q+1]||core->host_offsets[q+1]-core->host_offsets[q]>n)
                throw std::runtime_error("invalid query count");
        if(total){
            ck(cudaMemcpyAsync(core->host_ids,core->out_ids,size_t(total)*4,cudaMemcpyDeviceToHost,core->stream));
            ck(cudaMemcpyAsync(core->host_distance,core->out_distance,size_t(total)*4,cudaMemcpyDeviceToHost,core->stream));
        }
        ck(cudaStreamSynchronize(core->stream));
        float gpu_ms;ck(cudaEventElapsedTime(&gpu_ms,core->start_event,core->ready_event));
        return {seconds(begin)*1000,double(gpu_ms),total};
    }
    ~ExternalBatch(){core.reset();cv(cuvsResourcesDestroy(resource));
        ck(cudaFree(squared));ck(cudaFree(query));ck(cudaFree(database));}
};

int main(int argc,char** argv) {
    try {
        if(argc!=12&&argc!=13)throw std::runtime_error("usage: p5_external data.f32bin idlist.i32 measured.qid warmup.qid LIB64_U|LIB64_X|LIB32_U|LIB32_X radius_bits B Q_T reverse output_prefix dump [chunk_n]");
        const std::string mode=argv[5],out=argv[10];
        const int b=std::stoi(argv[7]),qt=std::stoi(argv[8]);
        const bool reverse=std::stoi(argv[9])!=0,dump=std::stoi(argv[11])!=0;
        if(b<1||b>33||qt!=2)throw std::runtime_error("bad batch/Q_T");
        const bool use64=mode=="LIB64_U"||mode=="LIB64_X";
        if(!use64&&mode!="LIB32_U"&&mode!="LIB32_X")throw std::runtime_error("bad external mode");
        const cuvsDistanceType metric=mode.back()=='U'?L2Unexpanded:L2Expanded;
        const auto setup_start=Clock::now();
        std::ifstream data_file(argv[1],std::ios::binary);int header[3];
        data_file.read(reinterpret_cast<char*>(header),sizeof(header));
        const int d=header[0],n=header[1];
        const int chunk_n=argc==13?std::stoi(argv[12]):n;
        if(chunk_n<1)throw std::runtime_error("bad chunk size");
        if(!data_file||header[2]!=2||n<1||d<2||d>960)throw std::runtime_error("bad data header");
        std::vector<float> host_data(size_t(n)*d);
        data_file.read(reinterpret_cast<char*>(host_data.data()),host_data.size()*4);
        if(!data_file||data_file.peek()!=EOF)throw std::runtime_error("bad data length");
        for(float x:host_data)if(!std::isfinite(x))throw std::runtime_error("nonfinite data");
        std::vector<int> order(n);std::ifstream ids_file(argv[2],std::ios::binary);
        ids_file.read(reinterpret_cast<char*>(order.data()),size_t(n)*4);
        if(!ids_file||ids_file.peek()!=EOF)throw std::runtime_error("bad id_list length");
        std::vector<uint8_t> seen(n,0);
        for(int id:order)if(id<0||id>=n||seen[id]++)throw std::runtime_error("bad id_list permutation");
        const auto measured=queries(argv[3],n),warmup=queries(argv[4],n);
        if(measured.size()%b||warmup.size()<size_t(b))throw std::runtime_error("bad qid batch");
        const auto all_radii=radii(argv[6],measured.size());
        float* data_dev=gpu<float>(host_data.size());int* order_dev=gpu<int>(n);
        ck(cudaMemcpy(data_dev,host_data.data(),host_data.size()*4,cudaMemcpyHostToDevice));
        ck(cudaMemcpy(order_dev,order.data(),size_t(n)*4,cudaMemcpyHostToDevice));
        std::ofstream timing(out+".csv"),per_query(out+"_queries.csv");
        if(!timing||!per_query)throw std::runtime_error("cannot open output");
        timing<<"batch_id,host_ms,gpu_ms,result_count_total,d2h_bytes,ordered_hash,query_ids_hash\n";
        per_query<<"batch_id,query_index,qid,count,ordered_hash\n";
        timing<<std::setprecision(12);per_query<<std::setprecision(12);
        std::ofstream binary;
        if(dump){binary.open(out+".bin",std::ios::binary);if(!binary)throw std::runtime_error("cannot dump");}
        const auto run=[&](auto& ext) {
            Batch& engine=*ext.core;
            const double data_setup_s=seconds(setup_start);
            for(int w=0;w<8;++w){const size_t start=size_t(w*b)%warmup.size();
                std::vector<float> wr(b);for(int i=0;i<b;++i)wr[i]=all_radii[size_t(i)%all_radii.size()];
                ext.execute(warmup.data()+start,wr.data());}
            const int batches=int(measured.size())/b;
            for(int step=0;step<batches;++step){const int index=reverse?batches-1-step:step;
                const size_t first=size_t(index)*b;
                auto result=ext.execute(measured.data()+first,all_radii.data()+first);
                uint64_t group_hash=1469598103934665603ull;
                for(int q=0;q<b;++q){const size_t begin=size_t(engine.host_offsets[q]);
                    const int count=int(engine.host_offsets[q+1]-engine.host_offsets[q]);
                    const uint64_t hash=digest(count,engine.host_ids+begin,engine.host_distance+begin);
                    group_hash=(group_hash^hash)*1099511628211ull;
                    per_query<<index<<','<<first+q<<','<<measured[first+q]<<','<<count<<','<<hash<<'\n';
                    if(dump){const int qid=measured[first+q];binary.write(reinterpret_cast<const char*>(&qid),4);
                        binary.write(reinterpret_cast<const char*>(&count),4);
                        binary.write(reinterpret_cast<const char*>(engine.host_ids+begin),size_t(count)*4);
                        binary.write(reinterpret_cast<const char*>(engine.host_distance+begin),size_t(count)*4);}}
                const uint64_t bytes=uint64_t(b+1)*8+uint64_t(result.total)*8;
                timing<<index<<','<<result.host_ms<<','<<result.gpu_ms<<','<<result.total
                      <<','<<bytes<<','<<group_hash<<','<<id_digest(measured.data()+first,b)<<'\n';}
            std::ofstream meta(out+".json");
            meta<<std::setprecision(12)<<"{\"mode\":\""<<mode<<"\",\"n\":"<<n<<",\"d\":"<<d
                <<",\"batch\":"<<b<<",\"queries\":"<<measured.size()
                <<",\"warmup_batches\":8,\"data_setup_s\":"<<data_setup_s
                <<",\"scan_temp_bytes\":"<<engine.scan_bytes<<",\"chunk_n\":"<<ext.chunk_n
                <<",\"ordered_layout_s\":"<<ext.ordered_layout_s
                <<",\"ordered_layout_bytes\":"<<size_t(n)*d*(use64?8:4)
                <<",\"squared_workspace_bytes\":"<<size_t(ext.chunk_n)*b*(use64?8:4)
                <<",\"graph\":"<<(ext.graph_supported?"true":"false")<<"}\n";
        };
        if(use64){ExternalBatch<double> ext(n,d,b,data_dev,nullptr,order_dev,metric,chunk_n);run(ext);}
        else {ExternalBatch<float> ext(n,d,b,data_dev,nullptr,order_dev,metric,chunk_n);run(ext);}
        ck(cudaFree(order_dev));ck(cudaFree(data_dev));
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
