#pragma once
// Only the eleven private temporaries of searchIndexRnnUpdate. Compute and
// initialization kernels and their existing completion fences stay unchanged.
struct ULifeWorkspace {
    struct Slot {void* pointer=nullptr; size_t capacity=0, logical_bytes=0;};
    Slot slots[11];
    bool reuse=u10_env("U10_LIFE");
    size_t allocations=0, frees=0, allocated_bytes=0, live_bytes=0, peak_bytes=0, growths=0;
    double release_ms=0, setup_ms=0;
    void acquire(void** out,int index,size_t bytes,bool managed) {
        Slot& s=slots[index];s.logical_bytes=bytes;
        if(reuse && s.capacity>=bytes){*out=bytes?s.pointer:nullptr;return;}
        if(reuse && s.pointer){
            // Every previous use ended at the unchanged mergeResultRnn fence.
            // The serialized operation ACK also precedes the next query.
            u10_ck(cudaFree(s.pointer));++frees;live_bytes-=s.capacity;
            s.pointer=nullptr;s.capacity=0;++growths;
        }
        u10_ck(managed?cudaMallocManaged(out,bytes):cudaMalloc(out,bytes));
        ++allocations;allocated_bytes+=bytes;live_bytes+=bytes;
        peak_bytes=std::max(peak_bytes,live_bytes);
        s.pointer=*out;s.capacity=bytes;
    }
    void release(void* pointer,int index) {
        if(reuse)return;
        Slot& s=slots[index];
        if(s.pointer!=pointer)throw std::runtime_error("workspace ownership");
        u10_ck(cudaFree(pointer));++frees;live_bytes-=s.capacity;
        s=Slot{};
    }
    void finish() {
        auto start=U10Clock::now();
        if(reuse)for(auto& s:slots)if(s.pointer){
            u10_ck(cudaFree(s.pointer));++frees;live_bytes-=s.capacity;
            s=Slot{};
        }
        release_ms=u10_ms(start);
        if(live_bytes)throw std::runtime_error("workspace leak");
    }
    void write(const std::string& path) {
        std::ofstream f(path+".workspace.json");f<<std::setprecision(17)
          <<"{\"mode\":\""<<(reuse?"U_LIFE":"U_BASE")<<"\",\"allocations\":"<<allocations
          <<",\"frees\":"<<frees<<",\"allocated_bytes\":"<<allocated_bytes<<",\"growths\":"<<growths
          <<",\"selected_workspace_peak_bytes\":"<<peak_bytes<<",\"live_after_release_bytes\":"<<live_bytes
          <<",\"final_release_ms\":"<<release_ms<<",\"process_setup_ms\":"<<setup_ms
          <<",\"setup_plus_trace_ms\":"<<setup_ms+u10.trace_ms
          <<",\"scope\":\"selected 11 explicit workspaces only; excludes Thrust, index, externally owned results and context setup\"}\n";
        if(!f)throw std::runtime_error("workspace ledger write");
    }
};
static ULifeWorkspace u_life;
