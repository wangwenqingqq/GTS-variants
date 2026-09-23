// Fixed-capacity query control; original source is supplied separately.
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <string>
#include <vector>
#include <sys/resource.h>
#include <cub/cub.cuh>
#define main original_gts_main
#include "source/src/main.cu"
#undef main
#undef short

using Clock = std::chrono::steady_clock;
double seconds(Clock::time_point t) { return std::chrono::duration<double>(Clock::now()-t).count(); }
void ck(cudaError_t e) { if(e!=cudaSuccess) { fprintf(stderr,"CUDA error: %s\n",cudaGetErrorString(e)); exit(2); } }
template<class T> void alloc(T*& p, size_t n) { ck(cudaMalloc(&p,n*sizeof(T))); }

// The original projection, with its logical length read on device; no fusion.
__global__ void projectBounded(const int* count, int* outid, float* outdis,
                              const int* ids, const float* ds, const int* prefix) {
    for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<*count;i+=gridDim.x*blockDim.x) {
        outid[i]=ids[i]-prefix[ids[i]]; outdis[i]=ds[i];
    }
}

struct Fixed {
    const int nodes=111, slots=2220;
    int n, height;
    cudaStream_t stream;
    cudaGraph_t graph=nullptr;
    cudaGraphExec_t executable=nullptr;
    void* temp=nullptr; size_t tempbytes=0;
    int *qid,*flags,*candidates,*queryids,*nodecount,*nodeprefix,*nodeidx;
    int *candidate_count,*hit_count,*hits,*count,*prefix,*rawids,*ids,*outids;
    float *rawdis,*ds,*outdis;
    int *hq,*hc,*hi; float* hd;
    Fixed(int count_n,int h):n(count_n),height(h) {
        ck(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
        alloc(qid,1);alloc(flags,nodes);alloc(candidates,nodes);alloc(queryids,nodes);
        alloc(nodecount,1);alloc(nodeprefix,1);alloc(nodeidx,nodes);
        alloc(candidate_count,1);alloc(hit_count,1);alloc(hits,slots);alloc(count,1);alloc(prefix,1);
        alloc(rawids,slots);alloc(rawdis,slots);alloc(ids,slots);alloc(ds,slots);alloc(outids,slots);alloc(outdis,slots);
        ck(cudaMallocHost(&hq,sizeof(int)));ck(cudaMallocHost(&hc,sizeof(int)));
        ck(cudaMallocHost(&hi,slots*sizeof(int)));ck(cudaMallocHost(&hd,slots*sizeof(float)));
        size_t z=0;
        ck(cub::DeviceReduce::Sum(nullptr,z,flags,candidate_count,nodes,stream));tempbytes=std::max(tempbytes,z);
        ck(cub::DeviceReduce::Sum(nullptr,z,hits,hit_count,slots,stream));tempbytes=std::max(tempbytes,z);
        ck(cub::DeviceScan::ExclusiveSum(nullptr,z,nodecount,nodeprefix,1,stream));tempbytes=std::max(tempbytes,z);
        ck(cub::DeviceScan::ExclusiveSum(nullptr,z,flags,nodeidx,nodes,stream));tempbytes=std::max(tempbytes,z);
        ck(cub::DeviceScan::InclusiveSum(nullptr,z,hits,hits,slots,stream));tempbytes=std::max(tempbytes,z);
        ck(cub::DeviceScan::InclusiveSum(nullptr,z,is_delete,is_delete_prefix,n,stream));tempbytes=std::max(tempbytes,z);
        ck(cudaMalloc(&temp,tempbytes));
        // Initialize inactive payload capacity so fixed-size host delivery is defined.
        ck(cudaMemset(outids,0,slots*sizeof(int)));ck(cudaMemset(outdis,0,slots*sizeof(float)));
    }
    void enqueue(float radius) {
        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));
        initQnode<<<1,THREAD_NUM,0,stream>>>(flags,1,max_node_num);
        int start=1, num=10;
        for(int level=1;level<height;++level) {
            findNextRnn<<<1,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s);
            updatePnodeFlag<<<1,THREAD_NUM,0,stream>>>(flags,start,num,max_node_num,empty_list);
            start+=num; num*=10;
        }
        ck(cub::DeviceReduce::Sum(temp,tempbytes,flags,candidate_count,nodes,stream));
        initRes<<<(slots+511)/512,512,0,stream>>>(hits,slots);
        getQnodeCount<<<1,512,0,stream>>>(1,flags,max_node_num,nodecount,0);
        ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,nodecount,nodeprefix,1,stream));
        ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,flags,nodeidx,nodes,stream));
        mergeLeafNode<<<1,512,0,stream>>>(flags,nodeidx,candidates,max_node_num,1,queryids,0);
        leafProcessRnnUpdate<<<nodes,512,0,stream>>>(candidates,node_list,id_list,queryids,data_d,qid,
            rawids,rawdis,data_info,radius,hits,candidate_count,data_s,size_s,is_delete);
        ck(cub::DeviceReduce::Sum(temp,tempbytes,hits,hit_count,slots,stream));
        getQresultCount<<<1,512,0,stream>>>(1,nodecount,nodeprefix,count,hits);
        ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,count,prefix,1,stream));
        ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,hits,hits,slots,stream));
        mergeResultRnn<<<(slots+511)/512,512,0,stream>>>(hits,rawids,rawdis,ids,ds,candidate_count);
        ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
        projectBounded<<<(slots+511)/512,512,0,stream>>>(count,outids,outdis,ids,ds,is_delete_prefix);
        ck(cudaMemcpyAsync(hc,count,sizeof(int),cudaMemcpyDeviceToHost,stream));
        ck(cudaMemcpyAsync(hi,outids,slots*sizeof(int),cudaMemcpyDeviceToHost,stream));
        ck(cudaMemcpyAsync(hd,outdis,slots*sizeof(float),cudaMemcpyDeviceToHost,stream));
        ck(cudaGetLastError());
    }
    double capture(float radius) {
        auto t=Clock::now();
        ck(cudaStreamBeginCapture(stream,cudaStreamCaptureModeGlobal));enqueue(radius);
        ck(cudaStreamEndCapture(stream,&graph));
        ck(cudaGraphInstantiate(&executable,graph,0));return seconds(t);
    }
    void query(int q,float radius,bool replay) {
        *hq=q;
        if(replay)ck(cudaGraphLaunch(executable,stream));else enqueue(radius);
        ck(cudaStreamSynchronize(stream));
        if(*hc<0 || *hc>slots) { fprintf(stderr,"Capacity failure\n");exit(3); }
    }
    ~Fixed() {
        if(executable)ck(cudaGraphExecDestroy(executable));if(graph)ck(cudaGraphDestroy(graph));
        for(void* p:{(void*)qid,(void*)flags,(void*)candidates,(void*)queryids,(void*)nodecount,(void*)nodeprefix,(void*)nodeidx,
                    (void*)candidate_count,(void*)hit_count,(void*)hits,(void*)count,(void*)prefix,(void*)rawids,(void*)rawdis,
                    (void*)ids,(void*)ds,(void*)outids,(void*)outdis,temp})ck(cudaFree(p));
        ck(cudaFreeHost(hq));ck(cudaFreeHost(hc));ck(cudaFreeHost(hi));ck(cudaFreeHost(hd));ck(cudaStreamDestroy(stream));
    }
};

