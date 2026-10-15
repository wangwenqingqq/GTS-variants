// Ordinary safe batch and full-capacity final-source materialization.
#pragma once
#include "plan.hpp"
#ifndef UPDATE
#error Explicit UPDATE=0(native),1(waves),2(final) required
#endif
struct PhysicalLedger {
    int kind,rows;uint64_t reference_moves,unique_dest,final_rows,copy_APIs,launches,H2D_plan_bytes,H2D_vector_bytes,D2D_bytes,kernel_payload_bytes,syncs,levels;
};
__global__ void materialize_final(uint32_t* data,const RowMove* plan,int rows,int dimensions){
    int r=int(blockIdx.x);if(r>=rows)return;RowMove move=plan[r];
    for(int j=threadIdx.x;j<dimensions;j+=blockDim.x)
        data[size_t(move.dst)*dimensions+j]=data[size_t(move.src)*dimensions+j];
}
static PhysicalLedger execute_plan(float* data,cudaStream_t stream,RowMove* device_plan,const BatchPlan& plan,int dimensions){
    PhysicalLedger ledger{};ledger.kind=0;ledger.rows=plan.count;ledger.reference_moves=plan.sequential.size();
    ledger.unique_dest=plan.final_source.size();ledger.final_rows=plan.net.size();ledger.syncs=1;
#if UPDATE==1
    int levels=plan.levels.empty()?0:*std::max_element(plan.levels.begin(),plan.levels.end())+1;
    std::vector<size_t> counts(levels),offsets(levels+1),cursor;
    for(int level:plan.levels)++counts[level];
    for(int l=0;l<levels;l++)offsets[l+1]=offsets[l]+counts[l];cursor=offsets;
    std::vector<void*> dsts(plan.sequential.size());std::vector<const void*> srcs(plan.sequential.size());
    std::vector<size_t> bytes(plan.sequential.size(),size_t(dimensions)*4);
    for(size_t i=0;i<plan.sequential.size();i++){auto m=plan.sequential[i];size_t k=cursor[plan.levels[i]]++;
        dsts[k]=data+size_t(m.dst)*dimensions;srcs[k]=data+size_t(m.src)*dimensions;}
    cudaMemcpyAttributes attr{};attr.srcAccessOrder=cudaMemcpySrcAccessOrderStream;size_t first=0;
    for(int l=0;l<levels;l++){
        ck(cudaMemcpyBatchAsync(dsts.data()+offsets[l],srcs.data()+offsets[l],bytes.data()+offsets[l],counts[l],&attr,&first,1,stream));++ledger.copy_APIs;
    }
    ledger.levels=levels;ledger.D2D_bytes=plan.sequential.size()*size_t(dimensions)*4;
#elif UPDATE==2
    if(plan.net.size()==1){auto m=plan.net[0];ck(cudaMemcpyAsync(data+size_t(m.dst)*dimensions,data+size_t(m.src)*dimensions,size_t(dimensions)*4,cudaMemcpyDeviceToDevice,stream));ledger.copy_APIs=1;ledger.D2D_bytes=size_t(dimensions)*4;}
    else if(!plan.net.empty()){
        ck(cudaMemcpyAsync(device_plan,plan.net.data(),plan.net.size()*sizeof(RowMove),cudaMemcpyHostToDevice,stream));ledger.copy_APIs=1;ledger.H2D_plan_bytes=plan.net.size()*sizeof(RowMove);
        materialize_final<<<int(plan.net.size()),128,0,stream>>>((uint32_t*)data,device_plan,int(plan.net.size()),dimensions);ck(cudaGetLastError());ledger.launches=1;
        ledger.kernel_payload_bytes=plan.net.size()*size_t(dimensions)*4;
    }
#else
    for(auto m:plan.sequential){ck(cudaMemcpyAsync(data+size_t(m.dst)*dimensions,data+size_t(m.src)*dimensions,size_t(dimensions)*4,cudaMemcpyDeviceToDevice,stream));++ledger.copy_APIs;}
    ledger.D2D_bytes=plan.sequential.size()*size_t(dimensions)*4;
#endif
    ck(cudaStreamSynchronize(stream));return ledger;
}
