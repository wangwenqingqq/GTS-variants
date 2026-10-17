// Same packed ownership and frozen query;only the delete plan/executor changes.
#include "generic.hpp"
#include <memory>
#include <thrust/for_each.h>
#include <thrust/iterator/counting_iterator.h>
#include <thrust/system/cuda/execution_policy.h>
static int variant=0;
static int batch_limit=512;
static const char* variants[]={"NATIVE","WAVES","GENERIC_WAVES","GENERIC_DSE","TAIL_GENERIC","TAIL_CUSTOM"};
struct UpdateRecord {int rows,moves,assignments,levels;uint64_t copy_APIs,kernels,metadata,payload,syncs;double capture_ms,plan_ms;};
struct IndexedCopy {
    uint32_t* data;const RowMove* plan;int dimensions;
    __device__ void operator()(int index)const{
        RowMove m=plan[index/dimensions];int j=index%dimensions;
        data[size_t(m.dst)*dimensions+j]=data[size_t(m.src)*dimensions+j];
    }
};
__global__ void materialize_final(uint32_t* data,const RowMove* plan,int rows,int dimensions){
    int r=int(blockIdx.x);if(r>=rows)return;RowMove m=plan[r];
    for(int j=threadIdx.x;j<dimensions;j+=blockDim.x)data[size_t(m.dst)*dimensions+j]=data[size_t(m.src)*dimensions+j];
}
static void generic_rows(float* data,const RowMove* plan,int rows,int d,cudaStream_t stream){
    if(!rows)return;
    thrust::for_each_n(thrust::cuda::par_nosync.on(stream),thrust::make_counting_iterator(0),rows*d,IndexedCopy{reinterpret_cast<uint32_t*>(data),plan,d});
    ck(cudaGetLastError());
}
struct Store:NativeStore {
    RowMove* device_plan=nullptr;std::vector<UpdateRecord> updates;
    void build(const std::vector<float>& x,int n,int extra){
        NativeStore::build(x,n,extra);updates.reserve(32768);if(variant>=2)alloc(device_plan,512);
    }
    uint64_t extra_device_bytes()const{return NativeStore::extra_device_bytes()+(variant>=2?4096:0);}
    Cost erase(const std::vector<int>& ids){
        if(variant==0||ids.size()==1){
            uint64_t before=swapped;Cost c=NativeStore::erase(ids);int moves=int((swapped-before)/3840);
            updates.push_back({int(ids.size()),moves,0,0,uint64_t(moves),0,0,uint64_t(moves)*3840,1,0,0});return c;
        }
        Zone ack("U_DELETE");require(!ids.empty()&&ids.size()<=512,"delete batch bound");
        {Zone validation("DELETE_VALIDATE");std::set<int> unique;for(int id:ids)require(id>=0&&id<next&&position.at(id)>=0&&unique.insert(id).second,"live unique delete IDs");}
        int n=p.n;auto capture=Clock::now();std::vector<RowMove> commands;commands.reserve(ids.size());
        for(int id:ids){int row=position[id],last=p.n-1,moved=row==last?-1:occurrence.back();
            Mutation m{0,id,p.n,row,last,moved,next,p.n-1};
            if(row!=last){commands.push_back({last,row});occurrence[row]=moved;position[moved]=row;swapped+=3840;}
            occurrence.pop_back();position[id]=-1;--p.n;mutations.push_back(m);
            require(int(occurrence.size())==p.n&&position[id]==-1,"delete local owner");
            if(moved>=0)require(occurrence[row]==moved&&position[moved]==row,"swap local owner");
        }
        UpdateRecord row{};row.rows=int(ids.size());row.moves=int(commands.size());row.capture_ms=ms(capture);row.syncs=1;
        auto plan_begin=Clock::now();std::unique_ptr<BatchPlan> tp;std::vector<RowMove> generic;const std::vector<RowMove>* final=nullptr;
        std::vector<RowMove> sorted;std::vector<int> offsets;std::vector<void*> dsts;std::vector<const void*> srcs;std::vector<size_t> sizes;
        {Zone planning("PLAN_BUILD");
            if(variant==1||variant==2){
                tp=std::make_unique<BatchPlan>(n,int(ids.size()),false);for(auto m:commands)tp->push(m.src,m.dst);tp->finish(true);
                int levels=tp->levels.empty()?0:*std::max_element(tp->levels.begin(),tp->levels.end())+1;row.levels=levels;offsets.assign(levels+1,0);
                for(int level:tp->levels)++offsets[level+1];for(int l=0;l<levels;l++)offsets[l+1]+=offsets[l];auto cursor=offsets;sorted.resize(commands.size());
                for(size_t i=0;i<commands.size();i++)sorted[cursor[tp->levels[i]]++]=commands[i];
                if(variant==1)for(auto m:sorted){dsts.push_back(p.database+size_t(m.dst)*960);srcs.push_back(p.database+size_t(m.src)*960);sizes.push_back(3840);}
            }else{
                if(variant==3){generic=generic_compile(commands);final=&generic;}
                else{tp=std::make_unique<BatchPlan>(n,int(ids.size()));for(auto m:commands)tp->push(m.src,m.dst);tp->finish(false);final=&tp->net;}
                std::set<int> destinations;for(auto m:*final)require(m.src>=0&&m.src<n&&m.dst>=0&&m.dst<n&&destinations.insert(m.dst).second,"unique legal final destinations");
                for(auto m:*final)require(!destinations.count(m.src),"in-place nonalias certificate");
                row.assignments=int(final->size());
            }
        }
        row.plan_ms=ms(plan_begin);
        {Zone execute("UPDATE_EXECUTE");
            if(variant==1){
                cudaMemcpyAttributes attr{};attr.srcAccessOrder=cudaMemcpySrcAccessOrderStream;size_t first=0;
                for(int l=0;l<row.levels;l++){int a=offsets[l],count=offsets[l+1]-a;
                    ck(cudaMemcpyBatchAsync(dsts.data()+a,srcs.data()+a,sizes.data()+a,count,&attr,&first,1,p.stream));++row.copy_APIs;}
                row.payload=uint64_t(commands.size())*3840;
            }else if(variant==2){
                if(!sorted.empty()){
                    ck(cudaMemcpyAsync(device_plan,sorted.data(),sorted.size()*8,cudaMemcpyHostToDevice,p.stream));row.copy_APIs=1;row.metadata=sorted.size()*8;
                    for(int l=0;l<row.levels;l++){int a=offsets[l],count=offsets[l+1]-a;generic_rows(p.database,device_plan+a,count,960,p.stream);++row.kernels;}
                }
                row.payload=uint64_t(commands.size())*3840;
            }else{
                int count=int(final->size());row.payload=uint64_t(count)*3840;
                if(count==1){auto m=final->front();ck(cudaMemcpyAsync(p.database+size_t(m.dst)*960,p.database+size_t(m.src)*960,3840,cudaMemcpyDeviceToDevice,p.stream));row.copy_APIs=1;}
                else if(count){
                    ck(cudaMemcpyAsync(device_plan,final->data(),count*8,cudaMemcpyHostToDevice,p.stream));row.copy_APIs=1;row.metadata=uint64_t(count)*8;
                    if(variant==5){materialize_final<<<count,128,0,p.stream>>>(reinterpret_cast<uint32_t*>(p.database),device_plan,count,960);ck(cudaGetLastError());}
                    else generic_rows(p.database,device_plan,count,960,p.stream);
                    row.kernels=1;
                }
            }
            ck(cudaStreamSynchronize(p.stream));
        }
        updates.push_back(row);return {};
        // All plan/set/vector destructors run before the enclosing Host ACK ends.
    }
    void write_updates(const std::string& out)const{
        std::ofstream f(out+".updates.csv");f<<std::setprecision(17)<<"rows,moves,assignments,levels,copy_APIs,kernels,metadata,payload,syncs,capture_ms,plan_ms\n";
        for(auto r:updates)f<<r.rows<<','<<r.moves<<','<<r.assignments<<','<<r.levels<<','<<r.copy_APIs<<','<<r.kernels<<','<<r.metadata<<','<<r.payload<<','<<r.syncs<<','<<r.capture_ms<<','<<r.plan_ms<<'\n';require(bool(f),"update ledger export");
    }
    void release(){drop(device_plan);std::vector<UpdateRecord>().swap(updates);NativeStore::release();}
};
