// Host-only check: compile with g++, do not link CUDA, do not create a context.
#include "profile.hpp"
#include <cassert>
#include <chrono>
#include <thread>

int main() {
    GtsDiagDump dump;
    {
        GTS_DIAG_SCOPE("outer");
        { GTS_DIAG_SCOPE("inner"); }
        { GTS_DIAG_SCOPE("inner"); }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    const auto& s = gts_diag_stats();
    assert(s.at("outer").count == 1 && s.at("inner").count == 2);
    assert(s.at("outer").wall >= 0.015);
    assert(s.at("outer").wall >= s.at("inner").wall);
    assert(s.at("outer").cpu >= s.at("inner").cpu);
    assert(s.at("inner").cpu >= 0);
    std::puts("PASS: nested host ranges and CPU/wall clock accounting; no CUDA calls");
}
