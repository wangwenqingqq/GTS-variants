#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "batch_tree_prefix.cuh"

static void ck(cudaError_t e) {
    if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e));
}
template<class T> static T* dev(size_t n) {T* p=nullptr;ck(cudaMalloc(&p,n*sizeof(T)));return p;}
static double elapsed(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
}
template<class T> static std::vector<T> raw(const std::string& path,size_t n) {
    std::ifstream in(path,std::ios::binary);std::vector<T> out(n);
    in.read(reinterpret_cast<char*>(out.data()),n*sizeof(T));
    if(!in||in.peek()!=EOF)throw std::runtime_error("bad raw file "+path);
    return out;
}
static std::vector<int> qids(const std::string& path,int n) {
    std::ifstream in(path);int count;in>>count;
    if(!in||count<1)throw std::runtime_error("bad qid header");
    std::vector<int> out(count);
    for(int& q:out)if(!(in>>q)||q<0||q>=n)throw std::runtime_error("bad qid");
    int extra;if(in>>extra)throw std::runtime_error("extra qid");
    return out;
}

__global__ void mask_compare(const uint8_t* a,const uint8_t* b,size_t count,
                             unsigned long long* mismatches) {
    const size_t i=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(i<count&&a[i]!=b[i])atomicAdd(mismatches,1ull);
}