void original_query(int q,float radius,int& count,std::vector<int>& ids,std::vector<float>& ds) {
    qid_list[0]=q;
    searchIndexRnnUpdate(data_d,node_list,id_list,max_node_num,qid_list,1,radius,tree_h,data_info,empty_list,
                        qresult_count,qresult_count_prefix,result_id,result_dis,data_s,size_s);
    count=qresult_count[0]; assert(count>=0 && count<=2220);
    ck(cudaMallocManaged(&total_result_id,count*sizeof(int)));ck(cudaMallocManaged(&total_result_dis,count*sizeof(float)));
    thrust::inclusive_scan(thrust::device,is_delete,is_delete+tree_size,is_delete_prefix);
    mergeTotalResult<<<(count-1)/512+1,512>>>(count,total_result_id,qresult_count,result_id,result_dis,obj_r,total_result_dis,is_delete_prefix,tree_size);
    ck(cudaDeviceSynchronize());
    for(int i=0;i<count;++i) {ids[i]=total_result_id[i];ds[i]=total_result_dis[i];}
    for(void* p:{(void*)total_result_id,(void*)total_result_dis,(void*)qresult_count,(void*)qresult_count_prefix,(void*)result_id,(void*)result_dis})ck(cudaFree(p));
}

uint64_t digest(int count,const int* ids,const float* ds) {
    uint64_t h=1469598103934665603ull;
    for(int i=0;i<count;++i) {uint32_t bits;memcpy(&bits,ds+i,4);h=(h^uint32_t(ids[i]))*1099511628211ull;h=(h^bits)*1099511628211ull;}
    return (h^uint32_t(count))*1099511628211ull;
}
double cpu_time() {rusage u{};getrusage(RUSAGE_SELF,&u);return u.ru_utime.tv_sec+u.ru_utime.tv_usec*1e-6+u.ru_stime.tv_sec+u.ru_stime.tv_usec*1e-6;}

