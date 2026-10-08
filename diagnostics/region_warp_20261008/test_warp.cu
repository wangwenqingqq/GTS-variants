#include <cuda_runtime.h>
#ifndef REGION_WARP_MICRO
__device__ int* owner_probe=nullptr;
#define REGION_WARP_TEST_OWNER(slot) (owner_probe[slot]=threadIdx.x/32)
#endif
#define main retained_structural_main
#include "../region_exec_20261008/test_region.cu"
#undef main
#include <cstring>
#include <random>

void check_leaves(const std::vector<int>& sizes,int nl) {
    int n=std::accumulate(sizes.begin(),sizes.end(),0),pos=0;
    require(n<=MAX_REGION_OBJECTS && int(sizes.size())<=10,"bounded test geometry");
    std::vector<Node> nodes(11);std::vector<int> empty(11,1),ids(n);
    nodes[0]={0,0,n,0,0};empty[0]=0;
    for(size_t i=0;i<sizes.size();i++){nodes[i+1]={0,0,sizes[i],pos,1};empty[i+1]=0;pos+=sizes[i];}
    std::iota(ids.rbegin(),ids.rend(),0);auto plan=make_plan(nodes,empty,ids,10);
    require(plan.regions.size()==1,"single bounded region");
    std::vector<float> host(n*QUERY_DIM);
    std::mt19937 rng(2026100801);std::uniform_int_distribution<int> value(-11,11);
    for(float& x:host)x=value(rng);
    if(n>1)std::copy(host.begin(),host.begin()+QUERY_DIM,host.begin()+QUERY_DIM);
    auto nd=gpu(nodes);auto em=gpu(empty);auto id=gpu(ids);auto data=gpu(host);
    auto deleted=gpu(std::vector<int>(n));auto qid=gpu(std::vector<int>{0});
    auto reg=gpu(plan.regions);auto ls=gpu(plan.leaf_slot);auto sp=gpu(plan.slot_pid);
    auto hit=gpu(std::vector<int>(n));auto dis=gpu(std::vector<float>(n));
    auto leaf=gpu(plan.leaves);auto counts=gpu(std::vector<int>{nl});
    View v{nd,em,id,data,deleted,qid,reg,ls,sp,n,11,1,10,7};
#ifndef REGION_WARP_MICRO
    auto owners=gpu(std::vector<int>(n,-1));ck(cudaMemcpyToSymbol(owner_probe,&owners,sizeof(owners)));
    Work w{};w.objects=gpu(std::vector<unsigned long long>(n));
    for(int repeat=0;repeat<3;repeat++)for(int del=0;del<2;del++)for(float radius:{0.0f,10000.0f}) {
        std::vector<int> deleted_host(n);
        for(int pid=0;pid<n;pid++)deleted_host[pid]=del && (pid==0 || pid%4==1);
        ck(cudaMemcpy(deleted,deleted_host.data(),n*4,cudaMemcpyHostToDevice));
        std::vector<int> refhit;std::vector<float> refdist;std::vector<unsigned long long> refwork;
        for(int warp=0;warp<2;warp++) {
            ck(cudaMemset(hit,0,n*4));ck(cudaMemset(dis,0,n*4));ck(cudaMemset(owners,0xff,n*4));ck(cudaMemset(w.objects,0,n*8));
            if(warp)verify_regions<true><<<1,BLOCK_THREADS>>>(v,leaf,counts,radius,hit,dis,w);
            else verify_regions<false><<<1,BLOCK_THREADS>>>(v,leaf,counts,radius,hit,dis,w);
            ck(cudaDeviceSynchronize());auto got=cpu(hit,n);auto fields=cpu(dis,n);auto work=cpu(w.objects,n);auto observed=cpu(owners,n);
            std::vector<int> expected(n);std::vector<unsigned long long> expected_work(n);
            for(int l=0;l<nl;l++)for(int j=0;j<nodes[plan.leaves[l]].size;j++) {
                int pid=ids[nodes[plan.leaves[l]].lid+j],slot=plan.leaf_slot[plan.leaves[l]]+j;
                long long sq=0;for(int d=0;d<QUERY_DIM;d++){long long diff=host[pid*QUERY_DIM+d]-host[d];sq+=diff*diff;}
                expected[slot]=!deleted_host[pid] && sq<=double(radius)*radius;
                expected_work[pid]=!deleted_host[pid] && pid!=0;
                if(warp && got[slot])require(observed[slot]==(nl==1?(j%BLOCK_THREADS)/32:l%8),"actual warp owner differs");
            }
            require(got==expected && work==expected_work,"integer oracle/work membership");
            if(!warp){refhit=got;refdist=fields;refwork=work;}
            else require(got==refhit && work==refwork && std::memcmp(fields.data(),refdist.data(),n*4)==0,"SERIAL/WARP exact fields");
        }
    }
    ck(cudaFree(owners));ck(cudaFree(w.objects));
#else
    Work w{};cudaEvent_t start,end;ck(cudaEventCreate(&start));ck(cudaEventCreate(&end));
    auto launch=[&](bool warp){
        if(warp)verify_regions<true><<<1,BLOCK_THREADS>>>(v,leaf,counts,10000,hit,dis,w);
        else verify_regions<false><<<1,BLOCK_THREADS>>>(v,leaf,counts,10000,hit,dis,w);
    };
    for(int i=0;i<100;i++){launch(false);launch(true);}ck(cudaDeviceSynchronize());
    std::cout<<"MICRO_ROWS [";
    for(int round=0;round<6;round++) {
        float times[2];
        for(int position=0;position<2;position++) {
            bool warp=(round%2?1-position:position);ck(cudaEventRecord(start));
            for(int i=0;i<512;i++)launch(warp);
            ck(cudaEventRecord(end));ck(cudaEventSynchronize(end));float elapsed;ck(cudaEventElapsedTime(&elapsed,start,end));times[warp]=elapsed/512;
        }
        std::cout<<(round?",":"")<<"{\"round\":"<<round+1<<",\"serial_ms\":"<<times[0]<<",\"warp_ms\":"<<times[1]<<"}";
    }
    std::cout<<"]\n";ck(cudaEventDestroy(start));ck(cudaEventDestroy(end));
    auto got=cpu(hit,n);require(std::all_of(got.begin(),got.end(),[](int x){return x==1;}),"micro full delivery");
#endif
    for(void* p:{(void*)nd,(void*)em,(void*)id,(void*)data,(void*)deleted,(void*)qid,(void*)reg,(void*)ls,(void*)sp,
                 (void*)hit,(void*)dis,(void*)leaf,(void*)counts})ck(cudaFree(p));
}

int main() try {
#ifdef REGION_WARP_MICRO
    check_leaves(std::vector<int>(8,20),8);
    std::cout<<"MICRO_PASS: 8 leaves x20 objects; counters/ownership probe OFF; CUDA-event batches only\n";
#else
    int valid=0,rejected=0;
    for(int nl:{0,1,7,8,9})for(int size:{1,20,32,33}) {
        if(nl*size>MAX_REGION_OBJECTS){++rejected;continue;}
        check_leaves(std::vector<int>(std::max(nl,1),size),nl);++valid;
    }
    check_leaves({1,20,32,33,1,20,32,33,1},9);++valid;
    check_leaves({33,1,20,32,1,33,32},7);++valid;
    std::cout<<"WARP_BOUNDARY_PASS: "<<valid<<" bounded geometries; "<<rejected<<" inadmissible combinations excluded; x3 reuse x2 deletion x2 radius x2 mapping; actual owners/work/FP32\n";
#endif
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
