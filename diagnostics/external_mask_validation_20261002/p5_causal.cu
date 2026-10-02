// Reuse the frozen P0-P3 batch collector, delivery, timer, and SCAN kernel.
#define main frozen_batch_main
#include "batch_bench.cu"
#undef main
#include <memory>
#include <thrust/iterator/counting_iterator.h>
#include "batch_tree_prefix.cuh"
#include "batch_candidate_tasks.cuh"

__global__ void fill_all_mask(uint8_t* mask,size_t slots) {
    const size_t i=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<slots)mask[i]=1;
}

struct TreeIndex {
    int depth,stride,nodes;
    TN* tree_dev;
    int *empty_dev,*frontier_dev;
    unsigned long long *lower,*upper;
    double refit_s;
    size_t index_bytes;

    TreeIndex(const std::string& path,int n,int d,int wanted_depth,
              const std::vector<int>& order,float* data,int* order_dev):depth(wanted_depth) {
        const auto begin=Clock::now();
        std::ifstream in(path,std::ios::binary);int header[3];
        in.read(reinterpret_cast<char*>(header),sizeof(header));
        nodes=header[2];
        if(!in||header[0]!=d||header[1]!=n||depth<1||depth>4)
            throw std::runtime_error("tree/data mismatch");
        std::vector<TN> tree(nodes);std::vector<int> empty(nodes),tree_order(n);
        in.read(reinterpret_cast<char*>(tree.data()),nodes*sizeof(TN));
        in.read(reinterpret_cast<char*>(empty.data()),nodes*sizeof(int));
        in.read(reinterpret_cast<char*>(tree_order.data()),n*sizeof(int));
        if(!in||in.peek()!=EOF||tree_order!=order)
            throw std::runtime_error("tree dump or id_list mismatch");
        index_bytes=sizeof(header)+nodes*(sizeof(TN)+sizeof(int))+n*sizeof(int);
        stride=1;int width=10;
        for(int level=1;level<=depth;++level){stride+=width;width*=10;}
        if(stride>nodes)throw std::runtime_error("tree too shallow");
        tree_dev=gpu<TN>(nodes);empty_dev=gpu<int>(nodes);
        frontier_dev=gpu<int>(n);
        lower=gpu<unsigned long long>(nodes);upper=gpu<unsigned long long>(nodes);
        ck(cudaMemcpy(tree_dev,tree.data(),nodes*sizeof(TN),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(empty_dev,empty.data(),nodes*sizeof(int),cudaMemcpyHostToDevice));
        std::vector<unsigned long long> lo(nodes,~0ull),hi(nodes,0);
        ck(cudaMemcpy(lower,lo.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(upper,hi.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
        int* map_dev=gpu<int>(n);std::vector<int> mapping(n);
        int start=1;width=10;
        for(int level=1;level<=depth;++level) {
            std::fill(mapping.begin(),mapping.end(),-1);
            for(int nid=start;nid<start+width;++nid)if(empty[nid]==0) {
                const TN node=tree[nid];
                if(node.pid<0||node.pid>=n||node.lid<0||node.size<=0||node.lid+node.size>n)
                    throw std::runtime_error("bad tree node");
                for(int pos=node.lid;pos<node.lid+node.size;++pos) {
                    if(mapping[pos]!=-1)throw std::runtime_error("overlap tree node");
                    mapping[pos]=nid;
                }
            }
            if(std::find(mapping.begin(),mapping.end(),-1)!=mapping.end())
                throw std::runtime_error("incomplete tree level");
            ck(cudaMemcpy(map_dev,mapping.data(),n*sizeof(int),cudaMemcpyHostToDevice));
            refit_bounds<<<(n+255)/256,256>>>(map_dev,order_dev,tree_dev,data,n,d,lower,upper);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            if(level==depth)
                ck(cudaMemcpy(frontier_dev,mapping.data(),n*sizeof(int),cudaMemcpyHostToDevice));
            start+=width;width*=10;
        }
        ck(cudaFree(map_dev));
        refit_s=seconds(begin);
    }
    ~TreeIndex(){
        ck(cudaFree(upper));ck(cudaFree(lower));ck(cudaFree(frontier_dev));
        ck(cudaFree(empty_dev));ck(cudaFree(tree_dev));
    }
};

struct TreeBatch {
    std::unique_ptr<Batch> core;
    int b,n,d,tiles,pairs;
    TreeIndex& index;
    std::string path;
    bool early;
    int *node_flags,*positions,*selected_count,*task_tiles,*task_count;
    uint8_t *candidate,*keep;
    uint32_t *mask0,*mask1;
    void* select_temp;size_t select_bytes;

    TreeBatch(int n_,int d_,int batch,int qt,const std::string& label,
              float* data,float* packed,int* order,TreeIndex& tree):
              b(batch),n(n_),d(d_),tiles((n+31)/32),pairs((batch+1)/2),
              index(tree),path(label.substr(0,label.size()-2)),early(label.back()=='E') {
        if(qt!=2||label.size()<3||label[label.size()-2]!='_')
            throw std::runtime_error("bad P4 mode or query tile");
        if(path!="C_ID"&&path!="C_MASK"&&path!="C_TASK"&&
           path!="MASK_ALL"&&path!="TREE_ALL"&&path!="TREE_REAL")
            throw std::runtime_error("unknown tree path");
        core=std::make_unique<Batch>(n,d,b,qt,"TILE_L",0,data,packed,order);
        ck(cudaGraphExecDestroy(core->graph_exec));ck(cudaGraphDestroy(core->graph));
        node_flags=gpu<int>(size_t(b)*index.stride);
        candidate=gpu<uint8_t>(size_t(b)*n);
        positions=gpu<int>(size_t(b)*n);selected_count=gpu<int>(b);
        task_tiles=gpu<int>(size_t(pairs)*tiles);task_count=gpu<int>(pairs);
        mask0=gpu<uint32_t>(size_t(pairs)*tiles);mask1=gpu<uint32_t>(size_t(pairs)*tiles);
        keep=gpu<uint8_t>(size_t(pairs)*tiles);
        size_t id_bytes=0,task_bytes=0;
        thrust::counting_iterator<int> first(0);
        ck(cub::DeviceSelect::Flagged(nullptr,id_bytes,first,candidate,positions,
                                      selected_count,n,core->stream));
        ck(cub::DeviceSelect::Flagged(nullptr,task_bytes,first,keep,task_tiles,
                                      task_count,tiles,core->stream));
        select_bytes=std::max(id_bytes,task_bytes);
        ck(cudaMalloc(&select_temp,select_bytes));
        ck(cudaStreamBeginCapture(core->stream,cudaStreamCaptureModeGlobal));
        ck(cudaMemcpyAsync(core->query_ids,core->host_query_ids,b*sizeof(int),
                           cudaMemcpyHostToDevice,core->stream));
        ck(cudaMemcpyAsync(core->query_radii,core->host_query_radii,b*sizeof(float),
                           cudaMemcpyHostToDevice,core->stream));
        ck(cudaMemsetAsync(core->flags,0,size_t(b)*n*sizeof(uint8_t),core->stream));
        const size_t slots=size_t(b)*n;
        if(path=="MASK_ALL") {
            fill_all_mask<<<(slots+255)/256,256,0,core->stream>>>(candidate,slots);
        } else {
            ck(cudaMemsetAsync(node_flags,0,size_t(b)*index.stride*sizeof(int),core->stream));
            roots<<<(b+255)/256,256,0,core->stream>>>(node_flags,index.stride,b);
            int start=1,width=10;
            for(int level=1;level<=index.depth;++level) {
                parent_walk<<<dim3((width/10+255)/256,b),256,0,core->stream>>>(
                    node_flags,index.stride,start,width/10,index.tree_dev,index.empty_dev,
                    index.lower,index.upper,data,core->query_ids,core->query_radii,b,d,nullptr);
                start+=width;width*=10;
            }
            const int force_all=path=="TREE_ALL";
            candidate_mask<<<(slots+255)/256,256,0,core->stream>>>(
                node_flags,index.stride,index.frontier_dev,n,b,force_all,candidate);
        }
        if(path=="C_ID") {
            for(int q=0;q<b;++q)
                ck(cub::DeviceSelect::Flagged(select_temp,select_bytes,first,
                   candidate+size_t(q)*n,positions+size_t(q)*n,selected_count+q,n,core->stream));
            if(early)id_distance<true><<<dim3(core->blocks,b),kObjectBlock,d*4,core->stream>>>(
                order,data,packed,core->query_ids,core->query_radii,positions,selected_count,
                n,d,b,core->flags,core->raw_distance);
            else id_distance<false><<<dim3(core->blocks,b),kObjectBlock,d*4,core->stream>>>(
                order,data,packed,core->query_ids,core->query_radii,positions,selected_count,
                n,d,b,core->flags,core->raw_distance);
        } else if(path=="C_MASK"||path=="MASK_ALL"||path=="TREE_ALL"||path=="TREE_REAL") {
            if(early)masked_distance<2,true><<<dim3(core->blocks,pairs),kObjectBlock,d*8,core->stream>>>(
                order,data,packed,core->query_ids,core->query_radii,candidate,
                n,d,b,core->flags,core->raw_distance);
            else masked_distance<2,false><<<dim3(core->blocks,pairs),kObjectBlock,d*8,core->stream>>>(
                order,data,packed,core->query_ids,core->query_radii,candidate,
                n,d,b,core->flags,core->raw_distance);
        } else {
            make_tile_masks<<<dim3((tiles+255)/256,pairs),256,0,core->stream>>>(
                candidate,n,b,tiles,mask0,mask1,keep);
            for(int q=0;q<pairs;++q)
                ck(cub::DeviceSelect::Flagged(select_temp,select_bytes,first,
                   keep+size_t(q)*tiles,task_tiles+size_t(q)*tiles,task_count+q,tiles,core->stream));
            const dim3 grid((tiles+15)/16,pairs);
            if(early)task_distance<true><<<grid,kObjectBlock,d*8,core->stream>>>(
                data,packed,core->query_ids,core->query_radii,task_tiles,task_count,
                mask0,mask1,n,d,b,tiles,core->flags,core->raw_distance);
            else task_distance<false><<<grid,kObjectBlock,d*8,core->stream>>>(
                data,packed,core->query_ids,core->query_radii,task_tiles,task_count,
                mask0,mask1,n,d,b,tiles,core->flags,core->raw_distance);
        }
        ck(cudaGetLastError());
        core->collect(core->flags);
        ck(cudaStreamEndCapture(core->stream,&core->graph));
        ck(cudaGraphInstantiate(&core->graph_exec,core->graph));
    }
    ~TreeBatch(){
        core.reset();
        ck(cudaFree(select_temp));ck(cudaFree(keep));ck(cudaFree(mask1));ck(cudaFree(mask0));
        ck(cudaFree(task_count));ck(cudaFree(task_tiles));ck(cudaFree(selected_count));
        ck(cudaFree(positions));ck(cudaFree(candidate));ck(cudaFree(node_flags));
    }
};

int main(int argc,char** argv) {
    try {
        if(argc!=14)throw std::runtime_error("usage: p5_causal data.f32bin idlist.i32 measured.qid warmup.qid MODE radius_bits B Q_T reverse output_prefix dump index.bin depth");
        const std::string mode=argv[5],out=argv[10];
        const int batch=std::stoi(argv[7]),qt=std::stoi(argv[8]),depth=std::stoi(argv[13]);
        const bool reverse=std::stoi(argv[9])!=0,dump=std::stoi(argv[11])!=0;
        if(batch<1||batch>33||qt!=2)throw std::runtime_error("bad batch/Q_T");
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
        if(measured.size()%batch||warmup.size()<size_t(batch))throw std::runtime_error("bad qid batch");
        const auto all_radii=radii(argv[6],measured.size());
        float* data_dev=gpu<float>(host_data.size());int* order_dev=gpu<int>(n);
        const size_t layout_items=size_t((n+31)/32)*32*d;
        float* packed=gpu<float>(layout_items);
        ck(cudaMemcpy(data_dev,host_data.data(),host_data.size()*sizeof(float),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(order_dev,order.data(),size_t(n)*sizeof(int),cudaMemcpyHostToDevice));
        const auto layout_start=Clock::now();
        rootcausePack32<<<(n+511)/512,512>>>(order_dev,data_dev,packed,n,d);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());
        const double layout_s=seconds(layout_start);
        TreeIndex tree(argv[12],n,d,depth,order,data_dev,order_dev);
        const double data_setup_s=seconds(setup_start);
        std::ofstream timing(out+".csv"),per_query(out+"_queries.csv");
        if(!timing||!per_query)throw std::runtime_error("cannot open output");
        timing<<"batch_id,host_ms,gpu_ms,result_count_total,d2h_bytes,ordered_hash,query_ids_hash\n";
        per_query<<"batch_id,query_index,qid,count,ordered_hash\n";
        timing<<std::setprecision(12);per_query<<std::setprecision(12);
        std::ofstream binary;
        if(dump){binary.open(out+".bin",std::ios::binary);if(!binary)throw std::runtime_error("cannot dump");}
        {
            std::unique_ptr<Batch> scan;
            std::unique_ptr<TreeBatch> candidate;
            Batch* engine=nullptr;
            if(mode=="SCAN_L"||mode=="SCAN_E") {
                scan=std::make_unique<Batch>(n,d,batch,qt,mode=="SCAN_L"?"TILE_L":"TILE_E",
                                              all_radii[0],data_dev,packed,order_dev);
                engine=scan.get();
            } else {
                candidate=std::make_unique<TreeBatch>(n,d,batch,qt,mode,
                                                      data_dev,packed,order_dev,tree);
                engine=candidate->core.get();
            }
            for(int w=0;w<8;++w) {
                const size_t start=size_t(w*batch)%warmup.size();
                std::vector<float> wr(batch);
                for(int i=0;i<batch;++i)wr[i]=all_radii[size_t(i)%all_radii.size()];
                engine->execute(warmup.data()+start,wr.data());
            }
            const int batches=int(measured.size())/batch;
            for(int step=0;step<batches;++step) {
                const int index=reverse?batches-1-step:step;
                const size_t first=size_t(index)*batch;
                auto result=engine->execute(measured.data()+first,all_radii.data()+first);
                uint64_t group_hash=1469598103934665603ull;
                for(int q=0;q<batch;++q) {
                    const size_t begin=size_t(engine->host_offsets[q]);
                    const int count=int(engine->host_offsets[q+1]-engine->host_offsets[q]);
                    const uint64_t hash=digest(count,engine->host_ids+begin,engine->host_distance+begin);
                    group_hash=(group_hash^hash)*1099511628211ull;
                    per_query<<index<<','<<first+q<<','<<measured[first+q]<<','<<count<<','<<hash<<'\n';
                    if(dump){const int qid=measured[first+q];binary.write(reinterpret_cast<const char*>(&qid),4);
                        binary.write(reinterpret_cast<const char*>(&count),4);
                        binary.write(reinterpret_cast<const char*>(engine->host_ids+begin),size_t(count)*4);
                        binary.write(reinterpret_cast<const char*>(engine->host_distance+begin),size_t(count)*4);}
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
                <<",\"data_setup_s\":"<<data_setup_s<<",\"index_refit_s\":"<<tree.refit_s
                <<",\"index_bytes\":"<<tree.index_bytes<<",\"scan_temp_bytes\":"<<engine->scan_bytes
                <<",\"reverse_batches\":"<<(reverse?"true":"false")<<"}\n";
        }
        ck(cudaFree(packed));ck(cudaFree(order_dev));ck(cudaFree(data_dev));
        return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
