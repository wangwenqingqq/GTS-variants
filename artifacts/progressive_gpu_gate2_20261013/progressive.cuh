// Frozen four-stage exact prefix screening; installed stable CUB selection.
#pragma once
#include <array>
#include <cstdint>
struct alignas(16) PrefixState {double sum;int id;uint32_t replay;};
static_assert(sizeof(PrefixState)==16,"charged tuple stride");
__device__ double ordered_prefix(const float* x,const float* q,int row,int end){
    double sum=0;
    for(int j=0;j<end;j++){
        double delta=__dsub_rn(double(x[size_t(row)*960+j]),double(q[j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));
    }
    return sum;
}
template<int START,int END>
__global__ void progressive_stage(const float* x,const float* q,const PrefixState* input,
                                 PrefixState* output,uint8_t* keep,int active,double cutoff){
    int r=int(blockIdx.x)*8+int(threadIdx.x)/32,lane=int(threadIdx.x)%32;
    if(r>=active)return; // Uniform warp return: no ragged-mask shuffle.
    int owner=START==0?r:__shfl_sync(0xffffffff,lane==0?input[r].id:0,0);
    float chunk=0;
    for(int j=START+lane;j<END;j+=32){
        float delta=__fsub_rn(x[size_t(owner)*960+j],q[j]);
        chunk=__fmaf_rn(delta,delta,chunk);
    }
    for(int step=16;step;step/=2)chunk=__fadd_rn(chunk,__shfl_down_sync(0xffffffff,chunk,step));
    if(lane==0){
        double sum=__dadd_rn(START==0?0.:input[r].sum,double(chunk));
        double error=__dadd_ru(__dmul_ru(sum,0x1p-16),0x1p-120);
        double lower=__dsub_rd(sum,error),upper=__dadd_ru(sum,error);
        uint32_t replay=0;bool retain;
        if(lower>cutoff)retain=false;
        else if(upper<=cutoff)retain=true;
        else{sum=ordered_prefix(x,q,owner,END);replay=END;retain=sum<=cutoff;}
        if(END==960&&retain&&replay==0){sum=ordered_prefix(x,q,owner,960);replay=960;}
        output[r]={sum,owner,replay};keep[r]=retain;
    }
}
__global__ void progressive_fields(const PrefixState* hits,int* ids,float* fields,double* raw,int count){
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<count){float score=__double2float_rn(hits[i].sum);ids[i]=hits[i].id;
        fields[i]=sqrtf(fmaxf(0,score));raw[i]=double(score);}
}
struct StageRecord {int invocation,stage,input,output;uint64_t replay=0;double scan=0,compact=0,host=0;};
struct ProgressiveScan {
    int n=0,d=960,*outids=nullptr,*count=nullptr,audit_mode=0,invocation=0;
    float *database=nullptr,*query=nullptr,*squared=nullptr,*fields=nullptr;double* raw=nullptr;
    PrefixState *active_state=nullptr,*temporary=nullptr;uint8_t* flags=nullptr;
    void* scratch=nullptr;size_t bytes=0;cudaStream_t stream{};
    std::string audit_prefix;std::vector<StageRecord> records;std::array<std::vector<int>,4> last_ids;
    cudaEvent_t events[14]{};std::vector<std::array<double,3>> outputs;
    void build(const std::vector<float>& data,int rows,int dim){
        if(rows<0||rows>1000000||dim!=960||data.size()!=size_t(rows)*960)throw std::runtime_error("P1 shape");
        for(float v:data)if(!std::isfinite(v)||std::abs(v)>16)throw std::runtime_error("P1 data envelope");
        n=rows;d=dim;ck(cudaStreamCreate(&stream));
        alloc(database,data.size());alloc(query,960);alloc(active_state,n);alloc(temporary,n);alloc(flags,n);
        alloc(outids,n);alloc(fields,n);alloc(raw,n);alloc(count,1);
        if(n){ck(cudaMemcpyAsync(database,data.data(),data.size()*4,cudaMemcpyHostToDevice,stream));
            ck(cub::DeviceSelect::Flagged(nullptr,bytes,temporary,flags,active_state,count,n,stream));ck(cudaMalloc(&scratch,bytes));}
        for(auto& e:events)ck(cudaEventCreate(&e));ck(cudaStreamSynchronize(stream));
    }
    void range(const float* q,float radius,std::vector<int>& ids,std::vector<float>& dist,std::vector<double>& native){
        if(!std::isfinite(radius)||radius<0)throw std::runtime_error("P1 radius");
        for(int j=0;j<960;j++)if(!std::isfinite(q[j])||std::abs(q[j])>16)throw std::runtime_error("P1 query envelope");
        ids.clear();dist.clear();native.clear();for(auto& x:last_ids)x.clear();if(!n)return;
        ck(cudaMemcpyAsync(query,q,960*4,cudaMemcpyHostToDevice,stream));
        int active=n;double cutoff=double(radius)*double(radius);
        for(int stage=0;stage<4;stage++){
            StageRecord record{invocation,stage+1,active,0};auto start=Clock::now();
            if(active){
                if(audit_mode==3)ck(cudaEventRecord(events[stage*3],stream));
                int grid=(active+7)/8;
                if(stage==0)progressive_stage<0,128><<<grid,256,0,stream>>>(database,query,nullptr,temporary,flags,active,cutoff);
                if(stage==1)progressive_stage<128,256><<<grid,256,0,stream>>>(database,query,active_state,temporary,flags,active,cutoff);
                if(stage==2)progressive_stage<256,512><<<grid,256,0,stream>>>(database,query,active_state,temporary,flags,active,cutoff);
                if(stage==3)progressive_stage<512,960><<<grid,256,0,stream>>>(database,query,active_state,temporary,flags,active,cutoff);
                ck(cudaGetLastError());if(audit_mode==3)ck(cudaEventRecord(events[stage*3+1],stream));
                size_t capacity=bytes;ck(cub::DeviceSelect::Flagged(scratch,capacity,temporary,flags,active_state,count,active,stream));
                if(audit_mode==3)ck(cudaEventRecord(events[stage*3+2],stream));
                ck(cudaMemcpyAsync(&record.output,count,4,cudaMemcpyDeviceToHost,stream));ck(cudaStreamSynchronize(stream));
                if(record.output<0||record.output>active)throw std::runtime_error("P1 capacity");
                if(audit_mode==3){float t;ck(cudaEventElapsedTime(&t,events[stage*3],events[stage*3+1]));record.scan=t;
                    ck(cudaEventElapsedTime(&t,events[stage*3+1],events[stage*3+2]));record.compact=t;record.host=ms(start);}
                if(audit_mode==2||audit_mode==4){
                    std::vector<PrefixState> in(active),out(record.output);
                    ck(cudaMemcpy(in.data(),temporary,in.size()*16,cudaMemcpyDeviceToHost));
                    if(!out.empty())ck(cudaMemcpy(out.data(),active_state,out.size()*16,cudaMemcpyDeviceToHost));
                    for(auto& v:in)record.replay+=v.replay;
                    for(auto& v:out)last_ids[stage].push_back(v.id);
                }
            }
            if(audit_mode==2){std::string path=audit_prefix+".checkpoint."+std::to_string(invocation)+"."+std::to_string(stage+1)+".i32";
                std::ofstream f(path,std::ios::binary);auto& v=last_ids[stage];f.write((char*)v.data(),v.size()*4);if(!f)throw std::runtime_error("checkpoint persistence");}
            records.push_back(record);active=record.output;
        }
        auto start=Clock::now();if(audit_mode==3)ck(cudaEventRecord(events[12],stream));
        if(active){progressive_fields<<<(active+255)/256,256,0,stream>>>(active_state,outids,fields,raw,active);ck(cudaGetLastError());}
        if(audit_mode==3)ck(cudaEventRecord(events[13],stream));
        ids.resize(active);dist.resize(active);native.resize(active);
        if(active){ck(cudaMemcpyAsync(ids.data(),outids,active*4,cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(dist.data(),fields,active*4,cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(native.data(),raw,active*8,cudaMemcpyDeviceToHost,stream));}
        ck(cudaStreamSynchronize(stream));double final_wall=ms(start),field_ms=0;
        if(audit_mode==3){float t;ck(cudaEventElapsedTime(&t,events[12],events[13]));field_ms=t;}
        outputs.push_back({double(invocation),field_ms,final_wall});++invocation;
    }
    void write_audit(const std::string& prefix){
        std::ofstream f(prefix+".stages.csv"),o(prefix+".output.csv");
        f<<"invocation,stage,input,output,replay_coordinates,scan_ms,compact_ms,host_stage_ms\n"<<std::setprecision(17);
        for(auto& r:records)f<<r.invocation<<','<<r.stage<<','<<r.input<<','<<r.output<<','<<r.replay<<','<<r.scan<<','<<r.compact<<','<<r.host<<'\n';
        o<<"invocation,fields_ms,host_output_ms\n"<<std::setprecision(17);for(auto& x:outputs)o<<x[0]<<','<<x[1]<<','<<x[2]<<'\n';
        if(!f||!o)throw std::runtime_error("P1 audit persistence");
    }
    void release(){drop(database);drop(query);drop(squared);drop(active_state);drop(temporary);drop(flags);
        drop(outids);drop(fields);drop(raw);drop(count);drop(scratch);
        for(auto& e:events)ck(cudaEventDestroy(e));ck(cudaStreamDestroy(stream));ck(cudaDeviceSynchronize());}
};
