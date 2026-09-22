#pragma once
// Diagnostic-only host ranges. No additional GPU synchronization is inserted.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <map>
#include <string>
#include <cuda_runtime_api.h>
#ifdef GTS_DIAG_NVTX
#include <nvtx3/nvToolsExt.h>
#endif

struct GtsDiagStats { unsigned long count = 0; double wall = 0, cpu = 0; };
inline std::map<std::string, GtsDiagStats>& gts_diag_stats() {
    static std::map<std::string, GtsDiagStats> stats;
    return stats;
}
inline double gts_diag_seconds(clockid_t id) {
    timespec t;
    if (clock_gettime(id, &t)) { std::perror("clock_gettime"); std::abort(); }
    return double(t.tv_sec) + double(t.tv_nsec) * 1e-9;
}
struct GtsDiagScope {
    const char* name;
    double wall, cpu;
    explicit GtsDiagScope(const char* n) : name(n) {
        gts_diag_stats()[name];
#ifdef GTS_DIAG_NVTX
        nvtxRangePushA(name);
#endif
        wall = gts_diag_seconds(CLOCK_MONOTONIC);
        cpu = gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID);
    }
    ~GtsDiagScope() {
        double c = gts_diag_seconds(CLOCK_THREAD_CPUTIME_ID) - cpu;
        double w = gts_diag_seconds(CLOCK_MONOTONIC) - wall;
#ifdef GTS_DIAG_NVTX
        nvtxRangePop();
#endif
        auto& s = gts_diag_stats()[name];
        ++s.count; s.wall += w; s.cpu += c;
    }
};
struct GtsDiagDump {
    GtsDiagDump() { gts_diag_stats(); }
    ~GtsDiagDump() {
        std::fprintf(stderr, "GTS_DIAG,range,count,inclusive_wall_s,inclusive_main_thread_cpu_s\n");
        for (const auto& p : gts_diag_stats())
            std::fprintf(stderr, "GTS_DIAG,%s,%lu,%.9f,%.9f\n", p.first.c_str(),
                         p.second.count, p.second.wall, p.second.cpu);
    }
};
#define GTS_DIAG_JOIN_(a,b) a##b
#define GTS_DIAG_JOIN(a,b) GTS_DIAG_JOIN_(a,b)
#define GTS_DIAG_SCOPE(name) GtsDiagScope GTS_DIAG_JOIN(gts_diag_scope_, __LINE__)(name)

inline bool gts_diag_blocking() {
    const char* v = std::getenv("GTS_DIAG_BLOCKING");
    return v && !std::strcmp(v, "1");
}
inline void gts_diag_configure() {
    if (gts_diag_blocking()) {
        cudaError_t e = cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync);
        if (e != cudaSuccess) {
            std::fprintf(stderr, "blocking control failed: %s\n", cudaGetErrorString(e));
            std::exit(2);
        }
    }
    std::fprintf(stderr, "GTS_DIAG,blocking_control,%d\n", int(gts_diag_blocking()));
}
inline cudaError_t gts_diag_event_create(cudaEvent_t* e) {
    return cudaEventCreateWithFlags(e, gts_diag_blocking() ? cudaEventBlockingSync : cudaEventDefault);
}