// Diagnostic only: measure how much of the SCAN_E arithmetic each tree mask removes.
__global__ void stop_dimensions(const float* data,const int* order,const int* query_ids,
                                const float* radii,int n,int d,size_t slots,uint16_t* stop) {
    const size_t at=size_t(blockIdx.x)*blockDim.x+threadIdx.x;
    if(at>=slots)return;
    const int q=int(at/n),pos=int(at%n);
    const float r=radii[q];
    if(r<0){stop[at]=0;return;}
    const double limit=__dmul_rn(double(r),double(r));
    const float* object=data+size_t(order[pos])*d;
    const float* query=data+size_t(query_ids[q])*d;
    double sum=0;
    int used=0;
    for(int j=0;j<d;++j) {
        const double delta=__dsub_rn(double(object[j]),double(query[j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));
        used=j+1;
        if((j&31)==31&&sum>limit)break;
    }
    stop[at]=uint16_t(used);
}

int main(int argc,char** argv) {
    try {
        if((argc!=8&&argc!=9)||(argc==9&&std::string(argv[8])!="--work"))
            throw std::runtime_error("usage: candidate_ledger data.f32bin index.bin idlist.i32 queries.qid radius_bits batch output_prefix [--work]");
        const bool measure_work=argc==9;
        const auto setup_start=std::chrono::steady_clock::now();
        std::ifstream index(argv[2],std::ios::binary);int header[3];
        index.read(reinterpret_cast<char*>(header),sizeof(header));
        const int d=header[0],n=header[1],nodes=header[2];
        if(!index||n<1||d<2||d>960||nodes<11111)throw std::runtime_error("bad index header");
        std::vector<TN> tree(nodes);std::vector<int> empty(nodes),order(n);
        index.read(reinterpret_cast<char*>(tree.data()),nodes*sizeof(TN));
        index.read(reinterpret_cast<char*>(empty.data()),nodes*sizeof(int));
        index.read(reinterpret_cast<char*>(order.data()),n*sizeof(int));
        if(!index||index.peek()!=EOF)throw std::runtime_error("bad index body");
        if(order!=raw<int>(argv[3],n))throw std::runtime_error("index id_list differs");
        std::ifstream data_file(argv[1],std::ios::binary);int data_header[3];
        data_file.read(reinterpret_cast<char*>(data_header),sizeof(data_header));
        if(!data_file||data_header[0]!=d||data_header[1]!=n||data_header[2]!=2)
            throw std::runtime_error("data/index dimension mismatch");
        std::vector<float> data(size_t(n)*d);
        data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
        if(!data_file||data_file.peek()!=EOF)throw std::runtime_error("bad data body");
        const auto measured=qids(argv[4],n);const int batch=std::stoi(argv[6]);
        if(batch<1||batch>32||measured.size()%batch)throw std::runtime_error("bad batch");
        const uint32_t radius_bits=uint32_t(std::stoul(argv[5],nullptr,0));
        float radius;std::memcpy(&radius,&radius_bits,4);
        if(!std::isfinite(radius)||radius<0)throw std::runtime_error("bad radius");
        std::vector<float> radii(batch,radius);
        const int stride=11111;
        std::vector<int> level_map(n),frontier(n,-1);
        float* d_data=dev<float>(data.size());int* d_order=dev<int>(n);
        TN* d_tree=dev<TN>(nodes);int* d_empty=dev<int>(nodes);
        int* d_map=dev<int>(n);int* d_frontier=dev<int>(n);
        auto* lower=dev<unsigned long long>(nodes);auto* upper=dev<unsigned long long>(nodes);
        std::vector<unsigned long long> lo(nodes,~0ull),hi(nodes,0);
        ck(cudaMemcpy(d_data,data.data(),data.size()*sizeof(float),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(d_order,order.data(),n*sizeof(int),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(d_tree,tree.data(),nodes*sizeof(TN),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(d_empty,empty.data(),nodes*sizeof(int),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(lower,lo.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
        ck(cudaMemcpy(upper,hi.data(),nodes*sizeof(unsigned long long),cudaMemcpyHostToDevice));
        int start=1,width=10;
        for(int level=1;level<=4;++level) {
            std::fill(level_map.begin(),level_map.end(),-1);
            for(int nid=start;nid<start+width;++nid)if(empty[nid]==0) {
                const TN node=tree[nid];
                if(node.pid<0||node.pid>=n||node.lid<0||node.size<=0||node.lid+node.size>n)
                    throw std::runtime_error("bad tree node");
                for(int pos=node.lid;pos<node.lid+node.size;++pos) {
                    if(level_map[pos]!=-1)throw std::runtime_error("overlap node membership");
                    level_map[pos]=nid;
                }
            }
            if(std::find(level_map.begin(),level_map.end(),-1)!=level_map.end())
                throw std::runtime_error("incomplete tree membership");
            ck(cudaMemcpy(d_map,level_map.data(),n*sizeof(int),cudaMemcpyHostToDevice));
            refit_bounds<<<(n+255)/256,256>>>(d_map,d_order,d_tree,d_data,n,d,lower,upper);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            if(level==4)frontier=level_map;
            start+=width;width*=10;
        }
        ck(cudaMemcpy(d_frontier,frontier.data(),n*sizeof(int),cudaMemcpyHostToDevice));
        const double setup_s=elapsed(setup_start);
        int* d_qids=dev<int>(batch);float* d_radii=dev<float>(batch);
        int* flags=dev<int>(size_t(batch)*stride);int* old=dev<int>(size_t(batch)*stride);
        uint8_t* fresh=dev<uint8_t>(size_t(batch)*n);
        uint8_t* legacy=dev<uint8_t>(size_t(batch)*n);
        auto* pivots=dev<unsigned long long>(batch);
        auto* mismatches=dev<unsigned long long>(1);
        uint16_t* d_stop=measure_work?dev<uint16_t>(size_t(batch)*n):nullptr;
        std::ofstream query_out(std::string(argv[7])+".queries.csv");
        std::ofstream pair_out(std::string(argv[7])+".pairs.csv");
        query_out<<"query_index,qid,candidates,pivot_distances,candidate_hash\n";
        pair_out<<"pair_index,qid0,qid1,candidate_pairs,union_objects,intersection_objects,nonempty_tiles\n";
        std::ofstream work_out;
        std::ofstream level_out;
        if(measure_work) {
            work_out.open(std::string(argv[7])+".work.csv");
            work_out<<"pair_index,scan_pair_coordinate_updates,tree_pair_coordinate_updates,"
                       "scan_shared_coordinate_steps,tree_shared_coordinate_steps,"
                       "scan_warp_span_steps,tree_warp_span_steps\n";
            level_out.open(std::string(argv[7])+".levels.csv");
            level_out<<"batch_id,level,entered_groups,tested_children,passed_children,"
                         "pivot_distances,reused_child_distances\n";
        }
        unsigned long long total_pivots=0,total_candidates=0,total_union=0,total_intersection=0;
        uint64_t scan_pair_steps=0,tree_pair_steps=0,scan_shared=0,tree_shared=0;
        uint64_t scan_warp=0,tree_warp=0;
        const auto run_start=std::chrono::steady_clock::now();
        for(size_t base=0;base<measured.size();base+=batch) {
            ck(cudaMemcpy(d_qids,measured.data()+base,batch*sizeof(int),cudaMemcpyHostToDevice));
            ck(cudaMemcpy(d_radii,radii.data(),batch*sizeof(float),cudaMemcpyHostToDevice));
            ck(cudaMemset(flags,0,size_t(batch)*stride*sizeof(int)));
            ck(cudaMemset(old,0,size_t(batch)*stride*sizeof(int)));
            ck(cudaMemset(pivots,0,batch*sizeof(unsigned long long)));
            ck(cudaMemset(mismatches,0,sizeof(unsigned long long)));
            roots<<<(batch+255)/256,256>>>(flags,stride,batch);
            roots<<<(batch+255)/256,256>>>(old,stride,batch);
            start=1;width=10;
            std::vector<unsigned long long> previous_pivots(batch,0);
            for(int level=1;level<=4;++level) {
                parent_walk<<<dim3((width/10+255)/256,batch),256>>>(flags,stride,start,width/10,
                    d_tree,d_empty,lower,upper,d_data,d_qids,d_radii,batch,d,pivots);
                for(int q=0;q<batch;++q) {
                    strict_walk<false><<<(width+511)/512,512>>>(old+size_t(q)*stride,start,
                        d_tree,radius,d_data,d_qids+q,width,d,d_empty,lower,upper);
                    clear_parents<<<(width/10+511)/512,512>>>(old+size_t(q)*stride,start,width);
                }
                if(measure_work) {
                    std::vector<int> level_flags(size_t(batch)*stride);
                    std::vector<unsigned long long> level_pivots(batch);
                    ck(cudaMemcpy(level_flags.data(),flags,level_flags.size()*sizeof(int),
                                  cudaMemcpyDeviceToHost));
                    ck(cudaMemcpy(level_pivots.data(),pivots,batch*sizeof(unsigned long long),
                                  cudaMemcpyDeviceToHost));
                    uint64_t entered=0,tested=0,passed=0,pivot_count=0;
                    for(int q=0;q<batch;++q) {
                        const int* query_flags=level_flags.data()+size_t(q)*stride;
                        for(int group=0;group<width/10;++group) {
                            const int first=start+group*10;
                            if(query_flags[(first-1)/10]!=1)continue;
                            ++entered;
                            for(int child=0;child<10;++child) {
                                const int nid=first+child;
                                if(empty[nid]!=0)continue;
                                ++tested;passed+=query_flags[nid]==1;
                            }
                        }
                        pivot_count+=level_pivots[q]-previous_pivots[q];
                    }
                    if(pivot_count>tested)throw std::runtime_error("invalid pivot count");
                    level_out<<base/batch<<','<<level<<','<<entered<<','<<tested
                             <<','<<passed<<','<<pivot_count<<','<<tested-pivot_count<<'\n';
                    previous_pivots=level_pivots;
                }
                start+=width;width*=10;
            }
            const size_t slots=size_t(batch)*n;
            candidate_mask<<<(slots+255)/256,256>>>(flags,stride,d_frontier,n,batch,fresh);
            candidate_mask<<<(slots+255)/256,256>>>(old,stride,d_frontier,n,batch,legacy);
            mask_compare<<<(slots+255)/256,256>>>(fresh,legacy,slots,mismatches);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            unsigned long long mismatch=0;
            ck(cudaMemcpy(&mismatch,mismatches,sizeof(mismatch),cudaMemcpyDeviceToHost));
            if(mismatch)throw std::runtime_error("candidate mismatch: "+std::to_string(mismatch));
            std::vector<uint8_t> host(slots);
            std::vector<unsigned long long> pivot_host(batch);
            ck(cudaMemcpy(host.data(),fresh,slots,cudaMemcpyDeviceToHost));
            std::vector<uint16_t> stop;
            if(measure_work) {
                stop.resize(slots);
                stop_dimensions<<<(slots+255)/256,256>>>(d_data,d_order,d_qids,d_radii,
                                                          n,d,slots,d_stop);
                ck(cudaGetLastError());
                ck(cudaMemcpy(stop.data(),d_stop,slots*sizeof(uint16_t),cudaMemcpyDeviceToHost));
            }
            ck(cudaMemcpy(pivot_host.data(),pivots,batch*sizeof(unsigned long long),cudaMemcpyDeviceToHost));
            std::vector<unsigned long long> counts(batch,0);
            for(int q=0;q<batch;++q) {
                uint64_t digest=1469598103934665603ull;
                for(int pos=0;pos<n;++pos)if(host[size_t(q)*n+pos]) {
                    ++counts[q];digest=(digest^uint32_t(pos))*1099511628211ull;
                }
                digest=(digest^counts[q])*1099511628211ull;
                query_out<<base+q<<','<<measured[base+q]<<','<<counts[q]<<','
                         <<pivot_host[q]<<','<<digest<<'\n';
                total_candidates+=counts[q];total_pivots+=pivot_host[q];
            }
            for(int q=0;q+1<batch;q+=2) {
                unsigned long long uni=0,intersection=0,tiles=0;
                uint64_t sp=0,tp=0,ss=0,ts=0,sw=0,tw=0;
                const uint8_t* a=host.data()+size_t(q)*n;
                const uint8_t* b=host.data()+size_t(q+1)*n;
                for(int pos=0;pos<n;pos+=32) {
                    bool nonempty=false;
                    uint16_t scan_tile_max=0,tree_tile_max=0;
                    for(int lane=0;lane<32&&pos+lane<n;++lane) {
                        const bool x=a[pos+lane],y=b[pos+lane];
                        uni+=x||y;intersection+=x&&y;nonempty|=x||y;
                        if(measure_work) {
                            const int at=pos+lane;
                            const uint16_t u=stop[size_t(q)*n+at];
                            const uint16_t v=stop[size_t(q+1)*n+at];
                            const uint16_t tu=x?u:0,tv=y?v:0;
                            sp+=u+v;tp+=tu+tv;
                            ss+=std::max(u,v);ts+=std::max(tu,tv);
                            scan_tile_max=std::max(scan_tile_max,std::max(u,v));
                            tree_tile_max=std::max(tree_tile_max,std::max(tu,tv));
                        }
                    }
                    sw+=scan_tile_max;tw+=tree_tile_max;
                    tiles+=nonempty;
                }
                pair_out<<(base+q)/2<<','<<measured[base+q]<<','<<measured[base+q+1]
                        <<','<<counts[q]+counts[q+1]<<','<<uni<<','<<intersection
                        <<','<<tiles<<'\n';
                total_union+=uni;total_intersection+=intersection;
                if(measure_work) {
                    work_out<<(base+q)/2<<','<<sp<<','<<tp<<','<<ss<<','<<ts
                            <<','<<sw<<','<<tw<<'\n';
                    scan_pair_steps+=sp;tree_pair_steps+=tp;
                    scan_shared+=ss;tree_shared+=ts;scan_warp+=sw;tree_warp+=tw;
                }
            }
            std::cout<<"PASS batch "<<base/batch<<" candidate masks identical\n"<<std::flush;
        }
        std::ofstream meta(std::string(argv[7])+".summary.txt");
        meta<<std::setprecision(12)<<"queries="<<measured.size()<<"\n"
            <<"batch="<<batch<<"\nrefit_and_setup_s="<<setup_s<<"\n"
            <<"ledger_wall_s="<<elapsed(run_start)<<"\n"
            <<"candidate_pairs="<<total_candidates<<"\n"
            <<"pair_fraction="<<double(total_candidates)/(double(measured.size())*n)<<"\n"
            <<"candidate_union_objects="<<total_union<<"\n"
            <<"candidate_intersection_objects="<<total_intersection<<"\n"
            <<"pivot_distances="<<total_pivots<<"\n"
            <<"candidate_identity=old_strict_walk_exact_for_all_positions\n";
        if(measure_work)meta<<"scan_pair_coordinate_updates="<<scan_pair_steps<<"\n"
            <<"tree_pair_coordinate_updates="<<tree_pair_steps<<"\n"
            <<"scan_shared_coordinate_steps="<<scan_shared<<"\n"
            <<"tree_shared_coordinate_steps="<<tree_shared<<"\n"
            <<"scan_warp_span_steps="<<scan_warp<<"\n"
            <<"tree_warp_span_steps="<<tree_warp<<"\n";
        std::cout<<"PASS all queries, candidate_pairs="<<total_candidates
                 <<" pivot_distances="<<total_pivots<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<"ERROR "<<e.what()<<'\n';return 2;}
}