int main(int argc,char** argv) {
    if(argc!=9) {fprintf(stderr,"usage: graph_bench data qids A|B|C radius repeats warmup output_prefix dump\n");return 1;}
    std::string mode=argv[3],out=argv[7];float radius=std::stof(argv[4]);int repeats=std::stoi(argv[5]),warmup=std::stoi(argv[6]);bool dump=std::stoi(argv[8]);
    assert((mode=="A"||mode=="B"||mode=="C") && repeats>0 && warmup>=0);
    auto process_start=Clock::now();load(argv[1],data_info,data_d,data_s,size_s);
    assert(data_info[1]==2000 && data_info[2]==6);
    std::ifstream qf(argv[2]);int nq; qf>>nq;assert(nq>0);std::vector<int> queries(nq);
    for(int& q:queries){qf>>q;assert(q>=0 && q<data_info[1]);}assert(qf.good());
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);ck(cudaDeviceSynchronize());
    assert(tree_h==3 && max_node_num[0]==111 && MAX_SIZE==20 && TREE_ORDER==10);
    std::vector<TN> tree(111);ck(cudaMemcpy(tree.data(),node_list,111*sizeof(TN),cudaMemcpyDeviceToHost));
    for(auto node:tree)if(node.is_leaf==1)assert(node.size<=20);
    tree_size=data_info[1];ck(cudaMallocManaged(&is_delete,tree_size*sizeof(int)));ck(cudaMallocManaged(&is_delete_prefix,tree_size*sizeof(int)));
    ck(cudaMemset(is_delete,0,tree_size*sizeof(int)));ck(cudaMallocManaged(&qid_list,sizeof(int)));ck(cudaDeviceSynchronize());
    std::vector<int> host_ids(2220);std::vector<float> host_ds(2220);int count=0;
    auto setup=Clock::now();Fixed* fixed=mode=="A"?nullptr:new Fixed(tree_size,tree_h);double capture_s=0;
    if(mode=="C"){*fixed->hq=queries[0];capture_s=fixed->capture(radius);}
    double setup_s=seconds(setup);
    auto call=[&](int q){if(fixed){fixed->query(q,radius,mode=="C");count=*fixed->hc;}else original_query(q,radius,count,host_ids,host_ds);};
    auto first=Clock::now();call(queries[0]);double first_s=seconds(first);
    for(int i=0;i<warmup;++i)call(queries[i%nq]);
    std::ofstream full; if(dump)full.open(out+".results");
    std::vector<double> us;std::vector<int> counts;std::vector<uint64_t> hashes;
    us.reserve(nq*repeats);counts.reserve(nq*repeats);hashes.reserve(nq*repeats);
    double cpu_start=cpu_time();auto loop=Clock::now();
    for(int j=0;j<repeats;++j)for(int q:queries) {
        auto t=Clock::now();call(q);us.push_back(seconds(t)*1e6);
        const int* ids=fixed?fixed->hi:host_ids.data();const float* ds=fixed?fixed->hd:host_ds.data();
        counts.push_back(count);hashes.push_back(digest(count,ids,ds));
        if(dump){full<<q<<' '<<count;for(int i=0;i<count;++i)full<<' '<<ids[i]<<':'<<ds[i];full<<'\n';}
    }
    double loop_s=seconds(loop),cpu_s=cpu_time()-cpu_start;
    std::ofstream samples(out+".csv");samples<<"qid,query_us,count,ordered_hash\n";samples<<std::setprecision(12);
    for(size_t i=0;i<us.size();++i)samples<<queries[i%nq]<<','<<us[i]<<','<<counts[i]<<','<<hashes[i]<<'\n';
    std::ofstream summary(out+".json");summary<<std::setprecision(12)
      <<"{\"mode\":\""<<mode<<"\",\"queries\":"<<us.size()<<",\"radius\":"<<radius
      <<",\"setup_s\":"<<setup_s<<",\"capture_instantiate_s\":"<<capture_s<<",\"first_query_s\":"<<first_s
      <<",\"sum_query_s\":"<<std::accumulate(us.begin(),us.end(),0.0)/1e6<<",\"loop_wall_s\":"<<loop_s
      <<",\"loop_cpu_s\":"<<cpu_s<<",\"before_cleanup_process_s\":"<<seconds(process_start)<<"}\n";
    delete fixed;
    ck(cudaFree(qid_list));ck(cudaFree(is_delete));ck(cudaFree(is_delete_prefix));
    for(void* p:{(void*)data_info,(void*)data_s,(void*)size_s,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)empty_list})ck(cudaFree(p));
    printf("PASS completed %s %zu queries\n",mode.c_str(),us.size());
}
