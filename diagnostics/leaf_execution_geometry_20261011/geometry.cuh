#pragma once
// Diagnostic sidecar only. Original search arrays and decisions are never written.
struct LGRow {
    float lower, node_bound, leaf_bound;
    unsigned tested, passed, visits, valid_mask, compute_mask, accepted_mask, leaf_task;
};
static_assert(sizeof(LGRow)==40, "portable row layout");
#if LG_COUNTS
__managed__ LGRow *lg_rows=nullptr;
__managed__ unsigned long long lg_pivots[2];
static int lg_capacity=0;
static void lg_check(cudaError_t e) {
    if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e));
}
static void lg_setup(int count) {
    if(MAX_SIZE>32 || THREAD_NUM!=512) throw std::runtime_error("geometry outside contract");
    lg_capacity=count;
    lg_check(cudaMallocManaged((void**)&lg_rows,size_t(count)*sizeof(LGRow)));
}
static void lg_reset() {
    lg_check(cudaMemset(lg_rows,0,size_t(lg_capacity)*sizeof(LGRow)));
    lg_pivots[0]=lg_pivots[1]=0;
}
static void lg_save(std::ofstream& f,int qid) {
    f.write((char*)&qid,4);f.write((char*)lg_pivots,16);
    f.write((char*)lg_rows,size_t(lg_capacity)*sizeof(LGRow));
    if(!f) throw std::runtime_error("geometry write failed");
}
static void lg_close() {lg_check(cudaFree(lg_rows));lg_rows=nullptr;}
#else
static void lg_setup(int) {}
static void lg_reset() {}
static void lg_save(std::ofstream&,int) {}
static void lg_close() {}
#endif
