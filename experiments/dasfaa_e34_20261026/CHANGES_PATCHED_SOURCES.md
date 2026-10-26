# Corrected P/G source builds

P is rebuilt from the archived header identified in AMENDMENTS.md, with exactly
the supplied correctness patch and separate WORK-only instrumentation. Native
leaf interval endpoints are preserved. Other copied headers are unchanged.

The vector harness rebuilds every index outside the query timer and rejects
unsafe N/height before search. It checks leaf capacity and complete ID coverage.
G's additional adapter observes existing sorted leaf-slot payloads to return IDs,
and sets native MAX_H from order10/leaf20. G is compile-only: the original
half-free-memory workspace can overflow its signed-int slot count on a near-idle
96GiB device. No workspace extension or runtime result is claimed.

`build_patched.py` creates a fresh output namespace and guards all compiler
children. Set `GTSPP_GUARD` to the verified guard path. Each compiler is bounded
by240s/16GiB and minimum48GiB available RAM. Source, patch, compiler commands and
binary hashes are retained in build manifests.

Local checks: `python3 test_patched_sources.py` (five tests). These establish
source-token/adapter/configuration properties, not GPU correctness. CUDA13.1
sm120 compilation succeeded for P, instrumented P and G; sanitizer and complete
correctness remain independent gates.
