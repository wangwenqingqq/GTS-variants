#pragma once
#include "gts_cpu_io_profile.hpp"
// Sequential host scopes; original CUDA synchronization is unchanged.
struct QueryStages {
    const char* name=nullptr;
    double wall=0,cpu=0;
    void close() {
        if(!name)return;
        double c=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID)-cpu;
        double w=gts_diag_seconds(CLOCK_MONOTONIC)-wall;
        nvtxRangePop();auto& s=gts_diag_stats()[name];
        ++s.count;s.wall+=w;s.cpu+=c;name=nullptr;
    }
    void set(const char* next) {
        close();name=next;gts_diag_stats()[name];nvtxRangePushA(name);
        wall=gts_diag_seconds(CLOCK_MONOTONIC);
        cpu=gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID);
    }
    ~QueryStages(){close();}
};
